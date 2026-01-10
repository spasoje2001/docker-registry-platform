"""
Unit tests for logging configuration and request logging middleware.
"""
import json
import logging
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from ..middleware import RequestLoggingMiddleware

User = get_user_model()


class LoggingConfigurationTests(TestCase):
    """Tests for Django logging configuration."""

    def test_logs_directory_exists(self):
        """Verify logs directory is created."""
        logs_dir = settings.BASE_DIR / "logs"
        self.assertTrue(logs_dir.exists())

    def test_logging_config_has_required_handlers(self):
        """Verify all required handlers are configured."""
        handlers = settings.LOGGING["handlers"]

        required_handlers = ["app_file", "access_file", "error_file", "console"]
        for handler in required_handlers:
            self.assertIn(handler, handlers, f"Missing handler: {handler}")

    def test_logging_config_has_json_formatter(self):
        """Verify JSON formatter is configured."""
        formatters = settings.LOGGING["formatters"]

        self.assertIn("json", formatters)
        self.assertIn("json_access", formatters)

    def test_access_logger_exists(self):
        """Verify access logger is configured."""
        loggers = settings.LOGGING["loggers"]
        self.assertIn("access", loggers)

class RequestLoggingMiddlewareTests(TestCase):
    """Tests for RequestLoggingMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_middleware_logs_authenticated_request(self):
        """Verify middleware logs requests with authenticated user."""
        request = self.factory.get("/test-path/")
        request.user = self.user

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args

            self.assertEqual(call_args[0][0], "HTTP Request")

            extra = call_args[1]["extra"]
            self.assertEqual(extra["user"], "testuser")
            self.assertEqual(extra["path"], "/test-path/")
            self.assertEqual(extra["method"], "GET")
            self.assertEqual(extra["status_code"], 200)

    def test_middleware_logs_anonymous_request(self):
        """Verify middleware logs requests for anonymous users."""
        request = self.factory.get("/public-path/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]
            self.assertEqual(extra["user"], "anonymous")

    def test_middleware_captures_response_time(self):
        """Verify middleware captures response time."""
        request = self.factory.get("/test/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]
            self.assertIn("response_time_ms", extra)
            self.assertIsInstance(extra["response_time_ms"], float)

    def test_middleware_extracts_client_ip(self):
        """Verify middleware extracts client IP address."""
        request = self.factory.get("/test/")
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]
            self.assertEqual(extra["ip_address"], "192.168.1.1")

    def test_middleware_handles_x_forwarded_for(self):
        """Verify middleware handles X-Forwarded-For header from proxy."""
        request = self.factory.get("/test/")
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]
            self.assertEqual(extra["ip_address"], "10.0.0.1")

    def test_middleware_skips_static_paths(self):
        """Verify middleware does not log static file requests."""
        request = self.factory.get("/static/css/style.css")
        request.user = MagicMock()
        request.user.is_authenticated = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            # Logger should NOT be called for static paths
            mock_logger.info.assert_not_called()

    def test_middleware_skips_favicon(self):
        """Verify middleware does not log favicon requests."""
        request = self.factory.get("/favicon.ico")
        request.user = MagicMock()
        request.user.is_authenticated = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)
            mock_logger.info.assert_not_called()

    def test_middleware_logs_non_static_paths(self):
        """Verify middleware logs normal requests."""
        request = self.factory.get("/explore/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        def get_response(req):
            return mock_response

        middleware = RequestLoggingMiddleware(get_response)

        with patch("config.middleware.logger") as mock_logger:
            response = middleware(request)

            # Logger SHOULD be called for normal paths
            mock_logger.info.assert_called_once()


class LogOutputFormatTests(TestCase):
    """Tests for verifying log output format is valid JSON."""

    def test_app_logger_produces_valid_json(self):
        """Verify application logs are valid JSON format."""
        log_file = settings.BASE_DIR / "logs" / "app.log"

        app_logger = logging.getLogger("accounts")
        app_logger.info("Test log message for JSON validation")

        # Force handlers to flush
        for handler in app_logger.handlers:
            handler.flush()

        if log_file.exists() and log_file.stat().st_size > 0:
            with open(log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    try:
                        log_entry = json.loads(last_line)
                        self.assertIn("timestamp", log_entry)
                        self.assertIn("level", log_entry)
                        self.assertIn("logger_name", log_entry)
                        self.assertIn("message", log_entry)
                    except json.JSONDecodeError:
                        self.fail(f"Log entry is not valid JSON: {last_line}")