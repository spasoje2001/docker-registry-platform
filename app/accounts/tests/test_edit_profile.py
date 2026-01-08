from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class EditProfileTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="StrongPass123!"
        )

        self.other_user = User.objects.create_user(
            username="hacker", email="hacker@example.com", password="StrongPass123!"
        )

        self.url = reverse("accounts:edit_profile")
        self.profile_url = reverse("accounts:profile")

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_get_edit_profile_page(self):
        self.client.login(username="testuser", password="StrongPass123!")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")
        self.assertIn("form", response.context)

    def test_successful_profile_update(self):
        self.client.login(username="testuser", password="StrongPass123!")

        data = {
            "first_name": "Pera",
            "last_name": "Peric",
        }

        response = self.client.post(self.url, data, follow=True)

        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, "Pera")
        self.assertEqual(self.user.last_name, "Peric")
        self.assertRedirects(response, self.profile_url)

        messages = list(response.context["messages"])
        self.assertTrue(messages)
        self.assertIn("Profile updated successfully.", str(messages[0]))

    def test_invalid_profile_update_shows_errors(self):
        self.client.login(username="testuser", password="StrongPass123!")

        data = {
            "first_name": "",
            "last_name": "",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("first_name", response.context["form"].errors)

    def test_user_cannot_edit_other_users_data(self):
        self.client.login(username="testuser", password="StrongPass123!")

        data = {
            "first_name": "Hacked",
            "last_name": "User",
        }

        self.client.post(self.url, data)

        self.user.refresh_from_db()
        self.other_user.refresh_from_db()

        # first user is changed
        self.assertEqual(self.user.first_name, "Hacked")
        self.assertEqual(self.user.last_name, "User")

        # other user is not changed
        self.assertEqual(self.other_user.first_name, "")
        self.assertEqual(self.other_user.last_name, "")
