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
        register_data = {
            "username": self.username,
            "email": self.email,
            "password1": self.password,
            "password2": self.password,
        }

        response = self.client.post(self.register_url, register_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(User.objects.filter(username=self.username).exists())
        user = User.objects.get(username=self.username)

        login_data = {
            "username": self.username,
            "password": self.password,
        }

        response = self.client.post(self.login_url, login_data)

        self.assertEqual(response.status_code, 302)

        repo_data = {
            "name": "test-repo",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "description": "Integration test repository",
        }

        response = self.client.post(self.repo_create_url, repo_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Repository.objects.filter(
                name="test-repo",
                owner=user,
            ).exists()
        )

        repo = Repository.objects.get(name="test-repo", owner=user)

        repo_detail_url = reverse(
            "repositories:detail",
            kwargs={
                "owner_username": user.username,
                "name": repo.name,
            },
        )

        response = self.client.get(repo_detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test-repo")
        self.assertContains(response, "Integration test repository")
