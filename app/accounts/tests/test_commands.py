"""Tests for Django management commands in accounts app."""

import os
import sys
import tempfile
import unittest

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from io import StringIO

User = get_user_model()


class SetupAdminCommandTest(TestCase):
    """Test cases for setup_admin management command."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for password files
        self.temp_dir = tempfile.mkdtemp()
        self.password_file = os.path.join(self.temp_dir, "test_admin_password.txt")

    def tearDown(self):
        """Clean up after tests."""
        # Remove password file if it exists
        if os.path.exists(self.password_file):
            os.remove(self.password_file)

        # Remove temp directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

        # Clean up environment variable
        if "ADMIN_PASSWORD_FILE" in os.environ:
            del os.environ["ADMIN_PASSWORD_FILE"]

    def test_command_creates_super_admin(self):
        """Test that command creates super admin when none exists."""
        # Ensure no super admin exists
        self.assertEqual(User.objects.filter(role=User.Role.SUPER_ADMIN).count(), 0)

        # Set environment variable for password file
        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        out = StringIO()
        call_command("setup_admin", stdout=out)

        # Check that super admin was created
        self.assertEqual(User.objects.filter(role=User.Role.SUPER_ADMIN).count(), 1)

        admin = User.objects.get(role=User.Role.SUPER_ADMIN)
        self.assertEqual(admin.username, "admin")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.must_change_password)
        self.assertEqual(admin.role, User.Role.SUPER_ADMIN)

        # Check output messages
        output = out.getvalue()
        self.assertIn("Successfully created super admin", output)
        self.assertIn("Password written to", output)
        self.assertIn("IMPORTANT", output)

    def test_command_skips_if_admin_exists(self):
        """Test that command skips creation if super admin already exists."""
        # Create existing super admin
        User.objects.create_user(
            username="existing_admin",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            is_superuser=True,
            is_staff=True,
        )

        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        out = StringIO()
        call_command("setup_admin", stdout=out)

        # Check that no new admin was created
        self.assertEqual(User.objects.filter(role=User.Role.SUPER_ADMIN).count(), 1)

        # Verify it's still the original admin
        admin = User.objects.get(role=User.Role.SUPER_ADMIN)
        self.assertEqual(admin.username, "existing_admin")

        # Check output message
        output = out.getvalue()
        self.assertIn("Super admin already exists", output)
        self.assertIn("existing_admin", output)

        # Password file should not be created
        self.assertFalse(os.path.exists(self.password_file))

    def test_password_file_created_with_correct_content(self):
        """Test that password file is created with correct content."""
        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        call_command("setup_admin", stdout=StringIO())

        # Check that password file exists
        self.assertTrue(os.path.exists(self.password_file))

        # Read and verify content
        with open(self.password_file, "r") as f:
            content = f.read()

        self.assertIn("Super Admin Credentials", content)
        self.assertIn("Username: admin", content)
        self.assertIn("Password:", content)
        self.assertIn("IMPORTANT: Change this password on first login!", content)

        # Verify password works
        admin = User.objects.get(role=User.Role.SUPER_ADMIN)

        # Extract password from file
        lines = content.split("\n")
        password_line = [line for line in lines if line.startswith("Password:")][0]
        password = password_line.split("Password: ")[1]

        # Verify the password is valid
        self.assertTrue(admin.check_password(password))
        # Verify password has reasonable length
        self.assertGreaterEqual(len(password), 20)

    @unittest.skipIf(
        sys.platform.startswith("win"),
        "File permissions test not applicable on Windows",
    )
    def test_password_file_permissions(self):
        """Test that password file has restrictive permissions."""
        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        call_command("setup_admin", stdout=StringIO())

        # Check file permissions (Unix-like systems only)
        if hasattr(os, "chmod"):
            file_stat = os.stat(self.password_file)
            # Check that file is readable/writable by owner only (0o600)
            self.assertEqual(file_stat.st_mode & 0o777, 0o600)

    def test_custom_username(self):
        """Test creating super admin with custom username."""
        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        call_command("setup_admin", "--username=superadmin", stdout=StringIO())

        admin = User.objects.get(role=User.Role.SUPER_ADMIN)
        self.assertEqual(admin.username, "superadmin")

        # Verify in password file
        with open(self.password_file, "r") as f:
            content = f.read()
        self.assertIn("Username: superadmin", content)

    @override_settings(ADMIN_PASSWORD_FILE=None)
    def test_password_file_path_from_settings(self):
        """Test that password file path can be configured via settings."""
        custom_path = os.path.join(self.temp_dir, "custom_password.txt")

        with override_settings(ADMIN_PASSWORD_FILE=custom_path):
            call_command("setup_admin", stdout=StringIO())

            self.assertTrue(os.path.exists(custom_path))

            # Clean up
            os.remove(custom_path)

    def test_idempotent_multiple_runs(self):
        """Test that running command multiple times is safe."""
        os.environ["ADMIN_PASSWORD_FILE"] = self.password_file

        # Run command first time
        call_command("setup_admin", stdout=StringIO())
        first_admin = User.objects.get(role=User.Role.SUPER_ADMIN)
        first_admin_id = first_admin.id

        # Run command second time
        out = StringIO()
        call_command("setup_admin", stdout=out)

        # Should still be only one admin
        self.assertEqual(User.objects.filter(role=User.Role.SUPER_ADMIN).count(), 1)

        # Should be the same admin
        admin = User.objects.get(role=User.Role.SUPER_ADMIN)
        self.assertEqual(admin.id, first_admin_id)

        # Output should indicate skipping
        output = out.getvalue()
        self.assertIn("already exists", output)
