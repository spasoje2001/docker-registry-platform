from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from repositories.models import Repository

User = get_user_model()


class ExploreRepositoriesTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="alice", password="password"
        )
        self.user2 = User.objects.create_user(
            username="bob", password="password"
        )
        self.user1.is_verified_publisher = True
        self.user1.save()

        # Public repo – name match
        self.repo_name_match = Repository.objects.create(
            name="nginx",
            description="Official nginx image",
            owner=self.user1,
            visibility="PUBLIC",
        )
        self.repo_name_match.is_official = True
        self.repo_name_match.save()

        # Public repo – description match
        self.repo_description_match = Repository.objects.create(
            name="webserver",
            description="nginx based web server",
            owner=self.user2,
            visibility="PUBLIC",
        )

        # Public repo – no match
        self.repo_no_match = Repository.objects.create(
            name="redis",
            description="In-memory database",
            owner=self.user1,
            visibility="PUBLIC",
        )

        # Private repo – should NEVER appear
        self.private_repo = Repository.objects.create(
            name="nginx-secret",
            description="Private nginx",
            owner=self.user1,
            visibility="PRIVATE",
        )

        self.url = reverse("explore:explore")

    def test_unauthenticated_user_can_access_explore(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_only_public_repositories_are_returned(self):
        response = self.client.get(self.url)
        repos = response.context["repositories"].object_list

        self.assertIn(self.repo_name_match, repos)
        self.assertIn(self.repo_description_match, repos)
        self.assertIn(self.repo_no_match, repos)

        self.assertNotIn(self.private_repo, repos)

    def test_search_filters_repositories_correctly(self):
        response = self.client.get(self.url, {"q": "nginx"})
        repos = list(response.context["repositories"].object_list)

        self.assertIn(self.repo_name_match, repos)
        self.assertIn(self.repo_description_match, repos)

        self.assertNotIn(self.repo_no_match, repos)
        self.assertNotIn(self.private_repo, repos)

    def test_relevance_sorting_name_before_description(self):
        response = self.client.get(self.url, {"q": "nginx"})
        repos = list(response.context["repositories"].object_list)

        self.assertGreater(len(repos), 1)

        # Name match MUST be first
        self.assertEqual(repos[0], self.repo_name_match)
        self.assertEqual(repos[1], self.repo_description_match)

    def test_empty_search_returns_all_public(self):
        response = self.client.get(self.url)
        page = response.context["repositories"]

        self.assertEqual(page.paginator.count, 3)

    def test_official_filter_works(self):
        response = self.client.get(self.url, {"filter": "official"})
        repos = list(response.context["repositories"].object_list)

        self.assertIn(self.repo_name_match, repos)
        self.assertNotIn(self.repo_description_match, repos)
        self.assertNotIn(self.repo_no_match, repos)
        self.assertNotIn(self.private_repo, repos)

    def test_verified_publisher_filter_works(self):
        response = self.client.get(self.url, {"filter": "verified"})
        repos = list(response.context["repositories"].object_list)

        self.assertIn(self.repo_name_match, repos)   # owner = verified
        self.assertIn(self.repo_no_match, repos)     # owner = verified

        self.assertNotIn(self.repo_description_match, repos)  # bob NOT verified
        self.assertNotIn(self.private_repo, repos)

    def test_sort_by_name_ascending(self):
        response = self.client.get(self.url, {"sort": "name_asc"})
        repos = list(response.context["repositories"].object_list)

        names = [r.name for r in repos]
        self.assertEqual(names, sorted(names))

    def test_sort_by_name_descending(self):
        response = self.client.get(self.url, {"sort": "name_desc"})
        repos = list(response.context["repositories"].object_list)

        names = [r.name for r in repos]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_sort_by_recently_updated(self):
        response = self.client.get(self.url, {"sort": "updated"})
        repos = list(response.context["repositories"].object_list)

        dates = [r.updated_at for r in repos]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_filters_combine_correctly(self):
        response = self.client.get(
            self.url,
            {
                "q": "nginx",
                "filter": "verified",
            }
        )

        repos = list(response.context["repositories"].object_list)

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0], self.repo_name_match)

    def test_explicit_sort_overrides_relevance(self):
        response = self.client.get(
            self.url,
            {
                "q": "nginx",
                "sort": "name_desc",
            }
        )

        repos = list(response.context["repositories"].object_list)
        names = [r.name for r in repos]

        self.assertEqual(names, sorted(names, reverse=True))
