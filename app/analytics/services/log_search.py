import logging
from datetime import datetime
from typing import Dict, Optional

from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError as ESConnectionError

logger = logging.getLogger(__name__)


class LogSearchService:
    """Service to search logs in Elasticsearch."""

    INDEX_PREFIX = "docker-registry-logs"
    DEFAULT_PAGE_SIZE = 20
    MAX_RESULTS = 10000

    def __init__(self, es_url: Optional[str] = None):
        """Initialize Elasticsearch client."""
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.es = None

    def connect(self) -> bool:
        """Establish ES connection. Returns True if successful."""
        try:
            self.es = Elasticsearch([self.es_url])
            if not self.es.ping():
                logger.error("Elasticsearch not reachable at %s", self.es_url)
                return False
            return True
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch: %s", e)
            return False

    def search_logs(
            self,
            query: Optional[str] = None,
            level: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            page: int = 1,
            page_size: int = DEFAULT_PAGE_SIZE,
            sort_order: str = 'desc'
    ) -> Dict:
        """
        Search logs with filters.

        Args:
            query: Text to search in message field
            level: Log level filter (INFO, WARNING, ERROR)
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            page: Page number for pagination (1-indexed)
            page_size: Results per page
            sort_order: 'desc' (newest first) or 'asc'

        Returns:
            dict with 'results', 'total', 'page', 'total_pages', 'has_next', 'has_prev'
        """
        if not self.connect():
            return {
                'results': [],
                'total': 0,
                'page': 1,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False,
                'error': 'Elasticsearch unavailable'
            }

        # Build query
        es_query = self._build_query(query, level, date_from, date_to)

        # Calculate pagination
        page = max(1, page)  # Ensure page is at least 1
        page_size = min(page_size, 100)  # Cap at 100 per page
        from_result = (page - 1) * page_size

        # Check if pagination exceeds max results
        if from_result >= self.MAX_RESULTS:
            return {
                'results': [],
                'total': 0,
                'page': page,
                'total_pages': 0,
                'has_next': False,
                'has_prev': page > 1,
                'error': f'Cannot retrieve results beyond {self.MAX_RESULTS} documents'
            }

        try:
            # Execute search
            response = self.es.search(
                index=self._get_index_pattern(),
                body={
                    'query': es_query,
                    'sort': [{'timestamp': {'order': sort_order}}],
                    'from': from_result,
                    'size': page_size
                }
            )

            # Parse results
            hits = response.get('hits', {})
            total = hits.get('total', {}).get('value', 0)
            results = [hit['_source'] for hit in hits.get('hits', [])]

            # Calculate pagination info
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            has_next = page < total_pages
            has_prev = page > 1

            return {
                'results': results,
                'total': total,
                'page': page,
                'total_pages': total_pages,
                'page_size': page_size,
                'has_next': has_next,
                'has_prev': has_prev
            }


        except NotFoundError:
            # No indices exist yet
            logger.warning("No Elasticsearch indices found")
            return {
                'results': [],
                'total': 0,
                'page': 1,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False,
                'error': 'No log data available. Run index_logs command first.'
            }

        except (ESConnectionError, Exception) as e:
            logger.error("Elasticsearch search error: %s", e)
            return {
                'results': [],
                'total': 0,
                'page': 1,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False,
                'error': 'Search error occurred'
            }

    @staticmethod
    def _build_query(
            query: Optional[str],
            level: Optional[str],
            date_from: Optional[str],
            date_to: Optional[str]
    ) -> Dict:
        """
        Build Elasticsearch query DSL.

        Returns a bool query with must clauses for filters.
        """
        must_clauses = []

        # Text search in message field
        if query and query.strip():
            must_clauses.append({
                'match': {
                    'message': {
                        'query': query.strip(),
                        'operator': 'and'
                    }
                }
            })

        # Log level filter
        if level and level.upper() in ['INFO', 'WARNING', 'ERROR']:
            must_clauses.append({
                'term': {
                    'level': level.upper()
                }
            })

        # Date range filter
        date_range = {}
        if date_from:
            try:
                datetime.strptime(date_from, '%Y-%m-%d')
                date_range['gte'] = f"{date_from}T00:00:00"
            except ValueError:
                logger.warning("Invalid date_from format: %s", date_from)

        if date_to:
            try:
                datetime.strptime(date_to, '%Y-%m-%d')
                date_range['lte'] = f"{date_to}T23:59:59"
            except ValueError:
                logger.warning("Invalid date_to format: %s", date_to)

        if date_range:
            must_clauses.append({
                'range': {
                    'timestamp': date_range
                }
            })

        # If no filters, match all
        if not must_clauses:
            return {'match_all': {}}

        # Return bool query
        return {
            'bool': {
                'must': must_clauses
            }
        }

    def _get_index_pattern(self) -> str:
        """Return index pattern to search across all monthly indices."""
        return f"{self.INDEX_PREFIX}-*"