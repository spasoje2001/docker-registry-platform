"""
Request logging middleware for capturing HTTP requests.
"""

import logging
import time

logger = logging.getLogger("access")


class RequestLoggingMiddleware:
    """
    Middleware that logs all HTTP requests with user context.

    Logs include: timestamp, level, logger_name, message, user, path, method,
    status_code, and response_time_ms.
    """

    SKIP_PATH_PREFIXES = (
        "/static/",
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip logging for static files
        if request.path.startswith(self.SKIP_PATH_PREFIXES):
            return self.get_response(request)

        start_time = time.time()

        response = self.get_response(request)

        response_time_ms = (time.time() - start_time) * 1000

        user = self._get_user(request)

        logger.info(
            "HTTP Request",
            extra={
                "user": user,
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "response_time_ms": round(response_time_ms, 2),
                "query_string": request.META.get("QUERY_STRING", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "ip_address": self._get_client_ip(request),
            },
        )

        return response

    def _get_user(self, request):
        """Extract username or return 'anonymous' for unauthenticated users."""
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user.username
        return "anonymous"

    def _get_client_ip(self, request):
        """Extract client IP address, considering proxy headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
