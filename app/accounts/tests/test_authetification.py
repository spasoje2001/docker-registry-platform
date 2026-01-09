from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthentificationTest(TestCase):
    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.home_url = reverse("core:home")

    def test_login_valid_credentials(self):
        User.objects.create_user(
            username="test",
            email="example@example.com",
            password="test1234",
        )
        response = self.client.post(
            self.login_url,
            {"username": "test", "password": "test1234"},
            follow=True,
        )
        user_in_context = response.context["user"]
        self.assertTrue(user_in_context.is_authenticated)
        self.assertEqual(response.request["PATH_INFO"], self.home_url)

    def test_login_wrong_credentials(self):
        User.objects.create_user(
            username="test",
            email="example@example.com",
            password="test1234",
        )

        response = self.client.post(
            self.login_url,
            {"username": "test", "password": "1234test"},
            follow=True,
        )
        self.assertFalse(response.context["user"].is_authenticated)

        form = response.context["form"]
        self.assertTrue(form.errors)
        self.assertTrue(form.non_field_errors())

        self.assertEqual(response.status_code, 200)

    def test_logout_clears_session(self):
        User.objects.create_user(
            username="test",
            email="example@example.com",
            password="test1234",
        )
        self.client.post(
            self.login_url,
            {"username": "test", "password": "test1234"},
        )

        response_after_login = self.client.get(self.home_url)
        self.assertTrue(response_after_login.context["user"].is_authenticated)

        response = self.client.post(
            self.logout_url,
            follow=True,
        )

        self.assertFalse(response.context["user"].is_authenticated)

        self.assertEqual(response.request["PATH_INFO"], self.home_url)
