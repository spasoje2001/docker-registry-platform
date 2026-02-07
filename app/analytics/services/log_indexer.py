import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

from django.conf import settings
from elasticsearch import Elasticsearch, exceptions as es_exceptions

logger = logging.getLogger(__name__)


class LogIndexer:
    """
    Service to index Django logs into Elasticsearch.

    Reads JSON log files and indexes them into monthly ES indices.
    Tracks file positions to avoid duplicate entries.
    """

    INDEX_PREFIX = "docker-registry-logs"
    BATCH_SIZE = 100

    # Loggers to exclude from indexing
    EXCLUDED_LOGGERS = [
        'django.server',  # Redundant with access logs
        'django.utils.autoreload',  # Development noise
        'django.template',  # Template debug noise
    ]

    # Path prefixes to exclude (reduces noise from static files)
    EXCLUDED_PATH_PREFIXES = [
        '/static/',
        '/favicon.ico',
    ]

    INDEX_MAPPING = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {"max_result_window": 10000}
        },
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "level": {"type": "keyword"},
                "logger_name": {"type": "keyword"},
                "message": {"type": "text"},
                "taskName": {"type": "keyword"},
                "user": {"type": "keyword"},
                "path": {"type": "keyword"},
                "method": {"type": "keyword"},
                "status_code": {"type": "integer"},
                "response_time_ms": {"type": "float"},
                "query_string": {"type": "text"},
                "user_agent": {"type": "text"},
                "ip_address": {"type": "ip"},
                "log_source": {"type": "keyword"}
            }
        }
    }

    def __init__(self, es_url: Optional[str] = None):
        """Initialize Elasticsearch client."""
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.es = None
        self.state_file = Path(settings.BASE_DIR) / "logs" / ".indexer_state.json"

    def connect(self) -> bool:
        """Establish ES connection. Returns True if successful."""
        try:
            self.es = Elasticsearch([self.es_url])
            if not self.es.ping():
                logger.error("Elasticsearch not reachable at %s", self.es_url)
                return False
            logger.info("Connected to Elasticsearch at %s", self.es_url)
            return True
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch: %s", e)
            return False

    def get_index_name(self, date: Optional[datetime] = None) -> str:
        """Generate index name: docker-registry-logs-YYYY.MM"""
        date = date or datetime.now()
        return f"{self.INDEX_PREFIX}-{date.strftime('%Y.%m')}"

    def ensure_index_exists(self, index_name: str) -> bool:
        """Create index with mapping if it doesn't exist."""
        try:
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name, body=self.INDEX_MAPPING)
                logger.info("Created index: %s", index_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to create index %s: %s", index_name, e)
            return False

    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse JSON log line, return dict or None if invalid."""
        line = line.strip()
        if not line:
            return None

        # Only try to parse lines that look like JSON
        if not line.startswith('{'):
            # Old plain-text format log - skip silently
            return None

        try:
            return json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Failed to parse log line: %s", line[:100])
            return None

    def should_index_log(self, log_entry: Dict) -> bool:
        """
        Determine if a log entry should be indexed.

        Filters out redundant and noisy logs.

        Args:
            log_entry: Parsed log entry dict

        Returns:
            True if log should be indexed, False to skip
        """
        # Check excluded loggers
        logger_name = log_entry.get('logger_name', '')
        for excluded in self.EXCLUDED_LOGGERS:
            if logger_name.startswith(excluded):
                return False

        # Check excluded paths (for access logs)
        path = log_entry.get('path', '')
        if path:
            for prefix in self.EXCLUDED_PATH_PREFIXES:
                if path.startswith(prefix):
                    return False

        return True

    def _load_state(self) -> Dict:
        """Load indexer state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load state file: %s", e)
        return {}

    def _save_state(self, state: Dict):
        """Save indexer state to file."""
        try:
            self.state_file.parent.mkdir(exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error("Failed to save state file: %s", e)

    def get_last_indexed_position(self, log_file: str) -> int:
        """Get last indexed byte position for log file."""
        state = self._load_state()
        return state.get(log_file, 0)

    def save_last_indexed_position(self, log_file: str, position: int):
        """Save last indexed byte position for log file."""
        state = self._load_state()
        state[log_file] = position
        self._save_state(state)

    def index_log_file(self, log_file_path: Path, full_reindex: bool = False) -> Dict:
        """
        Index new entries from log file.

        Returns dict with stats: indexed, skipped, errors, filtered.
        """
        if not log_file_path.exists():
            logger.warning("Log file not found: %s", log_file_path)
            return {"indexed": 0, "skipped": 0, "errors": 0, "filtered": 0}

        log_source = log_file_path.stem  # 'app', 'access', or 'error'
        start_position = 0 if full_reindex else self.get_last_indexed_position(
            str(log_file_path))

        stats = {"indexed": 0, "skipped": 0, "errors": 0, "filtered": 0}
        batch = []

        try:
            with open(log_file_path, 'r') as f:
                f.seek(start_position)
                current_position = start_position

                for line in f:
                    current_position += len(line.encode('utf-8'))

                    log_entry = self.parse_log_line(line)
                    if not log_entry:
                        stats["skipped"] += 1
                        continue

                    # Filter out noisy/redundant logs
                    if not self.should_index_log(log_entry):
                        stats["filtered"] += 1
                        continue

                    # Add metadata
                    log_entry["log_source"] = log_source

                    # Determine index and normalize timestamp
                    try:
                        # Parse timestamp: "2026-01-10 01:43:54,517" -> datetime
                        timestamp_str = log_entry["timestamp"]
                        # Replace comma with period and parse
                        timestamp_str = timestamp_str.replace(',', '.')
                        timestamp = datetime.strptime(
                            timestamp_str, "%Y-%m-%d %H:%M:%S.%f")

                        # Convert to ISO format for Elasticsearch
                        log_entry["timestamp"] = timestamp.isoformat()
                        index_name = self.get_index_name(timestamp)
                    except (KeyError, ValueError) as e:
                        logger.warning("Timestamp parsing failed: %s", e)
                        index_name = self.get_index_name()
                        # Keep original timestamp if parsing fails

                    # Ensure index exists
                    if not self.ensure_index_exists(index_name):
                        stats["errors"] += 1
                        continue

                    # Generate unique document ID to prevent duplicates on re-index
                    doc_id = hashlib.md5(
                        f"{log_entry.get('timestamp', '')}"
                        f"{log_entry.get('message', '')}"
                        f"{log_source}".encode()
                    ).hexdigest()

                    batch.append({"index": {"_index": index_name, "_id": doc_id}})
                    batch.append(log_entry)

                    # Bulk index when batch is full
                    if len(batch) >= self.BATCH_SIZE * 2:
                        if self._bulk_index(batch):
                            stats["indexed"] += len(batch) // 2
                        else:
                            stats["errors"] += len(batch) // 2
                        batch = []

                # Index remaining entries
                if batch:
                    if self._bulk_index(batch):
                        stats["indexed"] += len(batch) // 2
                    else:
                        stats["errors"] += len(batch) // 2

                # Save position
                self.save_last_indexed_position(str(log_file_path), current_position)

        except Exception as e:
            logger.error("Error indexing %s: %s", log_file_path, e)
            stats["errors"] += 1

        return stats

    def _bulk_index(self, batch: List) -> bool:
        """Execute bulk index operation. Returns True if successful."""
        try:
            response = self.es.bulk(body=batch, refresh=False)
            if response.get("errors"):
                # Log specific errors for debugging
                for item in response.get("items", []):
                    if "error" in item.get("index", {}):
                        error_info = item["index"]["error"]
                        logger.error(
                            "ES indexing error: %s - %s",
                            error_info.get("type"),
                            error_info.get("reason")
                        )
                return False
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Bulk index failed: %s", e)
            return False

    def index_all_logs(self, full_reindex: bool = False) -> Dict:
        """
        Index all log files.

        Returns combined stats for all files.
        """
        if not self.connect():
            logger.error("Cannot index logs: Elasticsearch unavailable")
            return {"indexed": 0, "skipped": 0, "errors": 0, "filtered": 0}

        logs_dir = Path(settings.BASE_DIR) / "logs"
        log_files = ["app.log", "access.log", "error.log"]

        total_stats = {"indexed": 0, "skipped": 0, "errors": 0, "filtered": 0}

        for log_file in log_files:
            log_path = logs_dir / log_file
            logger.info("Indexing %s...", log_file)

            stats = self.index_log_file(log_path, full_reindex)

            total_stats["indexed"] += stats["indexed"]
            total_stats["skipped"] += stats["skipped"]
            total_stats["errors"] += stats["errors"]
            total_stats["filtered"] += stats.get("filtered", 0)

            logger.info(
                "%s: indexed=%d, skipped=%d, errors=%d, filtered=%d",
                log_file, stats["indexed"], stats["skipped"], stats["errors"], stats.get("filtered", 0)
            )

        logger.info(
            "Total: indexed=%d, skipped=%d, errors=%d, filtered=%d",
            total_stats["indexed"],
            total_stats["skipped"],
            total_stats["errors"],
            total_stats["filtered"])

        return total_stats
