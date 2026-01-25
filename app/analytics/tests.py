import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings, Client
from django.urls import reverse

from .services import LogIndexer, LogSearchService
from .services.query_builder import QueryBuilder

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

class QueryBuilderBasicTests(TestCase):
    """Tests for basic QueryBuilder functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_empty_conditions_returns_match_all(self):
        """Empty conditions list should return match_all query."""
        result = self.builder.build_query([])
        self.assertEqual(result, {'match_all': {}})

    def test_invalid_field_returns_match_all(self):
        """Invalid field should be ignored, returning match_all."""
        conditions = [
            {'field': 'nonexistent_field', 'operator': 'equals', 'value': 'test'}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'match_all': {}})

    def test_empty_value_returns_match_all(self):
        """Empty value should be ignored, returning match_all."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': ''}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'match_all': {}})

    def test_whitespace_value_returns_match_all(self):
        """Whitespace-only value should be ignored."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': '   '}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'match_all': {}})

class QueryBuilderKeywordFieldTests(TestCase):
    """Tests for keyword field queries."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_single_keyword_equals(self):
        """Single keyword field with equals operator."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'term': {'level': 'ERROR'}})

    def test_keyword_field_method(self):
        """Keyword field 'method' with equals operator."""
        conditions = [
            {'field': 'method', 'operator': 'equals', 'value': 'POST'}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'term': {'method': 'POST'}})

    def test_keyword_field_user(self):
        """Keyword field 'user' with equals operator."""
        conditions = [
            {'field': 'user', 'operator': 'equals', 'value': 'admin'}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result, {'term': {'user': 'admin'}})

class QueryBuilderTextFieldTests(TestCase):
    """Tests for text field queries."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_single_text_contains(self):
        """Single text field with contains operator."""
        conditions = [
            {'field': 'message', 'operator': 'contains', 'value': 'failed'}
        ]
        result = self.builder.build_query(conditions)
        expected = {
            'match': {
                'message': {
                    'query': 'failed',
                    'operator': 'and'
                }
            }
        }
        self.assertEqual(result, expected)

    def test_text_contains_multiple_words(self):
        """Text field with multiple words should use AND operator."""
        conditions = [
            {'field': 'message', 'operator': 'contains', 'value': 'connection timeout'}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result['match']['message']['query'], 'connection timeout')
        self.assertEqual(result['match']['message']['operator'], 'and')

    def test_text_value_trimmed(self):
        """Text value should be trimmed of whitespace."""
        conditions = [
            {'field': 'message', 'operator': 'contains', 'value': '  failed  '}
        ]
        result = self.builder.build_query(conditions)
        self.assertEqual(result['match']['message']['query'], 'failed')

class QueryBuilderAndLogicTests(TestCase):
    """Tests for AND logic between conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_two_conditions_and(self):
        """Two conditions with AND logic."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 2)

    def test_three_conditions_and(self):
        """Three conditions with AND logic."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND'},
            {'field': 'method', 'operator': 'equals', 'value': 'POST', 'logic': 'AND'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 3)

    def test_default_logic_is_and(self):
        """Missing logic should default to AND."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])

