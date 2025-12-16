from app.repositories.mappers.repository_mapper import repository_mapper
from app.clients.registry_client import RegistryClient
from app.repositories.models import Repository

class RepositoryService():
    """
    Servis za upravljanje repozitorijumima u Docker Registry-ju.
    """

    def __init__(self, registry_client: "RegistryClient"):
        self.registry_client = registry_client

    def list_repositories(self) -> list[Repository]:
        """
        Dohvati listu svih repozitorijuma iz Docker Registry-ja.

        Returns:
            Lista repozitorijuma kao lista objekata Repository.
        """
        response = self.registry_client.get("/v2/_catalog")
        repositories = response.get("repositories", [])
        return toRepositoryList(repositories)