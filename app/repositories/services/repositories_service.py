from typing import List, Dict
from django.db.models.query import QuerySet
from django.db import models
from ..clients.registry_client import RegistryClient
from ..models import Repository, Tag


class RepositoryService():
    def __init__(self, registry_client=None):
        self.registry_client = registry_client or RegistryClient()

    def list_repositories(self, user, profile) -> QuerySet:
        repositories = []
        try:
            repositories = self.registry_client.get_all_repositories()
        except Exception as e:
            print(f"Error fetching repositories from registry: {e}")
            raise

        db_list = Repository.objects.filter(
                models.Q(visibility=Repository.VisibilityChoices.PUBLIC)
            )
        if profile:
            db_list = Repository.objects.filter(
                models.Q(is_official="False") &
                models.Q(owner=user)
            )

        return db_list.filter(name__in=repositories)

    def list_tags(self, repo_name: str) -> List[Tag]:
        tags = []
        try:
            tags = self.registry_client.get_tags_for_repository(repo_name)
        except Exception as e:
            print(f"Error fetching tags from registry: {e}")
            raise

        db_list = Tag.objects.filter(models.Q(repository=repo_name))

        return self.combine_lists(tags, db_list)

    def get_manifest(self, repo_name: str, tag_name: str) -> Dict:
        try:
            manifest = self.registry_client.get_manifest(repo_name, tag_name)
            return manifest
        except Exception as e:
            print(f"Error fetching manifest from registry: {e}")
            raise

    def delete_manifest(self, repo_name: str, tag_name: str) -> bool:
        try:
            return self.registry_client.delete_manifest(repo_name, tag_name)
        except Exception as e:
            print(f"Error deleting manifest from registry: {e}")
            raise

    def combine_lists(self, client_list: List[str], db_list: List) -> List:
        db_dict = {obj.name: obj for obj in db_list}
        combined = []

        for obj_name in client_list:
            if obj_name in db_dict:
                combined.append(db_dict[obj_name])

    def health_check(self) -> bool:
        return self.registry_client.check_health()

    def get_query_set(self) -> QuerySet:
        return Repository.objects.none()