class QueryBuilderOrLogicTests(TestCase):
    """Tests for OR logic between conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_two_conditions_or(self):
        """Two conditions with OR logic."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('should', result['bool'])
        self.assertEqual(result['bool']['minimum_should_match'], 1)
        self.assertEqual(len(result['bool']['should']), 2)

    def test_three_conditions_or(self):
        """Three conditions with OR logic."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR'},
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'logic': 'OR'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('should', result['bool'])
        self.assertEqual(len(result['bool']['should']), 3)

class QueryBuilderNegationTests(TestCase):
    """Tests for NOT operator (negation)."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_single_negated_condition(self):
        """Single negated condition should use must_not."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must_not', result['bool'])
        self.assertEqual(len(result['bool']['must_not']), 1)

    def test_regular_and_negated_condition(self):
        """Mix of regular and negated conditions."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'debug', 'logic': 'AND', 'negate': True}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertIn('must_not', result['bool'])
        self.assertEqual(len(result['bool']['must']), 1)
        self.assertEqual(len(result['bool']['must_not']), 1)

    def test_multiple_negated_conditions(self):
        """Multiple negated conditions."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True},
            {'field': 'level', 'operator': 'equals', 'value': 'DEBUG', 'logic': 'AND', 'negate': True}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must_not', result['bool'])
        self.assertEqual(len(result['bool']['must_not']), 2)

class QueryBuilderGroupTests(TestCase):
    """Tests for grouped conditions (parentheses support)."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_two_groups_and(self):
        """Two groups combined with AND: (A OR B) AND C."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND', 'group': 2}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 2)

        # First item should be nested bool with should
        first_group = result['bool']['must'][0]
        self.assertIn('bool', first_group)
        self.assertIn('should', first_group['bool'])

    def test_two_groups_or(self):
        """Two groups combined with OR: (A) OR (B)."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'method', 'operator': 'equals', 'value': 'POST', 'logic': 'OR', 'group': 2}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('should', result['bool'])
        self.assertEqual(result['bool']['minimum_should_match'], 1)

    def test_three_groups(self):
        """Three groups: (A OR B) AND (C) AND (D)."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
            {'field': 'method', 'operator': 'equals', 'value': 'POST', 'logic': 'AND', 'group': 2},
            {'field': 'user', 'operator': 'equals', 'value': 'admin', 'logic': 'AND', 'group': 3}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 3)

    def test_default_group_is_one(self):
        """Conditions without group should default to group 1."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND'}
        ]
        result = self.builder.build_query(conditions)

        # Should behave as single group with AND
        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])

class QueryBuilderDateRangeTests(TestCase):
    """Tests for date range filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_only_date_range(self):
        """Only date range, no conditions."""
        result = self.builder.build_query([], date_from='2025-01-01', date_to='2025-01-31')

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        range_clause = result['bool']['must'][0]
        self.assertIn('range', range_clause)
        self.assertIn('timestamp', range_clause['range'])
        self.assertEqual(range_clause['range']['timestamp']['gte'], '2025-01-01T00:00:00')
        self.assertEqual(range_clause['range']['timestamp']['lte'], '2025-01-31T23:59:59')

    def test_only_date_from(self):
        """Only date_from specified."""
        result = self.builder.build_query([], date_from='2025-01-15')

        range_clause = result['bool']['must'][0]
        self.assertIn('gte', range_clause['range']['timestamp'])
        self.assertNotIn('lte', range_clause['range']['timestamp'])

    def test_only_date_to(self):
        """Only date_to specified."""
        result = self.builder.build_query([], date_to='2025-01-31')

        range_clause = result['bool']['must'][0]
        self.assertNotIn('gte', range_clause['range']['timestamp'])
        self.assertIn('lte', range_clause['range']['timestamp'])

    def test_condition_with_date_range(self):
        """Single condition with date range."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        result = self.builder.build_query(conditions, date_from='2025-01-01')

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 2)

    def test_multiple_conditions_with_date_range(self):
        """Multiple conditions with date range."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND'}
        ]
        result = self.builder.build_query(conditions, date_from='2025-01-01', date_to='2025-01-31')

        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])
        self.assertEqual(len(result['bool']['must']), 3)

    def test_invalid_date_format_ignored(self):
        """Invalid date format should be ignored."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        result = self.builder.build_query(conditions, date_from='invalid-date')

        # Should just have the term clause, no date range
        self.assertEqual(result, {'term': {'level': 'ERROR'}})

