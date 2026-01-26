from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from repositories.models import Repository


User = get_user_model()


class ExploreRepositoriesTests(TestCase):

    def setUp(self):
        self.registry_patcher = patch(
            "repositories.services.repositories_service.RegistryClient.get_all_repositories"
        )
        self.mock_registry = self.registry_patcher.start()
        self.mock_registry.return_value = [
            "nginx",
            "webserver",
            "redis",
            "searchterm-repo",
            "other-app",
            "unverified-repo",
        ]

        self.user1 = User.objects.create_user(username="alice", password="password123")
        self.user1.is_verified_publisher = True
        self.user1.save()

        self.repo_nginx = Repository.objects.create(
            name="nginx",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC,
            is_official=True,
        )
        self.repo_web = Repository.objects.create(
            name="webserver",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC,
            is_official=False,
        )
        self.repo_redis = Repository.objects.create(
            name="redis",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC,
            is_official=False,
        )

        Repository.objects.create(
            name="secret",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PRIVATE,
        )

        self.url = reverse("explore:explore")

    def tearDown(self):
        self.registry_patcher.stop()

    def test_unauthenticated_user_sees_public_repos(self):
        response = self.client.get(self.url)
        repos = response.context.get("repositories") or response.context.get("page_obj")
        self.assertEqual(len(repos.object_list), 3)

    def test_search_by_query(self):
        response = self.client.get(self.url, {"q": "nginx"})
        repos = response.context.get("repositories") or response.context.get("page_obj")
        self.assertEqual(len(repos.object_list), 1)
        self.assertEqual(repos.object_list[0].name, "nginx")

    def test_official_filter(self):
        response = self.client.get(self.url, {"filter": "official"})
        repos = response.context.get("repositories") or response.context.get("page_obj")
        self.assertTrue(all(r.is_official for r in repos.object_list))
        self.assertEqual(len(repos.object_list), 1)

    def test_unauthenticated_user_can_access_explore(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_only_public_repositories_are_returned(self):
        response = self.client.get(self.url)
        repos = response.context["page_obj"]
        self.assertEqual(len(repos.object_list), 3)
        self.assertTrue(
            all(
                r.visibility == Repository.VisibilityChoices.PUBLIC
                for r in repos.object_list
            )
        )

    def test_search_filters_repositories_correctly(self):
        response = self.client.get(self.url, {"q": "redis"})
        repos = response.context["page_obj"]
        self.assertEqual(len(repos.object_list), 1)
        self.assertEqual(repos.object_list[0].name, "redis")

    def test_relevance_sorting_name_before_description(self):
        Repository.objects.create(
            name="other-app",
            description="searchterm",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC,
        )
        Repository.objects.create(
            name="searchterm-repo",
            description="blah",
            owner=self.user1,
            visibility=Repository.VisibilityChoices.PUBLIC,
        )

        response = self.client.get(self.url, {"q": "searchterm"})
        repos = list(response.context["page_obj"].object_list)

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0].name, "searchterm-repo")

    def test_empty_search_returns_all_public(self):
        response = self.client.get(self.url, {"q": ""})
        repos = response.context["page_obj"]
        self.assertEqual(len(repos.object_list), 3)

    def test_official_filter_works(self):
        response = self.client.get(self.url, {"filter": "official"})
        repos = response.context["page_obj"]
        self.assertTrue(all(r.is_official for r in repos.object_list))
        self.assertEqual(len(repos.object_list), 1)

    def test_verified_publisher_filter_works(self):
        bad_user = User.objects.create_user(username="bad", password="123")
        bad_user.is_verified_publisher = False
        bad_user.save()
        Repository.objects.create(
            name="unverified-repo",
            owner=bad_user,
            visibility=Repository.VisibilityChoices.PUBLIC,
        )
        response = self.client.get(self.url, {"filter": "verified"})
        repos = response.context["page_obj"]
        self.assertTrue(all(r.owner.is_verified_publisher for r in repos.object_list))
        self.assertNotIn("unverified-repo", [r.name for r in repos.object_list])

    def test_sort_by_name_ascending(self):
        response = self.client.get(self.url, {"sort": "name_asc"})
        repos = [r.name for r in response.context["page_obj"].object_list]
        self.assertEqual(repos, sorted(repos))

    def test_sort_by_name_descending(self):
        response = self.client.get(self.url, {"sort": "name_desc"})
        repos = [r.name for r in response.context["page_obj"].object_list]
        self.assertEqual(repos, sorted(repos, reverse=True))

    def test_sort_by_recently_updated(self):
        self.repo_web.save()
        response = self.client.get(self.url, {"sort": "updated"})
        repos = list(response.context["page_obj"].object_list)
        self.assertTrue(len(repos) > 0)
        self.assertEqual(repos[0].name, "webserver")

    def test_filters_combine_correctly(self):
        response = self.client.get(self.url, {"q": "nginx", "filter": "official"})
        repos = response.context["page_obj"]
        self.assertEqual(len(repos.object_list), 1)
        self.assertEqual(repos.object_list[0].name, "nginx")

    def test_explicit_sort_overrides_relevance(self):
        response = self.client.get(self.url, {"q": "", "sort": "name_desc"})
        repos = [r.name for r in response.context["page_obj"].object_list]

        self.assertEqual(repos[0], "webserver")
        self.assertEqual(repos[1], "redis")
        self.assertEqual(repos[2], "nginx")
