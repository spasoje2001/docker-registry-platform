from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from ..models import Repository
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock, Mock
import requests

User = get_user_model()


class RepositoryModelTests(TestCase):
    def setUp(self):
        """Prepare test users"""
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")
        self.user3 = User.objects.create_user(
            username="admin1",
            password="testpass123",
            role=User.Role.ADMIN
        )

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

    @patch('repositories.views.RepositoryService')
    def test_view_own_repository(self, MockService):
        """Test: show user's repository"""
        Repository.objects.create(
            name="my-repo",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PRIVATE,
        )

        mock_service_instance = MockService.return_value
        mock_service_instance.health_check.return_value = True
        mock_service_instance.list_tags.return_value = []

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

    def test_user_cannot_create_official_repo(self):
        """Test: regular user cannot create official repository"""
        self.client.login(username="user1", password="testpass123")
        url = reverse("repositories:create")

        response = self.client.post(
            url,
            {
                "name": "official-repo",
                "description": "Trying to create official repo",
                "visibility": Repository.VisibilityChoices.PUBLIC,
                "is_official": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Repository.objects.filter(name="official-repo", is_official=True).exists()
        )

    def test_duplicate_official_repo_name(self):
        """Test that creating an official repo with duplicate name validation"""
        Repository.objects.create(
            name="django-best-practices",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.user3
        )

        with self.assertRaises(IntegrityError):
            Repository.objects.create(
                name="django-best-practices",
                owner=self.user3,
                is_official=True)
        
    @patch('repositories.views.RepositoryService')
    def test_list_repositories_mock_registry(self, MockService):
        """Unit test: list repositories (mock registry response)"""
        repo1 = Repository.objects.create(
            name="test-repo-1",
            owner=self.user1,
            description="First test repository"
        )
        repo2 = Repository.objects.create(
            name="test-repo-2",
            owner=self.user1,
            description="Second test repository"
        )
        repo3 = Repository.objects.create(
            name="other-repo",
            owner=self.user2,
            description="Another user's repository"
        )
        
        mock_service_instance = MockService.return_value
        mock_service_instance.health_check.return_value = True
        mock_service_instance.list_repositories.return_value = [repo1, repo2, repo3]
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('repositories:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        mock_service_instance.health_check.assert_called_once()
        mock_service_instance.list_repositories.assert_called_once_with(self.user1)
        
        self.assertIn('repositories', response.context)
        repositories = response.context['repositories']
        self.assertEqual(len(repositories), 3)
        
        self.assertContains(response, 'test-repo-1')
        self.assertContains(response, 'test-repo-2')
        self.assertContains(response, 'other-repo')
        
        self.assertTemplateUsed(response, 'repositories/repository_list.html')

    @patch('repositories.views.RepositoryService')
    def test_list_repositories_connection_error(self, MockService):
        """Test: handle connection error when listing repositories"""
        mock_service_instance = MockService.return_value
        mock_service_instance.health_check.return_value = False
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('repositories:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        messages_list = list(response.context['messages'])
        self.assertTrue(any('unavailable' in str(msg).lower() or 'error' in str(msg).lower() 
                           for msg in messages_list))



class OfficialRepositoryTests(TestCase):
    """Tests for official repository functionality"""

    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username="user1",
            password="testpass123",
            role=User.Role.USER
        )
        self.admin = User.objects.create_user(
            username="admin1",
            password="testpass123",
            role=User.Role.ADMIN
        )
        self.super_admin = User.objects.create_user(
            username="superadmin",
            password="testpass123",
            role=User.Role.SUPER_ADMIN
        )

    def test_admin_can_create_official_repo(self):
        """Test: admin can create official repository"""
        self.client.login(username="admin1", password="testpass123")
        url = reverse("repositories:create")

        response = self.client.post(url, {
            "name": "python",
            "description": "Official Python image",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "is_official": True,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Repository.objects.filter(name="python", is_official=True).exists()
        )

    def test_super_admin_can_create_official_repo(self):
        """Test: super admin can create official repository"""
        self.client.login(username="superadmin", password="testpass123")
        url = reverse("repositories:create")

        response = self.client.post(url, {
            "name": "nginx",
            "description": "Official NGINX image",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "is_official": True,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Repository.objects.filter(name="nginx", is_official=True).exists()
        )

    def test_official_repo_must_be_public(self):
        """Test: official repository cannot be private"""
        self.client.login(username="admin1", password="testpass123")
        url = reverse("repositories:create")

        response = self.client.post(url, {
            "name": "redis",
            "description": "Official Redis image",
            "visibility": Repository.VisibilityChoices.PRIVATE,
            "is_official": True,
        })

        self.assertEqual(response.status_code, 200)  # Form re-rendered with error
        self.assertFalse(
            Repository.objects.filter(name="redis", is_official=True).exists()
        )

    def test_official_repo_detail_url(self):
        """Test: official repo accessible via /repositories/<name>/"""
        Repository.objects.create(
            name="postgres",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.admin
        )

        url = reverse("repositories:detail_official", kwargs={"name": "postgres"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "postgres")
        self.assertContains(response, "OFFICIAL")

    def test_all_admins_can_edit_official_repo(self):
        """Test: any admin can edit official repo (not just creator)"""
        # Admin1 creates repo
        repo = Repository.objects.create(
            name="mongodb",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.admin,
            description="Original description"
        )

        # Super admin edits it
        self.client.login(username="superadmin", password="testpass123")
        url = reverse("repositories:update_official", kwargs={"name": "mongodb"})

        response = self.client.post(url, {
            "name": "mongodb",
            "description": "Updated by super admin",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "is_official": True,
        })

        self.assertEqual(response.status_code, 302)
        repo.refresh_from_db()
        self.assertEqual(repo.description, "Updated by super admin")

    def test_regular_user_cannot_edit_official_repo(self):
        """Test: regular user cannot edit official repository"""
        repo = Repository.objects.create(
            name="mysql",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.admin
        )

        self.client.login(username="user1", password="testpass123")
        url = reverse("repositories:update_official", kwargs={"name": "mysql"})

        response = self.client.post(url, {
            "name": "mysql",
            "description": "Hacked!",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "is_official": True,
        })

        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        repo.refresh_from_db()
        self.assertNotEqual(repo.description, "Hacked!")

    def test_cannot_convert_official_to_personal(self):
        """Test: cannot convert official repo back to personal"""
        repo = Repository.objects.create(
            name="ubuntu",
            is_official=True,
            visibility=Repository.VisibilityChoices.PUBLIC,
            owner=self.admin
        )

        self.client.login(username="admin1", password="testpass123")
        url = reverse("repositories:update_official", kwargs={"name": "ubuntu"})

        self.client.post(url, {
            "name": "ubuntu",
            "description": "Ubuntu image",
            "visibility": Repository.VisibilityChoices.PUBLIC,
            "is_official": False,  # Trying to uncheck
        })

        # Form should reject or checkbox should be disabled
        repo.refresh_from_db()
        self.assertTrue(repo.is_official)  # Should still be official

    def test_official_repo_full_name_no_prefix(self):
        """Test: official repo full_name has no username prefix"""
        repo = Repository.objects.create(
            name="alpine",
            is_official=True,
            owner=self.admin
        )

        self.assertEqual(repo.full_name, "alpine")
        self.assertNotIn("/", repo.full_name)

    def test_official_repos_not_on_user_profile(self):
        """Test: official repos don't appear on admin's profile"""
        Repository.objects.create(
            name="node",
            is_official=True,
            owner=self.admin,
            visibility=Repository.VisibilityChoices.PUBLIC
        )

        Repository.objects.create(
            name="personal-repo",
            is_official=False,
            owner=self.admin,
            visibility=Repository.VisibilityChoices.PUBLIC
        )

        self.client.login(username="admin1", password="testpass123")
        url = reverse("accounts:profile")
        response = self.client.get(url)

        # Should only see personal repo
        repos = response.context['repositories']
        self.assertEqual(repos.count(), 1)
        self.assertEqual(repos[0].name, "personal-repo")
