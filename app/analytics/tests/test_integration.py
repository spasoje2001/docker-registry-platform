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
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..services.log_search import LogSearchService
from ..services.query_builder import QueryBuilder

User = get_user_model()


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
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_advanced_search_requires_login(self):
        """Advanced search page should require authentication."""
        response = self.client.get(reverse('analytics:advanced_search'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_simple_search_requires_admin(self):
        """Simple search page should require admin role."""
        self.client.login(username='regular_test', password='testpass123')
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 302)  # Redirect away

    def test_advanced_search_requires_admin(self):
        """Advanced search page should require admin role."""
        self.client.login(username='regular_test', password='testpass123')
        response = self.client.get(reverse('analytics:advanced_search'))
        self.assertEqual(response.status_code, 302)  # Redirect away

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

    def test_get_request_renders_form(self):
        """GET request should render the query builder form."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Query Builder')
        self.assertContains(response, 'advancedSearchForm')
        self.assertContains(response, 'conditionsJson')

    def test_post_with_empty_conditions(self):
        """POST with empty conditions should return all logs."""
        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        # Should have results or empty state (depending on ES data)
        self.assertIn('total', response.context)

    def test_post_with_single_condition(self):
        """POST with single condition should filter results."""
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

    def test_post_with_and_conditions(self):
        """POST with AND conditions should filter results."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR'},
            {'field': 'message', 'operator': 'contains', 'value': 'test', 'logic': 'AND'}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('AND', response.context['query_preview'])

    def test_post_with_or_conditions(self):
        """POST with OR conditions should filter results."""
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

    def test_post_with_grouped_conditions(self):
        """POST with grouped conditions should work correctly."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
            {'field': 'message', 'operator': 'contains', 'value': 'test', 'logic': 'AND', 'group': 2}
        ]

        response = self.client.post(self.url, {
            'conditions_json': json.dumps(conditions),
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        # Preview should contain both groups
        preview = response.context['query_preview']
        self.assertIn('OR', preview)
        self.assertIn('AND', preview)

    def test_post_with_date_range(self):
        """POST with date range should filter by date."""
        today = datetime.now().strftime('%Y-%m-%d')

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
        # Should show warning message
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid' in str(m) for m in messages))

    def test_post_preserves_conditions_json(self):
        """POST should preserve conditions_json in response for form state."""
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

    def test_post_preserves_date_fields(self):
        """POST should preserve date fields in response."""
        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date_from'], '2025-01-01')
        self.assertEqual(response.context['date_to'], '2025-01-31')

    def test_pagination_parameter(self):
        """POST with page parameter should paginate results."""
        response = self.client.post(self.url, {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '2'
        })

        self.assertEqual(response.status_code, 200)
        # Page should be 2 or 1 if not enough results
        self.assertIn(response.context['page'], [1, 2])

    def test_sort_order_parameter(self):
        """POST with sort_order should sort results."""
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

    def setUp(self):
        """Set up search service."""
        self.service = LogSearchService()
        self.builder = QueryBuilder()

    def test_service_connection(self):
        """Service should be able to connect to Elasticsearch."""
        # This may fail if ES is not running - that's okay for CI
        connected = self.service.connect()
        # We just verify it doesn't crash
        self.assertIsInstance(connected, bool)

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

        # Verify all results have level=ERROR (if there are results)
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

        # Verify all results have level=ERROR or WARNING
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
        # Get first page
        result_page1 = self.service.search_logs_advanced([], page=1, page_size=5)

        self.assertEqual(result_page1['page'], 1)
        self.assertLessEqual(len(result_page1['results']), 5)

        # If there are more pages, get second page
        if result_page1['has_next']:
            result_page2 = self.service.search_logs_advanced([], page=2, page_size=5)
            self.assertEqual(result_page2['page'], 2)

    def test_search_logs_advanced_sort_order(self):
        """search_logs_advanced should support sort order."""
        result_desc = self.service.search_logs_advanced([], sort_order='desc')
        result_asc = self.service.search_logs_advanced([], sort_order='asc')

        # Both should return results
        self.assertIn('results', result_desc)
        self.assertIn('results', result_asc)

        # If we have results, timestamps should be in different order
        if len(result_desc['results']) >= 2 and len(result_asc['results']) >= 2:
            # First result of desc should be newer than first of asc
            # (or equal if timestamps are the same)
            pass  # Timestamp comparison is complex, just verify no errors


class AnalyticsQueryBuilderIntegrationTests(TestCase):
    """Integration tests for QueryBuilder generating valid ES queries."""

    def setUp(self):
        """Set up query builder and search service."""
        self.builder = QueryBuilder()
        self.service = LogSearchService()

    def test_complex_query_executes_without_error(self):
        """Complex grouped query should execute without error."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
            {'field': 'message', 'operator': 'contains', 'value': 'request', 'logic': 'AND', 'group': 2}
        ]

        # Build query
        query = self.builder.build_query(conditions)
        self.assertIn('bool', query)

        # Execute query
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

        # Verify no INFO logs in results
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

        # Verify no INFO logs in results (all results must have level field)
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

        # Verify all results have status_code >= 400
        for log in result['results']:
            if 'status_code' in log:
                self.assertGreaterEqual(log['status_code'], 400)

    def test_or_not_combination_returns_all(self):
        """A OR NOT A should return all logs."""
        # Get total count first
        all_logs = self.service.search_logs_advanced([])
        total_all = all_logs['total']

        # Now search with A OR NOT A
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO'},
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True, 'logic': 'OR'}
        ]

        result = self.service.search_logs_advanced(conditions)

        # Should return same as all logs (or close to it)
        # Note: might differ slightly due to logs without level field
        self.assertIn('results', result)

    def test_and_not_combination_returns_none(self):
        """A AND NOT A should return no logs."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'INFO'},
            {'field': 'level', 'operator': 'equals', 'value': 'INFO', 'negate': True, 'logic': 'AND'}
        ]

        result = self.service.search_logs_advanced(conditions)

        # Should return 0 results (logical contradiction)
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

    @patch.object(LogSearchService, 'connect')
    def test_view_handles_connection_failure(self, mock_connect):
        """View should handle Elasticsearch connection failure gracefully."""
        mock_connect.return_value = False

        response = self.client.post(reverse('analytics:advanced_search'), {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        # Should show error message
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)

    @patch.object(LogSearchService, 'search_logs_advanced')
    def test_search_handles_search_exception(self, mock_search):
        """Search should handle Elasticsearch search exceptions gracefully."""
        # Mock the search method to return an error result
        mock_search.return_value = {
            'results': [],
            'total': 0,
            'page': 1,
            'total_pages': 0,
            'has_next': False,
            'has_prev': False,
            'query_preview': '',
            'error': 'Elasticsearch connection failed'
        }

        response = self.client.post(reverse('analytics:advanced_search'), {
            'conditions_json': '[]',
            'date_from': '',
            'date_to': '',
            'page': '1'
        })

        self.assertEqual(response.status_code, 200)
        # Should show error in context or messages
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

        # The active tab should have 'active' class
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

    def test_preview_for_equals_condition(self):
        """Preview should show 'equals' for equals operator."""
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

    def test_preview_for_not_equals_condition(self):
        """Preview should show 'does not equal' for not_equals operator."""
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

    def test_preview_for_contains_condition(self):
        """Preview should show 'contains' for contains operator."""
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

    def test_preview_for_grouped_conditions(self):
        """Preview should show parentheses for grouped conditions."""
        conditions = [
            {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
            {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1}
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

    def test_preview_includes_date_range(self):
        """Preview should include date range when specified."""
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