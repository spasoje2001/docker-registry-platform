from typing import List, Dict
from django.db import models
from ..clients.registry_client import RegistryClient
from ..models import Repository

class RepositoryService():
    def __init__(self, registry_client=None):
        self.registry_client = registry_client or RegistryClient()

    def list_repositories(self, user) -> List[Repository]:
        repositories = []
        try:
            repositories = self.registry_client.get_all_repositories()
        except Exception as e:
            print(f"Error fetching repositories from registry: {e}")
            raise

        db_list = []

        if user.is_authenticated:
            db_list = Repository.objects.filter(
            models.Q(visibility=Repository.VisibilityChoices.PUBLIC) |
            models.Q(owner=user)
        )
        else:
            db_list = Repository.objects.filter(
                models.Q(visibility=Repository.VisibilityChoices.PUBLIC)
            )

        result = self.combine_lists(user, repositories, db_list)
        return result
    
    def get_manifest(self, repository: str, tag_name: str) -> Dict:
        try:
            manifest = self.registry_client.get_manifest(repository, tag_name)
            return manifest
        except Exception as e:
            print(f"Error fetching manifest from registry: {e}")
            raise

    def delete_image(self, registry_url, repo_name, tag_name, digest):
        try:
            self.registry_client.delete_tag_and_image(registry_url, repo_name, tag_name, digest)
        except Exception as e:
            print(f"Error deleting image: {e}")
            raise

    def combine_lists(self, user, client_list: List[str], db_list: List[Repository]) -> List[Repository]:
        db_dict = {repo.name: repo for repo in db_list}
        combined = []
    
        for repo_name in client_list:
            if repo_name in db_dict:
                combined.append(db_dict[repo_name])

        return combined

    def health_check(self) -> bool:
        return self.registry_client.check_health()