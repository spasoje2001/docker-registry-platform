from django.test import TestCase, Client
from .models import Repository
from .models import User
from django.db import IntegrityError
from django.urls import reverse


class RepositoryModelTests(TestCase):
    def setUp(self):
        """Prepare test users"""
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")

    def test_create_repository(self):
        """Test creating a repository."""
        repo = Repository.objects.create(
            name="test-repo",
            visibility=True,
            description="A test repository",
            owner=self.user1,
        )
        self.assertEqual(repo.name, "test-repo")
        self.assertTrue(repo.visibility)
        self.assertEqual(repo.description, "A test repository")
        self.assertEqual(repo.owner, self.user1)
        self.assertFalse(repo.is_official)
        self.assertIsNotNone(repo.created_at)
        self.assertIsNotNone(repo.updated_at)

    def test_repository_full_name_official(self):
        """Test full_name property for official repository."""
        repo = Repository.objects.create(
            name="official-repo", is_official=True, owner=self.user1
        )
        self.assertEqual(repo.full_name, "official-repo")

    def test_repository_full_name_non_official(self):
        """Test full_name property for non-official repository."""
        repo = Repository.objects.create(
            name="user-repo", is_official=False, owner=self.user1
        )
        self.assertEqual(repo.full_name, "user1/user-repo")

    def test_uniqueness_constraint_works(self):
        """Test: (owner, name) combination must be unique."""
        Repository.objects.create(name="duplicate-test", owner=self.user1)

        with self.assertRaises(IntegrityError):
            Repository.objects.create(name="duplicate-test", owner=self.user1)

    def test_view_own_repository(self):
        """Test: show user's repository"""
        Repository.objects.create(
            name="my-repo",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PRIVATE,
        )

        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:detail", kwargs={"owner_username": "user1", "name": "my-repo"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "my-repo")

    def test_update_repository(self):
        """Test: update repository"""
        repo = Repository.objects.create(
            name="update-test",
            owner=self.user1,
            description="Original",
            visibility=Repository.VisibilityChoices.PUBLIC,
        )

        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:update",
            kwargs={"owner_username": "user1", "name": "update-test"},
        )

        response = self.client.post(
            url,
            {
                "name": "update-test",
                "description": "Updated description",
                "visibility": Repository.VisibilityChoices.PRIVATE,
            },
        )

        self.assertEqual(response.status_code, 302)
        repo.refresh_from_db()
        self.assertEqual(repo.description, "Updated description")
        self.assertEqual(repo.visibility, Repository.VisibilityChoices.PRIVATE)

    def test_delete_repository(self):
        """Test: delete repository"""
        Repository.objects.create(name="delete-test", owner=self.user1)

        self.client.login(username="user1", password="testpass123")
        url = reverse(
            "repositories:delete",
            kwargs={"owner_username": "user1", "name": "delete-test"},
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Repository.objects.filter(name="delete-test").exists())

    def test_cannot_edit_other_users_repository(self):
        """Test: user cannot edit someone's else repository"""
        repo = Repository.objects.create(name="other-repo", owner=self.user1)

        self.client.login(username="user2", password="testpass123")
        url = reverse(
            "repositories:update",
            kwargs={"owner_username": "user1", "name": "other-repo"},
        )

        response = self.client.post(
            url,
            {
                "name": "other-repo",
                "description": "Hacked!",
                "visibility": Repository.VisibilityChoices.PUBLIC,
            },
        )

        self.assertEqual(response.status_code, 302)
        repo.refresh_from_db()
        self.assertNotEqual(repo.description, "Hacked!")

    def test_cannot_delete_other_users_repository(self):
        """Test: user cannot delete another user's repository"""
        Repository.objects.create(name="other-repo", owner=self.user1)

        self.client.login(username="user2", password="testpass123")
        url = reverse(
            "repositories:delete",
            kwargs={"owner_username": "user1", "name": "other-repo"},
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Repository.objects.filter(name="other-repo").exists())

    def test_unauthenticated_cannot_create(self):
        """Test: unauthenticated user cannot create repository"""
        url = reverse("repositories:create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_private_repo_not_visible_to_others(self):
        """Test: user cannot see others repositories"""
        Repository.objects.create(
            name="private-repo",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PRIVATE,
        )

        self.client.login(username="user2", password="testpass123")
        url = reverse(
            "repositories:detail",
            kwargs={"owner_username": "user1", "name": "private-repo"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # TAG TESTS
    def test_create_repository_tag(self):
        """Test creating a tag for a repository."""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:abcdef1234567890",
            size=2048,
        )
        self.assertEqual(tag.name, "v1.0")
        self.assertEqual(tag.digest, "sha256:abcdef1234567890")
        self.assertEqual(tag.size, 2048)
        self.assertEqual(tag.repository, repo)
        self.assertIsNotNone(tag.created_at)

    def test_tag_full_tag_name(self):
        """Test full_tag_name property"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:abcdef1234567890",
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
            digest="sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
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
            digest="sha256:abcdef1234567890",
            size=1536,
        )
        self.assertEqual(tag.size_display, "1.50 KB")

    def test_tag_uniqueness_constraint(self):
        """Test: (repository, name) combination must be unique"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        repo.tags.create(name="v1.0", digest="sha256:abc", size=1024)

        with self.assertRaises(IntegrityError):
            repo.tags.create(name="v1.0", digest="sha256:def", size=2048)