class QueryBuilderPreviewTests(TestCase):
    """Tests for preview generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_empty_conditions_returns_empty_string(self):
        """Empty conditions should return empty preview."""
        preview = self.builder.generate_preview([])
        self.assertEqual(preview, "")

    def test_single_condition_preview(self):
        """Single condition preview."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertEqual(preview, "Log Level equals 'ERROR'")

    def test_two_conditions_and_preview(self):
        """Two conditions with AND preview."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND'}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('Log Level equals', preview)
        self.assertIn('AND', preview)
        self.assertIn('Message contains', preview)

    def test_two_conditions_or_preview(self):
        """Two conditions with OR preview."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR'}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('OR', preview)
        self.assertIn("'ERROR'", preview)
        self.assertIn("'WARNING'", preview)

    def test_negated_condition_preview(self):
        """Negated condition should show NOT."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('NOT', preview)
        self.assertIn("Log Level equals 'INFO'", preview)

    def test_grouped_conditions_preview(self):
        """Grouped conditions should show parentheses."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
            {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND', 'group': 2}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('(', preview)
        self.assertIn(')', preview)
        self.assertIn('OR', preview)
        self.assertIn('AND', preview)

    def test_date_range_preview(self):
        """Date range preview."""
        preview = self.builder.generate_preview([], date_from='2025-01-01', date_to='2025-01-31')
        self.assertIn('Date:', preview)
        self.assertIn('2025-01-01', preview)
        self.assertIn('2025-01-31', preview)

    def test_condition_with_date_range_preview(self):
        """Condition with date range preview."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        preview = self.builder.generate_preview(conditions, date_from='2025-01-01')
        self.assertIn("Log Level equals 'ERROR'", preview)
        self.assertIn('AND', preview)
        self.assertIn('Date:', preview)

    def test_date_from_only_preview(self):
        """Date from only preview."""
        preview = self.builder.generate_preview([], date_from='2025-01-15')
        self.assertEqual(preview, "Date: from 2025-01-15")

    def test_date_to_only_preview(self):
        """Date to only preview."""
        preview = self.builder.generate_preview([], date_to='2025-01-31')
        self.assertEqual(preview, "Date: until 2025-01-31")

class QueryBuilderUIHelperTests(TestCase):
    """Tests for UI helper methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_get_fields_for_ui(self):
        """get_fields_for_ui should return all fields with proper structure."""
        fields = self.builder.get_fields_for_ui()

        self.assertIsInstance(fields, list)
        self.assertTrue(len(fields) > 0)

        # Check structure of first field
        first_field = fields[0]
        self.assertIn('value', first_field)
        self.assertIn('label', first_field)
        self.assertIn('type', first_field)

    def test_get_fields_for_ui_contains_level(self):
        """Fields should contain 'level' field."""
        fields = self.builder.get_fields_for_ui()
        field_values = [f['value'] for f in fields]
        self.assertIn('level', field_values)

    def test_get_operators_for_keyword_field(self):
        """Keyword field should have equals operator."""
        operators = self.builder.get_operators_for_field('level')

        self.assertIsInstance(operators, list)
        self.assertTrue(len(operators) > 0)

        op_values = [op['value'] for op in operators]
        self.assertIn('equals', op_values)

    def test_get_operators_for_text_field(self):
        """Text field should have contains operator."""
        operators = self.builder.get_operators_for_field('message')

        op_values = [op['value'] for op in operators]
        self.assertIn('contains', op_values)

    def test_get_operators_for_invalid_field(self):
        """Invalid field should return empty list."""
        operators = self.builder.get_operators_for_field('nonexistent')
        self.assertEqual(operators, [])

class QueryBuilderNegativeOperatorTests(TestCase):
    """Tests for not_equals and not_contains operators."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = QueryBuilder()

    def test_keyword_not_equals(self):
        """Keyword field with not_equals operator."""
        conditions = [
            {'field': 'level', 'operator': 'not_equals', 'value': 'INFO'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must_not', result['bool'])
        self.assertEqual(len(result['bool']['must_not']), 1)
        self.assertEqual(result['bool']['must_not'][0], {'term': {'level': 'INFO'}})

    def test_text_not_contains(self):
        """Text field with not_contains operator."""
        conditions = [
            {'field': 'message', 'operator': 'not_contains', 'value': 'debug'}
        ]
        result = self.builder.build_query(conditions)

        self.assertIn('bool', result)
        self.assertIn('must_not', result['bool'])
        self.assertEqual(len(result['bool']['must_not']), 1)

    def test_equals_and_not_equals_same_value(self):
        """Equals AND not_equals same value should produce valid query (returns 0 results)."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO'},
            {'field': 'level', 'operator': 'not_equals', 'value': 'INFO', 'logic': 'AND'}
        ]
        result = self.builder.build_query(conditions)

        # Should produce a bool query with both conditions
        self.assertIn('bool', result)
        self.assertIn('must', result['bool'])

    def test_not_equals_preview(self):
        """Not equals should show 'does not equal' in preview."""
        conditions = [
            {'field': 'level', 'operator': 'not_equals', 'value': 'INFO'}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('does not equal', preview)
        self.assertIn('INFO', preview)

    def test_not_contains_preview(self):
        """Not contains should show 'does not contain' in preview."""
        conditions = [
            {'field': 'message', 'operator': 'not_contains', 'value': 'debug'}
        ]
        preview = self.builder.generate_preview(conditions)
        self.assertIn('does not contain', preview)
        self.assertIn('debug', preview)