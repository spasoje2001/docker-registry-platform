from typing import List, Dict
from django.db import models
from ..clients.registry_client import RegistryClient
from ..models import Repository

class RepositoryService():
    def __init__(self, registry_client=None):
        self.registry_client = registry_client or RegistryClient()

    def list_repositories(self, user) -> List[Repository]:
        repositories = self.registry_client.get_all_repositories()
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

    

    def combine_lists(self, user, client_list: List[str], db_list: List[Repository]) -> List[Repository]:
        db_dict = {repo.name: repo for repo in db_list}
        combined = []
    
        for repo_name in client_list:
            if repo_name in db_dict:
                combined.append(db_dict[repo_name])

        return combined