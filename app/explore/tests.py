from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from repositories.models import Repository
from unittest.mock import patch

User = get_user_model()


class ExploreRepositoriesTests(TestCase):

    def setUp(self):
        self.registry_patcher = patch('repositories.services.repositories_service.RegistryClient.get_all_repositories')
        self.mock_registry = self.registry_patcher.start()
        self.mock_registry.return_value = ['nginx', 'webserver', 'redis']

        self.user1 = User.objects.create_user(username="alice", password="password123")
        self.user1.is_verified_publisher = True
        self.user1.save()

        self.repo_nginx = Repository.objects.create(
            name="nginx", owner=self.user1, visibility="PUBLIC", is_official=True
        )
        self.repo_web = Repository.objects.create(
            name="webserver", owner=self.user1, visibility="PUBLIC", is_official=False
        )
        self.repo_redis = Repository.objects.create(
            name="redis", owner=self.user1, visibility="PUBLIC", is_official=False
        )
        
        Repository.objects.create(
            name="secret", owner=self.user1, visibility="PRIVATE"
        )

        self.url = reverse("explore:explore")

    def tearDown(self):
        self.registry_patcher.stop()

    def test_unauthenticated_user_sees_public_repos(self):
        response = self.client.get(self.url)
        repos = response.context["repositories"].object_list
        self.assertEqual(len(repos), 3)

    def test_search_by_query(self):
        response = self.client.get(self.url, {"q": "nginx"})
        repos = list(response.context["repositories"].object_list)
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0].name, "nginx")

    def test_official_filter(self):
        response = self.client.get(self.url, {"filter": "official"})
        repos = list(response.context["repositories"].object_list)
        self.assertTrue(all(r.is_official for r in repos))
        self.assertEqual(len(repos), 1)
