from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from ..models import Repository, Tag
from django.contrib.auth import get_user_model

User = get_user_model()


class TagModelTests(TestCase):
    def setUp(self):
        """Prepare test users"""
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="testpass123")

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
            kwargs={"owner_username": "user1", "name": "tag-repo", "tag_name": "v1.0"},
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(repo.tags.filter(name="v1.0").exists())

    def test_list_tags_for_repository(self):
        """Test: list all tags for a repository"""
        repo = Repository.objects.create(
            name='my-repo',
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC
        )

        Tag.objects.create(
            repository=repo,
            name='v1.0.0',
            digest='sha256:' + 'a' * 64,
            size=100000000
        )
        Tag.objects.create(
            repository=repo,
            name='latest',
            digest='sha256:' + 'b' * 64,
            size=105000000
        )
        Tag.objects.create(
            repository=repo,
            name='dev',
            digest='sha256:' + 'c' * 64,
            size=110000000
        )

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

    def test_different_admin_can_edit_official_repo_tag(self):
        """Test: different admin can edit tag created by another admin"""
        tag = Tag.objects.create(
            repository=self.official_repo,
            name="3.11",
            digest="sha256:" + "b" * 64,
            size=100000000
        )

        # Admin2 edits tag created by Admin1
        self.client.login(username="admin2", password="testpass123")
        url = reverse(
            "repositories:tag_update_official",
            kwargs={"name": "python", "tag_name": "3.11"}
        )

        response = self.client.post(url, {
            "name": "3.11",
            "digest": "sha256:" + "c" * 64,
            "size": 105000000
        })

        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertEqual(tag.digest, "sha256:" + "c" * 64)

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
            kwargs={"name": "python", "tag_name": "old-version"}
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.official_repo.tags.filter(name="old-version").exists())
