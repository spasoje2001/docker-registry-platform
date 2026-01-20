import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings, Client
from django.urls import reverse

from .services import LogIndexer, LogSearchService

User = get_user_model()


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


class LogSearchServiceTest(TestCase):
    """Unit tests for LogSearchService."""

    def setUp(self):
        self.search_service = LogSearchService(es_url="http://localhost:9200")

    def test_build_query_no_filters(self):
        """Test query building with no filters."""
        query = self.search_service._build_query(None, None, None, None)
        self.assertEqual(query, {'match_all': {}})

    def test_build_query_with_text(self):
        """Test query building with text search."""
        query = self.search_service._build_query("error message", None, None, None)
        self.assertIn('bool', query)
        self.assertIn('must', query['bool'])

    def test_build_query_with_level(self):
        """Test query building with level filter."""
        query = self.search_service._build_query(None, "ERROR", None, None)
        self.assertIn('bool', query)
        must_clauses = query['bool']['must']
        self.assertTrue(any('term' in clause and 'level' in clause.get('term', {})
                            for clause in must_clauses))

    def test_build_query_with_date_range(self):
        """Test query building with date range."""
        query = self.search_service._build_query(
            None, None, "2026-01-01", "2026-01-31"
        )
        self.assertIn('bool', query)
        must_clauses = query['bool']['must']
        self.assertTrue(any('range' in clause for clause in must_clauses))

    def test_get_index_pattern(self):
        """Test index pattern generation."""
        pattern = self.search_service._get_index_pattern()
        self.assertEqual(pattern, "docker-registry-logs-*")


class AnalyticsViewTest(TestCase):
    """Tests for analytics views."""

    def setUp(self):
        self.client = Client()

        # Create super admin
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='adminpass123',
            role=User.Role.SUPER_ADMIN
        )

        # Create regular user
        self.user = User.objects.create_user(
            username='regularuser',
            email='user@test.com',
            password='userpass123',
            role=User.Role.USER
        )

    def test_anonymous_user_cannot_access_analytics(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_regular_user_cannot_access_analytics(self):
        """Test that regular users cannot access analytics."""
        self.client.login(username='regularuser', password='userpass123')
        response = self.client.get(reverse('analytics:search'))

        # Should redirect to home
        self.assertEqual(response.status_code, 302)

        # Check warning message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('permission', str(messages[0]))

    @patch.object(LogSearchService, 'search_logs')
    def test_admin_can_access_analytics(self, mock_search):
        """Test that admin users can access analytics."""
        # Mock search results
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/search.html')

    @patch.object(LogSearchService, 'search_logs')
    def test_search_with_query_parameter(self, mock_search):
        """Test search with text query."""
        mock_search.return_value = {
            'results': [
                {
                    'timestamp': '2026-01-14T12:00:00',
                    'level': 'INFO',
                    'logger_name': 'test',
                    'message': 'Test message'
                }
            ],
            'total': 1,
            'page': 1,
            'total_pages': 1,
            'has_next': False,
            'has_prev': False
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'), {'q': 'test'})

        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once()

        # Verify query parameter was passed
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['query'], 'test')

    @patch.object(LogSearchService, 'search_logs')
    def test_filter_by_level(self, mock_search):
        """Test filtering by log level."""
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'), {'level': 'ERROR'})

        self.assertEqual(response.status_code, 200)

        # Verify level parameter was passed
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['level'], 'ERROR')

    @patch.object(LogSearchService, 'search_logs')
    def test_filter_by_date_range(self, mock_search):
        """Test filtering by date range."""
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'), {
            'date_from': '2026-01-01',
            'date_to': '2026-01-31'
        })

        self.assertEqual(response.status_code, 200)

        # Verify date parameters were passed
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['date_from'], '2026-01-01')
        self.assertEqual(call_kwargs['date_to'], '2026-01-31')

    @patch.object(LogSearchService, 'search_logs')
    def test_pagination(self, mock_search):
        """Test pagination works correctly."""
        mock_search.return_value = {
            'results': [],
            'total': 50,
            'page': 2,
            'total_pages': 3,
            'has_next': True,
            'has_prev': True
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'), {'page': '2'})

        self.assertEqual(response.status_code, 200)

        # Verify page parameter was passed
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['page'], 2)

        # Check context has pagination data
        self.assertTrue(response.context['has_next'])
        self.assertTrue(response.context['has_prev'])

    @patch.object(LogSearchService, 'search_logs')
    def test_elasticsearch_error_handling(self, mock_search):
        """Test graceful handling of Elasticsearch errors."""
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False,
            'error': 'Elasticsearch unavailable'
        }

        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:search'))

        self.assertEqual(response.status_code, 200)

        # Check error message was displayed
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('Elasticsearch', str(messages[0]))
