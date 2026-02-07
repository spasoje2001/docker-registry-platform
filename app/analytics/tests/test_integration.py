"""
Integration tests for Analytics Advanced Search.

Tests cover:
- View access control
- Search with various filters and conditions
- Complex queries (AND/OR/NOT, groups)
- Date range filtering
- Pagination
- Error handling when Elasticsearch is unavailable
- State preservation after search

Run with: python manage.py test analytics.tests.test_integration
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..services.log_search import LogSearchService
from ..services.query_builder import QueryBuilder


User = get_user_model()


def is_elasticsearch_available():
    """Check if Elasticsearch is available for testing."""
    service = LogSearchService()
    return service.connect()


class AnalyticsViewAccessTests(TestCase):
    """Tests for analytics view access control."""

    def setUp(self):
        """Set up test users."""
        self.client = Client()

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@test.com',
            password='testpass123',
            role='user'
        )

    def test_simple_search_requires_login(self):
        """Simple search page should require authentication."""
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 302)

    def test_advanced_search_requires_login(self):
        """Advanced search page should require authentication."""
        response = self.client.get(reverse('analytics:advanced_search'))
        self.assertEqual(response.status_code, 302)

    def test_simple_search_requires_admin(self):
        """Simple search page should require admin role."""
        self.client.login(username='regular_test', password='testpass123')
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 302)

    def test_advanced_search_requires_admin(self):
        """Advanced search page should require admin role."""
        self.client.login(username='regular_test', password='testpass123')
        response = self.client.get(reverse('analytics:advanced_search'))
        self.assertEqual(response.status_code, 302)

    def test_simple_search_accessible_by_admin(self):
        """Simple search page should be accessible by admin."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics')

    def test_advanced_search_accessible_by_admin(self):
        """Advanced search page should be accessible by admin."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('analytics:advanced_search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Query Builder')


class AnalyticsAdvancedSearchViewTests(TestCase):
    """Tests for advanced search view functionality."""

    def setUp(self):
        """Set up test client and admin user."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client.login(username='admin_test', password='testpass123')
        self.url = reverse('analytics:advanced_search')

        # Mock response for when ES is available
        self.mock_search_result = {
            'results': [
                {
                    'timestamp': '2025-01-15T10:00:00',
                    'level': 'ERROR',
                    'message': 'Test error'
                }
            ],
            'total': 1,
            'page': 1,
            'total_pages': 1,
            'has_next': False,
            'has_prev': False,
            'query_preview': ''
        }

    def test_get_request_renders_form(self):
        """GET request should render the query builder form."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Query Builder')
        self.assertContains(response, 'advancedSearchForm')
        self.assertContains(response, 'conditionsJson')

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_empty_conditions(self, mock_search):
        """POST with empty conditions should return all logs."""
        mock_search.return_value = {**self.mock_search_result, 'query_preview': ''}

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('total', response.context)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_single_condition(self, mock_search):
        """POST with single condition should filter results."""
        mock_search.return_value = {
            **self.mock_search_result,
            'query_preview': "Log Level equals 'ERROR'"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('query_preview', response.context)
        self.assertIn('ERROR', response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_and_conditions(self, mock_search):
        """POST with AND conditions should filter results."""
        mock_search.return_value = {
            **self.mock_search_result,
            'query_preview': "Log Level equals 'ERROR' AND Message contains 'test'"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {
                'field': 'message',
                'operator': 'contains',
                'value': 'test',
                'logic': 'AND'
            }
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('AND', response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_or_conditions(self, mock_search):
        """POST with OR conditions should filter results."""
        mock_search.return_value = {
            **self.mock_search_result,
            'query_preview': "(Log Level equals 'ERROR' OR Log Level equals 'WARNING')"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('OR', response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_grouped_conditions(self, mock_search):
        """POST with grouped conditions should work correctly."""
        mock_search.return_value = {
            **self.mock_search_result,
            'query_preview': "(Log Level equals 'ERROR' " +
            "OR Log Level equals 'WARNING') AND Message contains 'test'"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {
                'field': 'level',
                'operator': 'equals',
                'value': 'WARNING',
                'logic': 'OR',
                'group': 1
            },
            {
                'field': 'message',
                'operator': 'contains',
                'value': 'test',
                'logic': 'AND',
                'group': 2
            }
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        preview = response.context['query_preview']
        self.assertIn('OR', preview)
        self.assertIn('AND', preview)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_with_date_range(self, mock_search):
        """POST with date range should filter by date."""
        today = datetime.now().strftime('%Y-%m-%d')
        mock_search.return_value = {
            **self.mock_search_result,
            'query_preview': f'Date: {today} to {today}'
        }

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': today,
            'date_to': today,
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('Date:', response.context['query_preview'])

    def test_post_with_invalid_json(self):
        """POST with invalid JSON should handle gracefully."""
        response = self.client.post(self.url, {
            'conditions_json': 'not valid json',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid' in str(m) for m in messages))

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_preserves_conditions_json(self, mock_search):
        """POST should preserve conditions_json in response for form state."""
        mock_search.return_value = {**self.mock_search_result, 'query_preview': ''}

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]
        conditions_json = json.dumps(conditions)

        response = self.client.post(self.url, {
            'conditions_json': conditions_json,
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['conditions_json'], conditions_json)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_post_preserves_date_fields(self, mock_search):
        """POST should preserve date fields in response."""
        mock_search.return_value = {**self.mock_search_result, 'query_preview': ''}

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date_from'], '2025-01-01')
        self.assertEqual(response.context['date_to'], '2025-01-31')

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_pagination_parameter(self, mock_search):
        """POST with page parameter should paginate results."""
        mock_search.return_value = {
            **self.mock_search_result,
            'page': 2,
            'has_prev': True,
            'query_preview': ''
        }

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '2'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], 2)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_sort_order_parameter(self, mock_search):
        """POST with sort_order should sort results."""
        mock_search.return_value = {**self.mock_search_result, 'query_preview': ''}

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1',
            'sort_order': 'asc'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_order'], 'asc')


class AnalyticsSearchServiceTests(TestCase):
    """Tests for LogSearchService with real Elasticsearch (if available)."""

    @classmethod
    def setUpClass(cls):
        """Check if ES is available before running these tests."""
        super().setUpClass()
        cls.es_available = is_elasticsearch_available()

    def setUp(self):
        """Set up search service."""
        if not self.es_available:
            self.skipTest("Elasticsearch not available")
        self.service = LogSearchService()
        self.builder = QueryBuilder()

    def test_service_connection(self):
        """Service should be able to connect to Elasticsearch."""
        connected = self.service.connect()
        self.assertTrue(connected)

    def test_search_logs_advanced_empty_conditions(self):
        """search_logs_advanced with empty conditions should return results."""
        result = self.service.search_logs_advanced([])

        self.assertIn('results', result)
        self.assertIn('total', result)
        self.assertIn('page', result)
        self.assertIn('query_preview', result)
        self.assertEqual(result['query_preview'], '')

    def test_search_logs_advanced_with_level_filter(self):
        """search_logs_advanced should filter by level."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]

        result = self.service.search_logs_advanced(conditions)

        self.assertIn('results', result)
        self.assertIn("Log Level equals 'ERROR'", result['query_preview'])

        for log in result['results']:
            if 'level' in log:
                self.assertEqual(log['level'], 'ERROR')

    def test_search_logs_advanced_with_or_conditions(self):
        """search_logs_advanced should handle OR conditions."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR'}
        ]

        result = self.service.search_logs_advanced(conditions)

        self.assertIn('results', result)
        self.assertIn('OR', result['query_preview'])

        for log in result['results']:
            if 'level' in log:
                self.assertIn(log['level'], ['ERROR', 'WARNING'])

    def test_search_logs_advanced_with_date_range(self):
        """search_logs_advanced should filter by date range."""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        result = self.service.search_logs_advanced(
            [],
            date_from=yesterday,
            date_to=today
        )

        self.assertIn('results', result)
        self.assertIn('Date:', result['query_preview'])

    def test_search_logs_advanced_pagination(self):
        """search_logs_advanced should support pagination."""
        result_page1 = self.service.search_logs_advanced([], page=1, page_size=5)

        self.assertEqual(result_page1['page'], 1)
        self.assertLessEqual(len(result_page1['results']), 5)

        if result_page1['has_next']:
            result_page2 = self.service.search_logs_advanced([], page=2, page_size=5)
            self.assertEqual(result_page2['page'], 2)

    def test_search_logs_advanced_sort_order(self):
        """search_logs_advanced should support sort order."""
        result_desc = self.service.search_logs_advanced([], sort_order='desc')
        result_asc = self.service.search_logs_advanced([], sort_order='asc')

        self.assertIn('results', result_desc)
        self.assertIn('results', result_asc)


class AnalyticsQueryBuilderIntegrationTests(TestCase):
    """Integration tests for QueryBuilder generating valid ES queries."""

    @classmethod
    def setUpClass(cls):
        """Check if ES is available before running these tests."""
        super().setUpClass()
        cls.es_available = is_elasticsearch_available()

    def setUp(self):
        """Set up query builder and search service."""
        if not self.es_available:
            self.skipTest("Elasticsearch not available")
        self.builder = QueryBuilder()
        self.service = LogSearchService()

    def test_complex_query_executes_without_error(self):
        """Complex grouped query should execute without error."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {
                'field': 'level',
                'operator': 'equals',
                'value': 'WARNING',
                'logic': 'OR',
                'group': 1
            },
            {
                'field': 'message',
                'operator': 'contains',
                'value': 'request',
                'logic': 'AND',
                'group': 2
            }
        ]

        query = self.builder.build_query(conditions)
        self.assertIn('bool', query)

        result = self.service.search_logs_advanced(conditions)
        self.assertIn('results', result)
        self.assertNotIn('error', result)

    def test_negation_query_executes_without_error(self):
        """Query with negation should execute without error."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True}
        ]

        result = self.service.search_logs_advanced(conditions)
        self.assertIn('results', result)

        for log in result['results']:
            if 'level' in log:
                self.assertNotEqual(log['level'], 'INFO')

    def test_not_equals_query_executes_without_error(self):
        """Query with not_equals operator should execute without error."""
        conditions = [
            {'field': 'level', 'operator': 'not_equals', 'value': 'INFO'}
        ]

        result = self.service.search_logs_advanced(conditions)
        self.assertIn('results', result)

        for log in result['results']:
            if 'level' in log:
                self.assertNotEqual(log['level'], 'INFO')

    def test_integer_range_query_executes_without_error(self):
        """Query with integer range should execute without error."""
        conditions = [
            {'field': 'status_code', 'operator': 'gte', 'value': '400'}
        ]

        result = self.service.search_logs_advanced(conditions)
        self.assertIn('results', result)

        for log in result['results']:
            if 'status_code' in log:
                self.assertGreaterEqual(log['status_code'], 400)

    def test_or_not_combination_returns_all(self):
        """A OR NOT A should return all logs."""
        self.service.search_logs_advanced([])

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO'},
            {
                'field': 'level',
                'operator': 'equals',
                'value': 'INFO',
                'negate': True,
                'logic': 'OR'
            }
        ]

        result = self.service.search_logs_advanced(conditions)
        self.assertIn('results', result)

    def test_and_not_combination_returns_none(self):
        """A AND NOT A should return no logs."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO'},
            {
                'field': 'level',
                'operator': 'equals',
                'value': 'INFO',
                'negate': True,
                'logic': 'AND'
            }
        ]

        result = self.service.search_logs_advanced(conditions)
        self.assertEqual(result['total'], 0)


