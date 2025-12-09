from django.test import TestCase
from .models import Repository
from .models import User
from django.db import IntegrityError


class RepositoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_create_repository(self):
        """Test creating a repository."""
        repo = Repository.objects.create(
            name="test-repo",
            visibility=True,
            description="A test repository",
            owner=self.user,
        )
        self.assertEqual(repo.name, "test-repo")
        self.assertTrue(repo.visibility)
        self.assertEqual(repo.description, "A test repository")
        self.assertEqual(repo.owner, self.user)
        self.assertFalse(repo.is_official)
        self.assertIsNotNone(repo.created_at)
        self.assertIsNotNone(repo.updated_at)

    def test_repository_full_name_official(self):
        """Test full_name property for official repository."""
        repo = Repository.objects.create(
            name="official-repo", is_official=True, owner=self.user
        )
        self.assertEqual(repo.full_name, "official-repo")

    def test_repository_full_name_non_official(self):
        """Test full_name property for non-official repository."""
        repo = Repository.objects.create(
            name="user-repo", is_official=False, owner=self.user
        )
        self.assertEqual(repo.full_name, "testuser/user-repo")

    def test_uniqueness_constraint_works(self):
        """Test: (owner, name) combination must be unique."""
        Repository.objects.create(name="duplicate-test", owner=self.user)

        with self.assertRaises(IntegrityError):
            Repository.objects.create(name="duplicate-test", owner=self.user)
