from typing import List, Dict, Optional
from requests.auth import HTTPBasicAuth
import logging
import requests
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class RegistryClient:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not RegistryClient._initialized:
            self.auth = HTTPBasicAuth(
                os.environ.get("REGISTRY_USERNAME", "admin"),
                os.environ.get("REGISTRY_PASSWORD", "Admin123")
            )
            self.registry_url = os.environ.get("REGISTRY_URL", "http://localhost:5000").rstrip('/')
            self.session = requests.Session()
            self.session.auth = self.auth
            RegistryClient._initialized = True
        
    def get_all_repositories(self) -> List[str]:
        try:
            url = f"{self.registry_url}/v2/_catalog"
            response = self.session.get(url)
            response.raise_for_status()
            repositories = response.json().get('repositories', [])
            return repositories
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories: {e}")
            raise Exception(f"Failed to fetch repositories: {str(e)}")
    
    def get_single_repository_tags(self, repository: str) -> List[str]:
        try:
            url = f"{self.registry_url}/v2/{repository}/tags/list"
            response = self.session.get(url)
            response.raise_for_status()
            tags_list = response.json().get('tags', [])
            return tags_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repository {repository}: {e}")
            raise Exception(f"Failed to fetch repository {repository}: {str(e)}")
    
    def get_single_tag(self, repository: str, tag: str) -> Dict:
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{tag}"
            headers = {
                'Accept': 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            digest = response.headers.get('Docker-Content-Digest')
            registry_host = self.registry_url.replace('http://', '').replace('https://', '')
            
            return {
                'name': tag,
                'digest': digest,
                'full_name': f"{registry_host}/{repository}:{tag}",
                'repository': repository
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching tag {repository}:{tag}: {e}")
            raise Exception(f"Failed to fetch tag {repository}:{tag}: {str(e)}")
    
    def check_health(self) -> bool:
        try:
            url = f"{self.registry_url}/v2/"
            response = self.session.get(url)
            return response.status_code == 200
        except:
            logger.warning(f"Registry health check failed for {self.registry_url}")
            return False

    