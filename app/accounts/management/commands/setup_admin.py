"""
Django management command to create super administrator account.

Usage:
    python manage.py setup_admin
    python manage.py setup_admin --username=myadmin
"""

import os
import secrets
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """Create super administrator account with random password."""

    help = "Creates a super administrator account with a random password"

    def add_arguments(self, parser):
        """Add optional command arguments."""
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="Username for the super admin (default: admin)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        username = options["username"]

        # Check if super admin already exists
        if User.objects.filter(role=User.Role.SUPER_ADMIN).exists():
            existing_admin = User.objects.get(role=User.Role.SUPER_ADMIN)
            self.stdout.write(
                self.style.WARNING(
                    f"Super admin already exists: {existing_admin.username}. "
                    f"Skipping creation."
                )
            )
            return

        # Generate secure random password
        password = self._generate_password()

        # Create super admin user
        User.objects.create_user(
            username=username,
            password=password,
            role=User.Role.SUPER_ADMIN,
            must_change_password=True,
            is_superuser=True,
            is_staff=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created super admin: {username}")
        )

        # Write password to file
        password_file_path = self._get_password_file_path()
        self._write_password_to_file(password_file_path, username, password)

        self.stdout.write(
            self.style.SUCCESS(f"Password written to: {password_file_path}")
        )
        self.stdout.write(
            self.style.WARNING(
                "IMPORTANT: Super admin must change password on first login!"
            )
        )

    def _generate_password(self, length=20):
        """
        Generate a secure random password.

        Args:
            length: Password length (default: 20)

        Returns:
            Randomly generated password string
        """
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        return password

    def _get_password_file_path(self):
        """
        Get the path for the password file.

        Priority order:
        1. ADMIN_PASSWORD_FILE environment variable
        2. ADMIN_PASSWORD_FILE in settings
        3. Default: project_root/admin_password.txt

        Returns:
            Absolute path to password file
        """
        # Check environment variable first
        path = os.environ.get("ADMIN_PASSWORD_FILE")

        if not path:
            # Check Django settings
            path = getattr(settings, "ADMIN_PASSWORD_FILE", None)

        if not path:
            # Default to project root (one level above app directory)
            base_dir = settings.BASE_DIR
            path = os.path.join(base_dir.parent, "admin_password.txt")

        return path

    def _write_password_to_file(self, file_path, username, password):
        """
        Write password to file with restrictive permissions.

        Args:
            file_path: Path where to write the file
            username: Admin username
            password: Admin password

        Raises:
            Exception: If file writing fails
        """
        try:
            with open(file_path, "w") as f:
                f.write("Super Admin Credentials\n")
                f.write("========================\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                f.write("\nIMPORTANT: Change this password on first login!\n")

            # Set restrictive permissions (owner read/write only)
            os.chmod(file_path, 0o600)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to write password file: {str(e)}")
            )
            raise
