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
                "digest": "sha256:abcdef1234567890",
                "size": 2048,
            },
        )

        self.assertEqual(response.status_code, 200)


    def test_delete_tag(self):
        """Test: delete tag view"""
        repo = Repository.objects.create(
            name="tag-repo",
            owner=self.user1,
        )
        tag = repo.tags.create(
            name="v1.0",
            digest="sha256:abcdef1234567890",
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
