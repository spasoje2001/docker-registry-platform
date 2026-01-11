from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from repositories.models import Repository
from unittest.mock import patch

User = get_user_model()


class ExploreSearchFlowTestCase(TestCase):
    def setUp(self):
        self.explore_url = reverse("explore:explore")

        self.user = User.objects.create_user(
            username="user1",
            email="useremail@gmail.com",
            password="user123"
        )

        Repository.objects.create(
            name="docker-registry",
            visibility=Repository.VisibilityChoices.PUBLIC,
            description="docker-registry platform",
            owner=self.user
        )

        Repository.objects.create(
            name="kubernetes",
            visibility=Repository.VisibilityChoices.PUBLIC,
            description="kubernetes platform",
            owner=self.user
        )

        Repository.objects.create(
            name="docker-private",
            visibility=Repository.VisibilityChoices.PRIVATE,
            description="Docker private repo",
            owner=self.user
        )

        self.patcher = patch('repositories.services.repositories_service.RegistryClient.get_all_repositories')
        self.mock_registry = self.patcher.start()
        self.mock_registry.return_value = ["docker-registry", "kubernetes", "docker-private"]

    def tearDown(self):
        self.patcher.stop()

    def test_user_search_finds_correct_repositories(self):
        response = self.client.get(
            self.explore_url,
            {"q": "docker"}
        )

        self.assertEqual(response.status_code, 200)

        repositories = response.context["repositories"]
        repo_names = [repo.name for repo in repositories]

        self.assertIn("docker-registry", repo_names)
        self.assertNotIn("kubernetes", repo_names)
        self.assertNotIn("docker-private", repo_names)

        self.assertEqual(len(repo_names), 1)
