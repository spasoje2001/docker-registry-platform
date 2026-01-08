from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class ForcePasswordChangeMiddlewareTest(TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()

        self.user_must_change = User.objects.create_user(
            username="mustchange", password="oldpass123", must_change_password=True
        )

        self.normal_user = User.objects.create_user(
            username="normal", password="pass123", must_change_password=False
        )

    def test_user_with_flag_is_redirected_from_home(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("password/change", response.url)

    def test_user_without_flag_is_not_redirected(self):
        self.client.login(username="normal", password="pass123")

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

    def test_password_change_page_accessible_without_redirect_loop(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.get(reverse("accounts:password_change"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change Your Password")

    def test_password_change_done_page_accessible(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.get(reverse("accounts:password_change_done"))

        self.assertEqual(response.status_code, 200)

    def test_static_files_excluded_from_redirect(self):
        self.client.login(username="mustchange", password="oldpass123")

        # Static files should pass through (even if 404)
        response = self.client.get("/static/css/style.css")

        # Should NOT redirect to password change (might be 404, but not redirect)
        self.assertNotEqual(response.status_code, 302)

    def test_admin_excluded_from_redirect(self):
        self.user_must_change.is_staff = True
        self.user_must_change.save()

        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.get("/admin/")

        # Should not redirect to password change
        # (will redirect to admin login if needed, but not to password change)
        if response.status_code == 302:
            self.assertNotIn("password/change", response.url)

    def test_password_change_clears_flag(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "oldpass123",
                "new_password1": "newpass456!@#",
                "new_password2": "newpass456!@#",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password Changed Successfully")

        self.user_must_change.refresh_from_db()

        self.assertFalse(self.user_must_change.must_change_password)

    def test_user_can_access_site_after_password_change(self):
        self.client.login(username="mustchange", password="oldpass123")

        self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "oldpass123",
                "new_password1": "newpass456!@#",
                "new_password2": "newpass456!@#",
            },
        )

        self.user_must_change.refresh_from_db()

        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_not_affected(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

    def test_password_change_with_wrong_old_password(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "wrongpass",
                "new_password1": "newpass456!@#",
                "new_password2": "newpass456!@#",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your old password was entered incorrectly")

        self.user_must_change.refresh_from_db()
        self.assertTrue(self.user_must_change.must_change_password)

    def test_password_change_with_mismatched_passwords(self):
        self.client.login(username="mustchange", password="oldpass123")

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "oldpass123",
                "new_password1": "newpass456!@#",
                "new_password2": "different456!@#",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two password fields")

        self.user_must_change.refresh_from_db()
        self.assertTrue(self.user_must_change.must_change_password)
