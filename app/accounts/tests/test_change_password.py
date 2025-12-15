from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class ChangePasswordTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="OldPassword123!"
        )
        self.url = reverse("accounts:change_password")
        self.profile_url = reverse("accounts:profile")

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_get_change_password_page(self):
        self.client.login(username="testuser", password="OldPassword123!")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/change_password.html")
        self.assertIn("form", response.context)

    def test_wrong_old_password_fails(self):
        self.client.login(username="testuser", password="OldPassword123!")

        data = {
            "old_password": "WrongPassword",
            "new_password1": "NewStrongPass123!",
            "new_password2": "NewStrongPass123!",
        }

        response = self.client.post(self.url, data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

        messages = list(response.context["messages"])
        self.assertTrue(messages)
        self.assertIn("Current password wasn't correct.", str(messages[0]))

    def test_successful_password_change(self):
        self.client.login(username="testuser", password="OldPassword123!")

        data = {
            "old_password": "OldPassword123!",
            "new_password1": "NewStrongPass123!",
            "new_password2": "NewStrongPass123!",
        }

        response = self.client.post(self.url, data, follow=True)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))

        self.assertRedirects(response, self.profile_url)

        messages = list(response.context["messages"])
        self.assertTrue(messages)
        self.assertIn("Password successfully changed.", str(messages[0]))
