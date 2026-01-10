from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from repositories.models import Repository

User = get_user_model()


class OfficialRepositoryEndToEndFlowTestCase(TestCase):

    def test_admin_creates_official_repo_visible_in_explore_and_opens_detail(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@gmail.com",
            password="admin123"
        )

        self.client.login(username="admin", password="admin123")

        repo = Repository.objects.create(
            name="docker-official",
            description="Official Docker image",
            visibility="PUBLIC",
            is_official=True,
            owner=admin
        )

        explore_url = reverse("explore:explore")
        explore_response = self.client.get(explore_url)

        self.assertEqual(explore_response.status_code, 200)

        repositories = explore_response.context["repositories"]
        repo_names = [r.name for r in repositories]

        self.assertIn(repo.name, repo_names)

        detail_url = reverse(
            "repositories:detail_official",
            kwargs={"name": repo.name}
        )
        detail_response = self.client.get(detail_url)

        self.assertEqual(detail_response.status_code, 200)

        self.assertNotIn(admin.username, detail_url)
