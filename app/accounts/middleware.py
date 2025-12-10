from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class ForcePasswordChangeMiddleware:
    """
    Middleware to force users to change password before accessing the application.

    Users with must_change_password=True are redirected to the password change page.
    This is primarily used for the super admin on first login.

    Excluded URLs:
    - Password change page (to avoid redirect loop)
    - Login page
    - Logout page
    - Static/media files
    - Admin site (optional - Django admin has its own password change)
    """

    def __init__(self, get_response):
        """
        Initialize middleware.

        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response

        self.excluded_paths = [
            reverse('accounts:password_change'),
            reverse('accounts:password_change_done'),
        ]

        self.excluded_prefixes = [
            '/static/',
            '/media/',
            '/admin/',
        ]

    def __call__(self, request):
        """
        Process each request.

        Args:
            request: The HTTP request object

        Returns:
            HTTP response (either redirect or continue to next middleware/view)
        """
        if (
                request.user.is_authenticated
                and hasattr(request.user, 'must_change_password')
                and request.user.must_change_password
        ):
            if not self._is_excluded_path(request.path):
                return redirect('accounts:password_change')

        response = self.get_response(request)
        return response

    def _is_excluded_path(self, path):
        # Check exact path matches
        if path in self.excluded_paths:
            return True

        # Check path prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False