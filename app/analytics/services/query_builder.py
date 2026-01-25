"""
Query builder for constructing Elasticsearch DSL queries from UI conditions.

This module provides a QueryBuilder class that converts user-defined
search conditions (with AND/OR/NOT operators and grouping) into
Elasticsearch Query DSL format.
"""

from typing import Dict, List, Optional


class QueryBuilder:
    """
    Builds Elasticsearch queries from structured conditions.

    Supports:
    - Multiple field types (keyword, text, integer, date)
    - Logical operators (AND, OR)
    - Negation (NOT)
    - Grouping (parentheses via group IDs)
    """

    # Field definitions with their Elasticsearch types
    # Format: 'field_name': {'type': 'es_type', 'label': 'Human readable'}
    FIELDS = {
        'level': {
            'type': 'keyword',
            'label': 'Log Level',
            'choices': ['INFO', 'WARNING', 'ERROR']
        },
        'logger_name': {
            'type': 'keyword',
            'label': 'Logger Name',
            'choices': None
        },
        'message': {
            'type': 'text',
            'label': 'Message',
            'choices': None
        },
        'user': {
            'type': 'keyword',
            'label': 'User',
            'choices': None
        },
        'path': {
            'type': 'keyword',
            'label': 'Request Path',
            'choices': None
        },
        'method': {
            'type': 'keyword',
            'label': 'HTTP Method',
            'choices': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        },
        'status_code': {
            'type': 'integer',
            'label': 'Status Code',
            'choices': None
        },
        'log_source': {
            'type': 'keyword',
            'label': 'Log Source',
            'choices': ['app', 'access', 'error']
        },
    }

    # Operators available per field type
    # Format: 'field_type': [{'value': 'op_id', 'label': 'Human readable', 'es_type': 'term|match|range'}]
    OPERATORS = {
        'keyword': [
            {'value': 'equals', 'label': 'equals', 'es_type': 'term'},
            {'value': 'not_equals', 'label': 'does not equal', 'es_type': 'term_negated'},
        ],
        'text': [
            {'value': 'contains', 'label': 'contains', 'es_type': 'match'},
            {'value': 'not_contains', 'label': 'does not contain', 'es_type': 'match_negated'},
        ],
        'integer': [
            {'value': 'equals', 'label': 'equals', 'es_type': 'term'},
            {'value': 'not_equals', 'label': 'does not equal', 'es_type': 'term_negated'},
            {'value': 'gt', 'label': 'greater than', 'es_type': 'range'},
            {'value': 'gte', 'label': 'greater than or equal', 'es_type': 'range'},
            {'value': 'lt', 'label': 'less than', 'es_type': 'range'},
            {'value': 'lte', 'label': 'less than or equal', 'es_type': 'range'},
        ],
    }

    def __init__(self):
        """Initialize QueryBuilder."""
        pass

    def build_query(
            self,
            conditions: List[Dict],
            date_from: Optional[str] = None,
            date_to: Optional[str] = None
    ) -> Dict:
        """
        Build Elasticsearch query DSL from conditions.

        Args:
            conditions: List of condition dicts, each containing:
                - field: Field name (must be in FIELDS)
                - operator: Operator (must be valid for field type)
                - value: Search value
                - logic: 'AND' or 'OR' (optional, for 2nd+ conditions)
                - negate: bool (optional, wraps in must_not)
                - group: int (optional, for grouping with parentheses)
            date_from: Optional start date filter (YYYY-MM-DD)
            date_to: Optional end date filter (YYYY-MM-DD)

        Returns:
            Elasticsearch query DSL dict

        Example:
            conditions = [
                {'field': 'level', 'operator': 'equals', 'value': 'ERROR', 'group': 1},
                {'field': 'level', 'operator': 'equals', 'value': 'WARNING', 'logic': 'OR', 'group': 1},
                {'field': 'message', 'operator': 'contains', 'value': 'failed', 'logic': 'AND', 'group': 2}
            ]
            # Produces: (level=ERROR OR level=WARNING) AND message contains "failed"
            query = builder.build_query(conditions)
        """
        # No conditions - return all
        if not conditions:
            # Even with no conditions, we may have date filters
            date_clause = self._build_date_range_clause(date_from, date_to)
            if date_clause:
                return {
                    'bool': {
                        'must': [date_clause]
                    }
                }
            return {'match_all': {}}

        # Group conditions by group ID
        grouped = self._group_conditions(conditions)

        # Build query for each group
        group_queries = []
        group_ids = sorted(grouped.keys())

        for i, group_id in enumerate(group_ids):
            group_conditions = grouped[group_id]
            group_query = self._build_group_query(group_conditions)

            if group_query:
                # Inter-group logic: use logic from first condition of this group
                # (ignored for the very first group)
                if i == 0:
                    inter_logic = 'AND'  # First group has no preceding logic
                else:
                    inter_logic = group_conditions[0].get('logic', 'AND')

                group_queries.append({
                    'clause': group_query,
                    'logic': inter_logic,
                    'negate': False
                })

        # No valid groups produced
        if not group_queries:
            date_clause = self._build_date_range_clause(date_from, date_to)
            if date_clause:
                return {
                    'bool': {
                        'must': [date_clause]
                    }
                }
            return {'match_all': {}}

        # Build the base query
        if len(group_queries) == 1:
            base_query = group_queries[0]['clause']
        else:
            base_query = self._combine_clauses(group_queries)

        # Add date range filter if specified
        date_clause = self._build_date_range_clause(date_from, date_to)
        if date_clause:
            return self._add_date_filter(base_query, date_clause)

        return base_query

    def _build_date_range_clause(
            self,
            date_from: Optional[str],
            date_to: Optional[str]
    ) -> Optional[Dict]:
        """
        Build ES range clause for date filtering.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            ES range query dict or None if no dates provided
        """
        if not date_from and not date_to:
            return None

        date_range = {}

        if date_from:
            # Validate format
            try:
                from datetime import datetime
                datetime.strptime(date_from, '%Y-%m-%d')
                date_range['gte'] = f"{date_from}T00:00:00"
            except ValueError:
                pass  # Invalid format, skip

        if date_to:
            # Validate format
            try:
                from datetime import datetime
                datetime.strptime(date_to, '%Y-%m-%d')
                date_range['lte'] = f"{date_to}T23:59:59"
            except ValueError:
                pass  # Invalid format, skip

        if date_range:
            return {
                'range': {
                    'timestamp': date_range
                }
            }

        return None

    def _add_date_filter(self, base_query: Dict, date_clause: Dict) -> Dict:
        """
        Add date range filter to an existing query.

        Args:
            base_query: The existing ES query
            date_clause: The date range clause to add

        Returns:
            Combined query with date filter
        """
        # If base query is already a bool, add date to must
        if 'bool' in base_query:
            bool_query = base_query['bool'].copy()

            if 'must' in bool_query:
                # Add to existing must
                if isinstance(bool_query['must'], list):
                    bool_query['must'] = bool_query['must'] + [date_clause]
                else:
                    bool_query['must'] = [bool_query['must'], date_clause]
            else:
                # Create new must with date clause
                # Move should to a nested bool if present
                if 'should' in bool_query:
                    should_query = {
                        'bool': {
                            'should': bool_query.pop('should'),
                            'minimum_should_match': bool_query.pop('minimum_should_match', 1)
                        }
                    }
                    bool_query['must'] = [should_query, date_clause]
                else:
                    bool_query['must'] = [date_clause]

            return {'bool': bool_query}

        # Base query is a simple clause (term, match, etc.)
        # Wrap in bool with must
        return {
            'bool': {
                'must': [base_query, date_clause]
            }
        }

    def _group_conditions(self, conditions: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group conditions by their group ID.

        Args:
            conditions: List of condition dicts

        Returns:
            Dict mapping group_id to list of conditions in that group
        """
        groups = {}
        for condition in conditions:
            group_id = condition.get('group', 1)  # Default to group 1
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(condition)
        return groups

    def _build_group_query(self, group_conditions: List[Dict]) -> Optional[Dict]:
        """
        Build ES query for a single group of conditions.

        Args:
            group_conditions: List of conditions in the same group

        Returns:
            ES query dict for this group
        """
        clauses = []
        for condition in group_conditions:
            clause = self._build_clause(condition)
            if clause:
                clauses.append({
                    'clause': clause,
                    'logic': condition.get('logic', 'AND'),
                    'negate': condition.get('negate', False)
                })

        if not clauses:
            return None

        # Single clause in group
        if len(clauses) == 1:
            if clauses[0]['negate']:
                return {
                    'bool': {
                        'must_not': [clauses[0]['clause']]
                    }
                }
            return clauses[0]['clause']

        # Multiple clauses - combine within group
        return self._combine_clauses(clauses)

    def _combine_clauses(self, clauses: List[Dict]) -> Dict:
        """
        Combine multiple clauses into a bool query.

        Args:
            clauses: List of dicts with 'clause', 'logic', and 'negate' keys

        Returns:
            ES bool query dict
        """
        # Separate negated and non-negated clauses
        must_not_clauses = []
        regular_clauses = []

        for item in clauses:
            if item['negate']:
                must_not_clauses.append(item)
            else:
                regular_clauses.append(item)

        # Determine logic for regular clauses
        logics = [item['logic'].upper() for item in regular_clauses[1:]] if len(regular_clauses) > 1 else []

        all_and = all(logic == 'AND' for logic in logics) if logics else True
        all_or = all(logic == 'OR' for logic in logics) if logics else False

        # Build the bool query
        bool_query = {}

        # Handle regular (non-negated) clauses
        if regular_clauses:
            regular_clause_list = [item['clause'] for item in regular_clauses]

            if len(regular_clause_list) == 1:
                # Single regular clause goes to must
                bool_query['must'] = regular_clause_list
            elif all_or:
                bool_query['should'] = regular_clause_list
                bool_query['minimum_should_match'] = 1
            else:
                # AND or mixed -> must
                bool_query['must'] = regular_clause_list

        # Handle negated clauses (always go to must_not)
        if must_not_clauses:
            bool_query['must_not'] = [item['clause'] for item in must_not_clauses]

        if bool_query:
            return {'bool': bool_query}

        return {'match_all': {}}

    def _build_clause(self, condition: Dict) -> Optional[Dict]:
        """
        Build a single ES clause from a condition.

        Args:
            condition: Dict with field, operator, value keys

        Returns:
            ES clause dict or None if invalid
        """
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        # Validate field exists
        if field not in self.FIELDS:
            return None

        # Validate value is not empty
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        field_type = self.FIELDS[field]['type']

        # Build clause based on field type and operator
        if field_type == 'keyword':
            return self._build_keyword_clause(field, operator, value)
        elif field_type == 'text':
            return self._build_text_clause(field, operator, value)

        return None

    def _build_text_clause(self, field: str, operator: str, value: str) -> Optional[Dict]:
        """
        Build ES clause for text field.

        Args:
            field: Field name
            operator: 'contains' or 'not_contains'
            value: Value to search for

        Returns:
            ES match query dict
        """
        if operator == 'contains':
            return {
                'match': {
                    field: {
                        'query': value.strip(),
                        'operator': 'and'
                    }
                }
            }
        elif operator == 'not_contains':
            return {
                'bool': {
                    'must_not': [{
                        'match': {
                            field: {
                                'query': value.strip(),
                                'operator': 'and'
                            }
                        }
                    }]
                }
            }

        return None

    def _build_keyword_clause(self, field: str, operator: str, value: str) -> Optional[Dict]:
        """
        Build ES clause for keyword field.

        Args:
            field: Field name
            operator: 'equals' or 'not_equals'
            value: Value to match

        Returns:
            ES term query dict
        """
        if operator == 'equals':
            return {'term': {field: value}}
        elif operator == 'not_equals':
            return {
                'bool': {
                    'must_not': [{'term': {field: value}}]
                }
            }

        return None

    def generate_preview(
            self,
            conditions: List[Dict],
            date_from: Optional[str] = None,
            date_to: Optional[str] = None
    ) -> str:
        """
        Generate human-readable preview of the query.

        Args:
            conditions: List of condition dicts (same format as build_query)
            date_from: Optional start date filter (YYYY-MM-DD)
            date_to: Optional end date filter (YYYY-MM-DD)

        Returns:
            Human-readable string like:
            "(level = ERROR OR level = WARNING) AND message contains 'failed'"
        """
        if not conditions:
            if date_from or date_to:
                return self._format_date_range_preview(date_from, date_to)
            return ""

        # Group conditions by group ID
        grouped = self._group_conditions(conditions)
        group_ids = sorted(grouped.keys())

        # Build preview for each group
        group_previews = []

        for i, group_id in enumerate(group_ids):
            group_conditions = grouped[group_id]
            group_preview = self._generate_group_preview(group_conditions)

            if group_preview:
                # Inter-group logic
                if i == 0:
                    inter_logic = ""
                else:
                    inter_logic = group_conditions[0].get('logic', 'AND').upper()

                group_previews.append({
                    'preview': group_preview,
                    'logic': inter_logic
                })

        if not group_previews:
            if date_from or date_to:
                return self._format_date_range_preview(date_from, date_to)
            return ""

        # Combine group previews
        result_parts = []
        for i, item in enumerate(group_previews):
            if i > 0 and item['logic']:
                result_parts.append(f" {item['logic']} ")
            result_parts.append(item['preview'])

        result = "".join(result_parts)

        # Add date range if specified
        date_preview = self._format_date_range_preview(date_from, date_to)
        if date_preview:
            if result:
                result = f"{result} AND {date_preview}"
            else:
                result = date_preview

        return result

    def _generate_group_preview(self, group_conditions: List[Dict]) -> str:
        """
        Generate preview for a single group of conditions.

        Args:
            group_conditions: List of conditions in the same group

        Returns:
            Preview string, wrapped in parentheses if multiple conditions
        """
        condition_previews = []

        for i, condition in enumerate(group_conditions):
            preview = self._generate_condition_preview(condition)
            if preview:
                # Intra-group logic (between conditions in same group)
                if i == 0:
                    logic = ""
                else:
                    logic = condition.get('logic', 'AND').upper()

                condition_previews.append({
                    'preview': preview,
                    'logic': logic
                })

        if not condition_previews:
            return ""

        # Single condition - no parentheses needed
        if len(condition_previews) == 1:
            return condition_previews[0]['preview']

        # Multiple conditions - combine and wrap in parentheses
        parts = []
        for i, item in enumerate(condition_previews):
            if i > 0 and item['logic']:
                parts.append(f" {item['logic']} ")
            parts.append(item['preview'])

        return f"({''.join(parts)})"

    def _generate_condition_preview(self, condition: Dict) -> str:
        """
        Generate preview for a single condition.

        Args:
            condition: Condition dict with field, operator, value, negate

        Returns:
            Preview string like "level = ERROR" or "NOT message contains 'failed'"
        """
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        negate = condition.get('negate', False)

        # Validate
        if field not in self.FIELDS:
            return ""
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""

        # Get human-readable field label
        field_label = self.FIELDS[field]['label']

        # Get human-readable operator
        operator_label = self._get_operator_label(field, operator)
        if not operator_label:
            return ""

        # Format value
        if isinstance(value, str):
            value_formatted = f"'{value.strip()}'"
        else:
            value_formatted = str(value)

        # Build preview
        preview = f"{field_label} {operator_label} {value_formatted}"

        # Add NOT prefix if negated
        if negate:
            preview = f"NOT {preview}"

        return preview

    def _get_operator_label(self, field: str, operator: str) -> str:
        """
        Get human-readable label for an operator.

        Args:
            field: Field name
            operator: Operator value

        Returns:
            Human-readable operator label
        """
        field_info = self.FIELDS.get(field)
        if not field_info:
            return ""

        field_type = field_info['type']
        operators = self.OPERATORS.get(field_type, [])

        for op in operators:
            if op['value'] == operator:
                return op['label']

        return operator  # Fallback to raw operator

    def _format_date_range_preview(
            self,
            date_from: Optional[str],
            date_to: Optional[str]
    ) -> str:
        """
        Format date range for preview.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Preview string like "Date: 2025-01-01 to 2025-01-31"
        """
        if not date_from and not date_to:
            return ""

        if date_from and date_to:
            return f"Date: {date_from} to {date_to}"
        elif date_from:
            return f"Date: from {date_from}"
        else:
            return f"Date: until {date_to}"

    def get_fields_for_ui(self) -> List[Dict]:
        """
        Get field definitions formatted for UI dropdowns.

        Returns:
            List of dicts with 'value', 'label', 'type', 'choices' keys
        """
        return [
            {
                'value': field_name,
                'label': field_info['label'],
                'type': field_info['type'],
                'choices': field_info.get('choices')
            }
            for field_name, field_info in self.FIELDS.items()
        ]

    def get_operators_for_field(self, field_name: str) -> List[Dict]:
        """
        Get valid operators for a specific field.

        Args:
            field_name: Name of the field

        Returns:
            List of operator dicts with 'value' and 'label' keys
        """
        field_info = self.FIELDS.get(field_name)
        if not field_info:
            return []

        field_type = field_info['type']
        operators = self.OPERATORS.get(field_type, [])

        return [
            {'value': op['value'], 'label': op['label']}
            for op in operators
        ]