"""
Custom User model for the application.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    Roles (from FAQ):
    - SUPER_ADMIN: Created during setup, can create other admins
    - ADMIN: Can manage official repos and assign badges to users
    - USER: Regular authenticated user, can create personal repos

    Badges (assigned by admins):
    - is_verified_publisher: Verified Publisher badge
    - is_sponsored_oss: Sponsored OSS badge

    Setup requirement:
    - must_change_password: Forces password change on first login (for super admin)
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        USER = "user", "User"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    is_verified_publisher = models.BooleanField(default=False)
    is_sponsored_oss = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        """Check if user is admin or super admin."""
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]

    @property
    def is_super_admin(self):
        """Check if user is super admin."""
        return self.role == self.Role.SUPER_ADMIN