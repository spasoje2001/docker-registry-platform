from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from repositories.models import Repository

User = get_user_model()

class ProfileRepoTabTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="password123"
        )
        self.client.login(username="testuser", password="password123")

    def test_create_new_repository_success(self):
        url = reverse("repositories:create")
        data = {
            "name": "my-repo",
            "description": "Test repository",
            "visibility": "PUBLIC",
            "from_profile": "1"
        }

        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("accounts:profile"))

        self.assertTrue(Repository.objects.filter(name="my-repo", owner=self.user).exists())

    def test_create_new_repository_name_exists(self):
        Repository.objects.create(name="existing-repo", owner=self.user)

        url = reverse("repositories:create")
        data = {
            "name": "existing-repo",
            "description": "Another repo",
            "visibility": "PUBLIC",
            "from_profile": "1",
        }

        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'data-bs-target="#new_repo"')
        self.assertContains(response, "Repository with this name already exists!")