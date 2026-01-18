import json
from datetime import datetime
from unittest.mock import patch

from django.test import TestCase

from .services import LogIndexer


class LogIndexerTest(TestCase):
    """Unit tests for LogIndexer service."""

    def setUp(self):
        self.indexer = LogIndexer(es_url="http://localhost:9200")

    def test_get_index_name_current_month(self):
        """Test index name generation for current month."""
        now = datetime.now()
        expected = f"docker-registry-logs-{now.strftime('%Y.%m')}"
        self.assertEqual(self.indexer.get_index_name(), expected)

    def test_get_index_name_specific_date(self):
        """Test index name generation for specific date."""
        date = datetime(2024, 12, 15)
        expected = "docker-registry-logs-2024.12"
        self.assertEqual(self.indexer.get_index_name(date), expected)

    def test_parse_app_log_entry(self):
        """Test parsing app.log format."""
        log_line = json.dumps({
            "message": "Test message",
            "taskName": None,
            "timestamp": "2026-01-10 01:43:54,517",
            "level": "INFO",
            "logger_name": "django.test"
        })

        result = self.indexer.parse_log_line(log_line)

        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "Test message")
        self.assertEqual(result["level"], "INFO")
        self.assertEqual(result["logger_name"], "django.test")

    def test_parse_access_log_entry(self):
        """Test parsing access.log format."""
        log_line = json.dumps({
            "message": "HTTP Request",
            "user": "testuser",
            "path": "/test/",
            "method": "GET",
            "status_code": 200,
            "response_time_ms": 3.67,
            "timestamp": "2026-01-09 21:07:59,377",
            "level": "INFO",
            "logger_name": "access"
        })

        result = self.indexer.parse_log_line(log_line)

        self.assertIsNotNone(result)
        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["method"], "GET")
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["response_time_ms"], 3.67)

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        result = self.indexer.parse_log_line("not valid json")
        self.assertIsNone(result)

    @patch.object(LogIndexer, 'connect')
    def test_connect_success(self, mock_connect):
        """Test successful ES connection."""
        mock_connect.return_value = True
        self.assertTrue(self.indexer.connect())

    @patch.object(LogIndexer, 'connect')
    def test_connect_failure(self, mock_connect):
        """Test failed ES connection."""
        mock_connect.return_value = False
        self.assertFalse(self.indexer.connect())

    def test_position_tracking(self):
        """Test position save and load."""
        log_file = "/app/logs/test.log"
        position = 1024

        self.indexer.save_last_indexed_position(log_file, position)
        loaded_position = self.indexer.get_last_indexed_position(log_file)

        self.assertEqual(loaded_position, position)

    def test_position_tracking_new_file(self):
        """Test position for new file returns 0."""
        position = self.indexer.get_last_indexed_position("/nonexistent.log")
        self.assertEqual(position, 0)
