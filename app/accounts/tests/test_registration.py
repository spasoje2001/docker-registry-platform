from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegistrationTest(TestCase):

    def setUp(self):
        self.url = reverse("accounts:register")
        self.home_url = reverse("core:home")

    def test_get_register_page_renders_template(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_authenticated_user_is_redirected_from_register(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="Testpass123!",
        )
        self.client.login(username="existing", password="Testpass123!")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)

    def test_successful_registration_creates_user_and_redirects(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.must_change_password)

        self.assertRedirects(response, self.home_url)

    def test_registration_shows_success_message(self):
        data = {
            "username": "msguser",
            "email": "msguser@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }

        response = self.client.post(self.url, data, follow=True)
        messages = list(response.context.get("messages"))
        self.assertTrue(messages)
        self.assertIn(
            "Your account has been created! You are now able to log in",
            str(messages[0])
        )

    def test_email_must_be_unique(self):
        User.objects.create_user(
            username="existing",
            email="dup@example.com",
            password="Testpass123!",
        )
        data = {
            "username": "other",
            "email": "dup@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = self.client.post(self.url, data)

        self.assertEqual(User.objects.count(), 1)

        form = response.context["form"]

        self.assertTrue(form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("Email already registered", form.errors["email"])

    def test_weak_password_fails_verification(self):
        data = {
            "username": "weakuser",
            "email": "weak@example.com",
            "password1": "123",
            "password2": "123",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(User.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("password2", response.context["form"].errors)
