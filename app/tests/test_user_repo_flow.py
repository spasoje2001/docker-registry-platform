from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from repositories.models import Repository

User = get_user_model()


class UserRepositoryIntegrationTest(TestCase):
    def setUp(self):
        # URLs
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("accounts:login")
        self.repo_create_url = reverse("repositories:create")

        # Test data
        self.username = "testuser"
        self.password = "StrongPass123!"
        self.email = "testuser@example.com"

    def test_user_registration_login_create_and_view_repository(self):
        # Registracija
        register_data = {
            "username": self.username,
            "email": self.email,
            "password1": self.password,
            "password2": self.password,
        }
        response = self.client.post(self.register_url, register_data)
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username=self.username)

        # Login
        login_data = {
            "username": self.username,
            "password": self.password,
        }
        response = self.client.post(self.login_url, login_data, follow=True)
        self.assertTrue(response.context["user"].is_authenticated)

        repo_data = {
            "name": "test-repo",
            "visibility": "PUBLIC",
            "description": "Integration test repository",
            "initial_tag": "latest"
        }
        response = self.client.post(self.repo_create_url, repo_data, follow=True)

        if (response.status_code == 200 and
                hasattr(response, "context") and
                "form" in response.context):
            print("Form errors:", response.context["form"].errors)

        repo = Repository.objects.get(name="test-repo", owner=user)
        self.assertEqual(repo.description, "Integration test repository")

        repo_detail_url = reverse(
            "repositories:detail",
            kwargs={"owner_username": user.username, "name": repo.name},
        )
        response = self.client.get(repo_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test-repo")
        self.assertContains(response, "Integration test repository")
