from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from datetime import datetime
import pytz
import json

from .services import LogSearchService


def format_timestamp(ts_string):
    """Convert ISO timestamp to local Serbia timezone (Europe/Belgrade)."""
    if not ts_string:
        return "-"
    try:
        # Parse ISO format: "2026-01-14T22:36:47.435000" or "2026-01-14T22:36:47"
        if 'T' in ts_string:
            # Remove microseconds and Z suffix if present
            ts_clean = ts_string.replace('Z', '').split('.')[0]

            # Parse as UTC datetime
            dt_utc = datetime.fromisoformat(ts_clean)

            # Make it timezone aware (assume UTC if naive)
            if dt_utc.tzinfo is None:
                utc_tz = pytz.UTC
                dt_utc = utc_tz.localize(dt_utc)

            # Convert to Serbia timezone (UTC+1 in winter, UTC+2 in summer)
            serbia_tz = pytz.timezone('Europe/Belgrade')
            dt_local = dt_utc.astimezone(serbia_tz)

            # Format: YYYY-MM-DD HH:MM:SS
            return dt_local.strftime('%Y-%m-%d %H:%M:%S')

        return ts_string
    except (ValueError, AttributeError) as e:
        return ts_string


@login_required
def log_search(request):
    """
    Analytics log search view.

    Admin-only access. Allows searching and filtering logs from Elasticsearch.
    """
    # Check admin permission
    if not request.user.is_admin:
        messages.warning(request, "You do not have permission to access this page.")
        return redirect("core:home")

    # Get search parameters
    query = request.GET.get('q', '').strip()
    level = request.GET.get('level', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    page = request.GET.get('page', '1')
    sort_order = request.GET.get('sort', 'desc')  # ADD THIS LINE

    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    # Convert page to int
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    # Initialize search service
    search_service = LogSearchService()

    # Perform search
    search_results = search_service.search_logs(
        query=query if query else None,
        level=level if level else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        page=page,
        page_size=20,
        sort_order=sort_order
    )

    # Handle errors
    if 'error' in search_results:
        messages.error(request, search_results['error'])

    # Format timestamps for display
    for result in search_results.get('results', []):
        if 'timestamp' in result:
            result['timestamp_formatted'] = format_timestamp(result['timestamp'])

    # Build pagination range (show max 10 page numbers)
    total_pages = search_results['total_pages']
    current_page = search_results['page']

    # Calculate page range to show
    page_range = []  # noqa - Used in template context
    if total_pages <= 10:
        page_range = range(1, total_pages + 1)
    else:
        # Show pages around current page
        start = max(1, current_page - 4)
        end = min(total_pages, current_page + 5)
        page_range = range(start, end + 1)

    context = {
        'results': search_results['results'],
        'total': search_results['total'],
        'page': current_page,
        'total_pages': total_pages,
        'has_next': search_results['has_next'],
        'has_prev': search_results['has_prev'],
        'page_range': page_range,
        # Preserve form values
        'query': query,
        'level': level,
        'date_from': date_from,
        'date_to': date_to,
        'sort_order': sort_order,
    }

    return render(request, 'analytics/search.html', context)

@login_required
def advanced_search(request):
    """Advanced analytics log search with query builder. Admin-only access."""
    if not request.user.is_admin:
        messages.warning(request, "You do not have permission to access this page.")
        return redirect("core:home")

    # Default context
    context = {
        'results': [],
        'total': 0,
        'page': 1,
        'total_pages': 0,
        'has_next': False,
        'has_prev': False,
        'page_range': [],
        'query_preview': '',
        'conditions_json': '[]',
        'date_from': '',
        'date_to': '',
        'sort_order': 'desc',
    }

    if request.method == 'POST':
        # Parse form data
        conditions_json = request.POST.get('conditions_json', '[]').strip()
        date_from = request.POST.get('date_from', '').strip()
        date_to = request.POST.get('date_to', '').strip()
        sort_order = request.POST.get('sort_order', 'desc')
        page = request.POST.get('page', '1')

        # Validate sort order
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'

        # Parse page number
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1

        # Parse conditions JSON
        try:
            conditions = json.loads(conditions_json)
            if not isinstance(conditions, list):
                conditions = []
        except (json.JSONDecodeError, TypeError):
            conditions = []
            messages.warning(request, "Invalid query format. Using empty query.")

        # Perform search
        search_service = LogSearchService()
        search_results = search_service.search_logs_advanced(
            conditions=conditions,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            page=page,
            page_size=20,
            sort_order=sort_order
        )

        # Handle errors
        if 'error' in search_results:
            messages.error(request, search_results['error'])

        # Format timestamps
        for result in search_results.get('results', []):
            if 'timestamp' in result:
                result['timestamp_formatted'] = format_timestamp(result['timestamp'])

        # Build page range for pagination
        total_pages = search_results['total_pages']
        current_page = search_results['page']

        if total_pages <= 10:
            page_range = range(1, total_pages + 1)
        else:
            start = max(1, current_page - 4)
            end = min(total_pages, current_page + 5)
            page_range = range(start, end + 1)

        # Update context with results
        context.update({
            'results': search_results['results'],
            'total': search_results['total'],
            'page': current_page,
            'total_pages': total_pages,
            'has_next': search_results['has_next'],
            'has_prev': search_results['has_prev'],
            'page_range': page_range,
            'query_preview': search_results.get('query_preview', ''),
            'conditions_json': conditions_json,
            'date_from': date_from,
            'date_to': date_to,
            'sort_order': sort_order,
        })

    return render(request, 'analytics/advanced_search.html', context)