from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from repositories.models import Repository, Tag
from repositories.services.sync_service import SyncService
from repositories.clients.registry_client import RegistryClient
import os
from unittest import skipIf

User = get_user_model()


@skipIf(os.getenv("CI") == "true", "Skipping registry integration tests in CI")
class TestRegistryIntegration(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.repository = Repository.objects.create(
            name="myrepo",
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.user
        )

    @patch.object(RegistryClient, "get_tags_for_repository")
    @patch.object(RegistryClient, "get_manifest")
    def test_sync_create_tag_and_total_size(self, mock_get_manifest, mock_get_tags):
        mock_get_tags.return_value = ["v1.0.0"]
        mock_get_manifest.return_value = {
            "digest": "sha256:123456abcdef",
            "size": 2048,
            "os": "linux",
            "arch": "amd64",
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json"
        }

        sync_service = SyncService()
        stats = sync_service.sync_all_tags()

        tag = Tag.objects.get(repository=self.repository, name="v1.0.0")
        self.assertEqual(tag.digest, "sha256:123456abcdef")
        self.assertEqual(tag.size, 2048)
        self.assertEqual(stats.tags_created, 1)

        self.repository.refresh_from_db()
        self.assertEqual(self.repository.total_size, 2048)
        self.assertEqual(self.repository.total_size_display, "2.00 KB")

    @patch.object(RegistryClient, "get_tags_for_repository")
    @patch.object(RegistryClient, "get_manifest")
    def test_sync_delete_tag(self, mock_get_manifest, mock_get_tags):
        Tag.objects.create(
            repository=self.repository,
            name="v1.0.0",
            digest="sha256:123456abcdef",
            size=1024,
            os="linux",
            arch="amd64",
            image_type="Image",
            last_synced=timezone.now()
        )

        mock_get_tags.return_value = []
        mock_get_manifest.return_value = {}

        sync_service = SyncService()
        stats = sync_service.sync_all_tags()

        self.assertEqual(
            Tag.objects.filter(
                repository=self.repository,
                name="v1.0.0").count(),
            0)
        self.assertEqual(stats.tags_deleted, 1)

        self.repository.refresh_from_db()
        self.assertEqual(self.repository.total_size, 0)
        self.assertEqual(self.repository.total_size_display, "0.00 B")

    @patch.object(RegistryClient, "get_tags_for_repository")
    def test_registry_unavailable(self, mock_get_tags):
        mock_get_tags.side_effect = Exception("Registry unavailable")

        sync_service = SyncService()
        stats = sync_service.sync_all_tags()

        self.assertEqual(stats.tags_created, 0)
        self.assertEqual(stats.tags_updated, 0)
        self.assertEqual(stats.repos_skipped, 1)
        self.assertIn("Registry unavailable", stats.errors[0])

    @patch("repositories.clients.registry_client.requests.Session.get")
    def test_authentication_flow(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repositories": []}
        mock_get.return_value = mock_response

        client = RegistryClient()
        self.assertEqual(client.auth.username, "admin")
        self.assertEqual(client.auth.password, "Admin123")
        self.assertTrue(client.check_health())
