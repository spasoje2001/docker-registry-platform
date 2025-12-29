from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from ..models import Repository, Tag
from ..services import SyncService, SyncStats
from django.contrib.auth import get_user_model
from django.core.management import call_command as django_call_command
from unittest.mock import patch, MagicMock, Mock
from io import StringIO

User = get_user_model()


class TagModelTests(TestCase):
    def setUp(self):
        """Prepare test users"""
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.repo = Repository.objects.create(name="test-repo",owner=self.user1)

    def test_tag_full_tag_name(self):
        """Test full_tag_name property"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:" + "a" * 64,
            size=2048,
        )
        self.assertEqual(tag.full_tag_name, "user1/tag-repo:v1.0")

    def test_tag_short_digest(self):
        """Test short_digest property"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:abcdef1234567890abcdef12345"
                   "67890abcdef1234567890abcdef1234567890",
            size=2048,
        )
        self.assertEqual(tag.short_digest, "sha256:abcdef123456...")

    def test_tag_size_display(self):
        """Test size_display property"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:" + "c" * 64,
            size=1536,
        )
        self.assertEqual(tag.size_display, "1.50 KB")

    def test_tag_uniqueness_constraint(self):
        """Test: (repository, name) combination must be unique"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        repo.tags.create(name="v1.0", digest="sha256:" + "d" * 64, size=1024)

        with self.assertRaises(IntegrityError):
            repo.tags.create(name="v1.0", digest="sha256:" + "d" * 64, size=2048)

    def test_create_tag(self):
        """Test: create tag view"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )

        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:tag_create",
            kwargs={"owner_username": "user1", "name": "tag-repo"},
        )

        response = self.client.post(
            url,
            {
                "name": "v1.0",
                "digest": "sha256:" + "a" * 64,
                "size": 2048,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(repo.tags.filter(name="v1.0").exists())

    def test_delete_tag(self):
        """Test: delete tag view"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        repo.tags.create(
            name="v1.0",
            digest="sha256:" + "e" * 64,
            size=2048,
        )

        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:tag_delete",
            kwargs={
                "owner_username": "user1",
                "name": "tag-repo",
                "tag_name": "v1.0",
                "digest": "sha256:" + "a" * 64},
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(repo.tags.filter(name="v1.0").exists())

    @patch('repositories.views.RepositoryService')
    def test_list_tags_for_repository(self, MockService):
        """Test: list all tags for a repository"""
        repo = Repository.objects.create(
            name='my-repo',
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC
        )

        tag1 = Tag.objects.create(
            repository=repo,
            name='v1.0.0',
            digest='sha256:' + 'a' * 64,
            size=100000000
        )
        tag2 = Tag.objects.create(
            repository=repo,
            name='latest',
            digest='sha256:' + 'b' * 64,
            size=105000000
        )
        tag3 = Tag.objects.create(
            repository=repo,
            name='dev',
            digest='sha256:' + 'c' * 64,
            size=110000000
        )

        mock_service_instance = MockService.return_value
        mock_service_instance.health_check.return_value = True
        mock_service_instance.list_tags.return_value = [tag1, tag2, tag3]
        
        url = reverse(
            'repositories:detail',
            kwargs={'owner_username': 'user1', 'name': 'my-repo'}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('tags', response.context)
        tags = response.context['tags']
        self.assertEqual(tags.count(), 3)

        self.assertContains(response, 'v1.0.0')
        self.assertContains(response, 'latest')
        self.assertContains(response, 'dev')

    @patch('repositories.views.RepositoryService')
    def test_list_tags_mock_registry(self, MockService):
        """Unit test: list tags (mock registry response)"""
        tag1 = Tag.objects.create(
            name="v1.0",
            repository=self.repo,
            digest="sha256:abc123",
            size=1024
        )
        tag2 = Tag.objects.create(
            name="v2.0",
            repository=self.repo,
            digest="sha256:def456",
            size=2048
        )
        tag3 = Tag.objects.create(
            name="latest",
            repository=self.repo,
            digest="sha256:ghi789",
            size=3072
        )
        
        mock_service_instance = MockService.return_value
        mock_service_instance.health_check.return_value = True
        mock_service_instance.list_tags.return_value = [tag1, tag2, tag3]
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('repositories:detail', kwargs={
            'owner_username': 'user1',
            'name': 'test-repo'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        #mock_service_instance.list_tags.assert_called_once_with(self.repo.name)
        
        self.assertIn('tags', response.context)
        tags = response.context['tags']
        self.assertEqual(len(tags), 3)
        
        self.assertContains(response, 'v1.0')
        self.assertContains(response, 'v2.0')
        self.assertContains(response, 'latest')


class OfficialRepoTagTests(TestCase):
    """Tests for tag operations on official repositories"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin1",
            password="testpass123",
            role=User.Role.ADMIN
        )
        self.admin2 = User.objects.create_user(
            username="admin2",
            password="testpass123",
            role=User.Role.ADMIN
        )
        self.regular_user = User.objects.create_user(
            username="user1",
            password="testpass123",
            role=User.Role.USER
        )

        self.official_repo = Repository.objects.create(
            name="python",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.admin
        )

    def test_admin_can_create_tag_for_official_repo(self):
        """Test: admin can create tag for official repository"""
        self.client.login(username="admin1", password="testpass123")
        url = reverse(
            "repositories:tag_create_official",
            kwargs={"name": "python"}
        )

        response = self.client.post(url, {
            "name": "3.12",
            "digest": "sha256:" + "a" * 64,
            "size": 100000000
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.official_repo.tags.filter(name="3.12").exists())

    def test_regular_user_cannot_create_tag_for_official_repo(self):
        """Test: regular user cannot create tag for official repository"""
        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:tag_create_official",
            kwargs={"name": "python"}
        )

        response = self.client.post(url, {
            "name": "3.10",
            "digest": "sha256:" + "d" * 64,
            "size": 100000000
        })

        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.official_repo.tags.filter(name="3.10").exists())

    def test_delete_official_repo_tag(self):
        """Test: admin can delete tag from official repository"""
        Tag.objects.create(
            repository=self.official_repo,
            name="old-version",
            digest="sha256:" + "e" * 64,
            size=100000000
        )

        self.client.login(username="admin2", password="testpass123")
        url = reverse(
            "repositories:tag_delete_official",
            kwargs={"name": "python", "tag_name": "old-version", "digest": "sha256:" + "e" * 64}
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.official_repo.tags.filter(name="old-version").exists())

class SyncTagsCommandTest(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user1 = User.objects.create_user(
            username="user1",
            password="testpass123"
        )
        self.repository = Repository.objects.create(
            name='test-repo',
            description='Test repository',
            owner=self.user1
        )

        self.mock_client = Mock()
        self.service = SyncService(registry_client=self.mock_client)

    def _setup_mock_for_tags(self, tags_dict):
        """
        Helper to setup mock for multiple tags.
        
        Args:
            tags_dict: Dict of tag_name -> digest
            Example: {'v1.0.0': 'sha256:abc', 'v2.0.0': 'sha256:def'}
        """
        self.mock_client.get_tags_for_repository.return_value = list(tags_dict.keys())
        
        def get_manifest(repo_name, tag_name):
            digest = tags_dict.get(tag_name, 'sha256:unknown')
            return {
                'config': {'digest': digest, 'size': 1000},
                'layers': [],
                'mediaType': 'application/vnd.docker.distribution.manifest.v2+json'
            }
        
        self.mock_client.get_manifest.side_effect = get_manifest
        
        self.mock_client.get_config_blob.return_value = {
            'os': 'linux',
            'architecture': 'amd64'
        }

    def call_command(self, *args, **kwargs):
        """Helper to call command and capture output"""
        out = StringIO()
        err = StringIO()
        django_call_command('sync_tags', *args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    @patch('repositories.management.commands.sync_tags.SyncService')
    def test_sync_all_repositories(self, mock_service_class):
        """Test syncing all repositories."""

        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        stats = SyncStats(
            repos_processed=1,
            tags_created=3,
            tags_updated=1,
            tags_deleted=0
        )
        mock_service.sync_all_tags.return_value = stats
        
        out, err = self.call_command()
        
        mock_service.sync_all_tags.assert_called_once()
        self.assertIn('Synchronizing repositories...', out)
        self.assertIn('Synchronization complete!', out)
        self.assertIn('Tags created:           3', out)
        self.assertIn('Tags updated:           1', out)

    def test_orphan_tags_are_deleted(self):
        """Test that orphan tags (not in registry) are deleted from database."""
        Tag.objects.create(repository=self.repository, name='v1.0.0', digest='sha256:abc123')
        Tag.objects.create(repository=self.repository, name='v2.0.0', digest='sha256:def456')
        Tag.objects.create(repository=self.repository, name='orphan-tag', digest='sha256:orphan')
        
        self._setup_mock_for_tags({
            'v1.0.0': 'sha256:abc123',
            'v2.0.0': 'sha256:def456',
        })
        
        created, updated, deleted = self.service.sync_repository_tags(self.repository)
        
        self.assertEqual(deleted, 1)
        self.assertEqual(Tag.objects.filter(repository=self.repository).count(), 2)