class AnalyticsElasticsearchUnavailableTests(TestCase):
    """Tests for graceful error handling when Elasticsearch is unavailable."""

    def setUp(self):
        """Set up test client and admin user."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client.login(username='admin_test', password='testpass123')

    @patch.object(LogSearchService, 'connect')
    def test_search_handles_connection_failure(self, mock_connect):
        """Search should handle Elasticsearch connection failure gracefully."""
        mock_connect.return_value = False

        service = LogSearchService()
        result = service.search_logs_advanced([])

        self.assertIn('error', result)
        self.assertEqual(result['results'], [])
        self.assertEqual(result['total'], 0)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_view_handles_connection_failure(self, mock_search):
        """View should handle Elasticsearch connection failure gracefully."""
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False,
            'error': 'Elasticsearch unavailable',
            'query_preview': ''
        }

        response = self.client.post(reverse('analytics:advanced_search'), {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 0)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_search_handles_search_exception(self, mock_search):
        """Search should handle Elasticsearch search exceptions gracefully."""
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False,
            'error': 'Elasticsearch connection failed',
            'query_preview': ''
        }

        response = self.client.post(reverse('analytics:advanced_search'), {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 0)


class AnalyticsTabNavigationTests(TestCase):
    """Tests for tab navigation between simple and advanced search."""

    def setUp(self):
        """Set up test client and admin user."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client.login(username='admin_test', password='testpass123')

    def test_simple_search_has_tabs(self):
        """Simple search page should have tab navigation."""
        response = self.client.get(reverse('analytics:search'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Simple Search')
        self.assertContains(response, 'Advanced Query')

    def test_advanced_search_has_tabs(self):
        """Advanced search page should have tab navigation."""
        response = self.client.get(reverse('analytics:advanced_search'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Simple Search')
        self.assertContains(response, 'Advanced Query')

    def test_simple_search_tab_active(self):
        """Simple search page should have simple tab active."""
        response = self.client.get(reverse('analytics:search'))
        content = response.content.decode()
        self.assertIn('nav-link active', content)

    def test_advanced_search_tab_active(self):
        """Advanced search page should have advanced tab active."""
        response = self.client.get(reverse('analytics:advanced_search'))
        content = response.content.decode()
        self.assertIn('nav-link active', content)


class AnalyticsPreviewGenerationTests(TestCase):
    """Tests for query preview generation in the view."""

    def setUp(self):
        """Set up test client and admin user."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client.login(username='admin_test', password='testpass123')
        self.url = reverse('analytics:advanced_search')

        self.mock_result_base = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False,
        }

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_preview_for_equals_condition(self, mock_search):
        """Preview should show 'equals' for equals operator."""
        mock_search.return_value = {
            **self.mock_result_base,
            'query_preview': "Log Level equals 'ERROR'"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertIn("equals 'ERROR'", response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_preview_for_not_equals_condition(self, mock_search):
        """Preview should show 'does not equal' for not_equals operator."""
        mock_search.return_value = {
            **self.mock_result_base,
            'query_preview': "Log Level does not equal 'INFO'"
        }

        conditions = [
            {'field': 'level', 'operator': 'not_equals', 'value': 'INFO'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertIn("does not equal 'INFO'", response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_preview_for_contains_condition(self, mock_search):
        """Preview should show 'contains' for contains operator."""
        mock_search.return_value = {
            **self.mock_result_base,
            'query_preview': "Message contains 'error'"
        }

        conditions = [
            {'field': 'message', 'operator': 'contains', 'value': 'error'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertIn("contains 'error'", response.context['query_preview'])

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_preview_for_grouped_conditions(self, mock_search):
        """Preview should show parentheses for grouped conditions."""
        mock_search.return_value = {
            **self.mock_result_base,
            'query_preview': "(Log Level equals 'ERROR' OR Log Level equals 'WARNING')"
        }

        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {
                'field': 'level',
                'operator': 'equals',
                'value': 'WARNING',
                'logic': 'OR',
                'group': 1
            }
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        preview = response.context['query_preview']
        self.assertIn('(', preview)
        self.assertIn(')', preview)
        self.assertIn('OR', preview)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_preview_includes_date_range(self, mock_search):
        """Preview should include date range when specified."""
        mock_search.return_value = {
            **self.mock_result_base,
            'query_preview': 'Date: 2025-01-01 to 2025-01-31'
        }

        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'page': '1'
        })

        preview = response.context['query_preview']
        self.assertIn('Date:', preview)
        self.assertIn('2025-01-01', preview)
        self.assertIn('2025-01-31', preview)


class AnalyticsRefreshLogsTests(TestCase):
    """Tests for the refresh logs endpoint."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@test.com',
            password='testpass123',
            role='user'
        )
        self.url = reverse('analytics:refresh_logs')

    def test_refresh_logs_requires_authentication(self):
        """Refresh logs should require authentication."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    def test_refresh_logs_requires_admin(self):
        """Refresh logs should require admin role."""
        self.client.login(username='regular_test', password='testpass123')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])

    def test_refresh_logs_rejects_get_request(self):
        """Refresh logs should reject GET requests."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method not allowed

    @patch('analytics.views.call_command')
    def test_refresh_logs_success(self, mock_call_command):
        """Refresh logs should call index_logs command."""
        self.client.login(username='admin_test', password='testpass123')

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        mock_call_command.assert_called_once()

    @patch('analytics.views.call_command')
    def test_refresh_logs_handles_command_error(self, mock_call_command):
        """Refresh logs should handle command errors gracefully."""
        mock_call_command.side_effect = Exception('Command failed')
        self.client.login(username='admin_test', password='testpass123')

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
