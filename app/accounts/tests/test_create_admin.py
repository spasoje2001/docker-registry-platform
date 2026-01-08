from django.contrib.messages import get_messages
from django.test import TestCase, Client
from django.urls import reverse

from ..forms import CreateAdminForm
from ..models import User


class CreateAdminViewTests(TestCase):
    """Test suite for admin creation functionality."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()

        # Create super admin
        self.super_admin = User.objects.create_user(
            username="superadmin",
            email="super@example.com",
            password="SuperPass123!",
            role=User.Role.SUPER_ADMIN,
            must_change_password=False,
        )

        # Create regular admin
        self.admin = User.objects.create_user(
            username="regularadmin",
            email="admin@example.com",
            password="AdminPass123!",
            role=User.Role.ADMIN,
            must_change_password=False,
        )

        # Create regular user
        self.user = User.objects.create_user(
            username="regularuser",
            email="user@example.com",
            password="UserPass123!",
            role=User.Role.USER,
        )

        self.create_admin_url = reverse("accounts:create_admin")
        self.admin_panel_url = reverse("accounts:admin_panel")

    def test_super_admin_can_access_create_admin_page(self):
        """Super admin should be able to access the create admin page."""
        self.client.login(username="superadmin", password="SuperPass123!")
        response = self.client.get(self.create_admin_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/create_admin.html")
        self.assertContains(response, "Create Admin User")

    def test_regular_admin_cannot_access_create_admin_page(self):
        """Regular admin should NOT be able to access create admin page."""
        self.client.login(username="regularadmin", password="AdminPass123!")
        response = self.client.get(self.create_admin_url)

        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertRedirects(response, self.admin_panel_url)

        # Check warning message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Only super administrators", str(messages[0]))

    def test_regular_user_cannot_access_create_admin_page(self):
        """Regular user should NOT be able to access create admin page."""
        self.client.login(username="regularuser", password="UserPass123!")
        response = self.client.get(self.create_admin_url, follow=True)

        # Should redirect (either to admin_panel then to home, or directly to home)
        self.assertEqual(response.status_code, 200)

        # Check that warning message exists about permissions
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("permission" in str(m).lower() for m in messages),
            "Expected permission warning message",
        )

    def test_unauthenticated_user_cannot_access_create_admin_page(self):
        """Unauthenticated user should be redirected to login."""
        response = self.client.get(self.create_admin_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_create_admin_with_generated_password_success(self):
        """Super admin can create admin with auto-generated password."""
        self.client.login(username="superadmin", password="SuperPass123!")

        initial_admin_count = User.objects.filter(role=User.Role.ADMIN).count()

        form_data = {
            "username": "newadmin",
            "email": "newadmin@example.com",
            "first_name": "New",
            "last_name": "Admin",
            "generate_password": True,
        }

        response = self.client.post(self.create_admin_url, form_data)

        # Should redirect to success page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:create_admin_success"))

        # Check admin was created
        self.assertEqual(
            User.objects.filter(role=User.Role.ADMIN).count(), initial_admin_count + 1
        )

        new_admin = User.objects.get(username="newadmin")
        self.assertEqual(new_admin.email, "newadmin@example.com")
        self.assertEqual(new_admin.first_name, "New")
        self.assertEqual(new_admin.last_name, "Admin")
        self.assertEqual(new_admin.role, User.Role.ADMIN)
        self.assertTrue(new_admin.must_change_password)

        # Check password is set (not empty)
        self.assertTrue(new_admin.has_usable_password())

    def test_create_admin_with_manual_password_success(self):
        """Super admin can create admin with manually provided password."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "manualadmin",
            "email": "manual@example.com",
            "first_name": "Manual",
            "last_name": "Admin",
            "generate_password": False,
            "password": "ManualPass123!",
            "password_confirm": "ManualPass123!",
        }

        response = self.client.post(self.create_admin_url, form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:create_admin_success"))

        # Check admin was created
        new_admin = User.objects.get(username="manualadmin")
        self.assertEqual(new_admin.role, User.Role.ADMIN)
        self.assertTrue(new_admin.must_change_password)

        # Verify password works
        self.assertTrue(new_admin.check_password("ManualPass123!"))

    def test_create_admin_missing_email_fails(self):
        """Creating admin without email should fail."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "noemail",
            "email": "",  # Missing email
            "generate_password": True,
        }

        response = self.client.post(self.create_admin_url, form_data)

        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)

        # Django 5.x API - access form from context
        form = response.context["form"]
        self.assertFormError(form, "email", "This field is required.")

        # Admin should NOT be created
        self.assertFalse(User.objects.filter(username="noemail").exists())

    def test_create_admin_password_mismatch_fails(self):
        """Creating admin with mismatched passwords should fail."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "mismatch",
            "email": "mismatch@example.com",
            "generate_password": False,
            "password": "Password123!",
            "password_confirm": "DifferentPass123!",
        }

        response = self.client.post(self.create_admin_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")
        self.assertFalse(User.objects.filter(username="mismatch").exists())

    def test_create_admin_weak_password_fails(self):
        """Creating admin with weak password should fail."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "weakpass",
            "email": "weak@example.com",
            "generate_password": False,
            "password": "123",  # Too short
            "password_confirm": "123",
        }

        response = self.client.post(self.create_admin_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password validation failed")
        self.assertFalse(User.objects.filter(username="weakpass").exists())

    def test_create_admin_no_password_provided_fails(self):
        """Creating admin without password and not generating should fail."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "nopass",
            "email": "nopass@example.com",
            "generate_password": False,
            "password": "",
            "password_confirm": "",
        }

        response = self.client.post(self.create_admin_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You must provide a password")
        self.assertFalse(User.objects.filter(username="nopass").exists())

    def test_create_admin_duplicate_username_fails(self):
        """Creating admin with existing username should fail."""
        self.client.login(username="superadmin", password="SuperPass123!")

        form_data = {
            "username": "regularadmin",  # Already exists
            "email": "different@example.com",
            "generate_password": True,
        }

        response = self.client.post(self.create_admin_url, form_data)

        self.assertEqual(response.status_code, 200)

        # Check form has username error
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

        # Check error message contains 'username' and 'exists'
        error_message = str(form.errors["username"])
        self.assertIn("username", error_message.lower())
        self.assertIn("exists", error_message.lower())

    def test_success_page_displays_credentials(self):
        """Success page should display generated credentials."""
        self.client.login(username="superadmin", password="SuperPass123!")

        # Create admin
        form_data = {
            "username": "testadmin",
            "email": "test@example.com",
            "generate_password": True,
        }
        self.client.post(self.create_admin_url, form_data)

        # Visit success page
        response = self.client.get(reverse("accounts:create_admin_success"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/create_admin_success.html")
        self.assertContains(response, "testadmin")
        self.assertContains(response, "Admin User Created Successfully")

    def test_success_page_clears_credentials_from_session(self):
        """Credentials should be cleared after viewing success page."""
        self.client.login(username="superadmin", password="SuperPass123!")

        # Create admin
        form_data = {
            "username": "cleartest",
            "email": "clear@example.com",
            "generate_password": True,
        }
        self.client.post(self.create_admin_url, form_data)

        # First visit - should show credentials
        response1 = self.client.get(reverse("accounts:create_admin_success"))
        self.assertContains(response1, "cleartest")

        # Second visit - credentials should be cleared
        response2 = self.client.get(reverse("accounts:create_admin_success"))
        self.assertRedirects(response2, self.admin_panel_url)

    def test_regular_admin_cannot_access_success_page(self):
        """Regular admin should not access success page."""
        self.client.login(username="regularadmin", password="AdminPass123!")

        response = self.client.get(reverse("accounts:create_admin_success"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.admin_panel_url)


class CreateAdminFormTests(TestCase):
    """Test suite for CreateAdminForm."""

    def test_form_valid_with_generated_password(self):
        """Form should be valid with generated password option."""
        form_data = {
            "username": "testadmin",
            "email": "test@example.com",
            "generate_password": True,
        }
        form = CreateAdminForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_valid_with_manual_password(self):
        """Form should be valid with manual password."""
        form_data = {
            "username": "testadmin",
            "email": "test@example.com",
            "generate_password": False,
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
        }
        form = CreateAdminForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_email(self):
        """Form should be invalid without email."""
        form_data = {
            "username": "testadmin",
            "email": "",
            "generate_password": True,
        }
        form = CreateAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_invalid_password_mismatch(self):
        """Form should be invalid if passwords don't match."""
        form_data = {
            "username": "testadmin",
            "email": "test@example.com",
            "generate_password": False,
            "password": "Pass123!",
            "password_confirm": "Different123!",
        }
        form = CreateAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Passwords do not match", str(form.non_field_errors()))

    def test_generated_password_format(self):
        """Generated password should meet security requirements."""
        password = CreateAdminForm.generate_random_password()

        # Check length
        self.assertEqual(len(password), 16)

        # Check contains required character types
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(not c.isalnum() for c in password))

    def test_generated_password_is_random(self):
        """Each generated password should be unique."""
        password1 = CreateAdminForm.generate_random_password()
        password2 = CreateAdminForm.generate_random_password()

        self.assertNotEqual(password1, password2)
