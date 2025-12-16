import requests
from typing import List, Dict, Optional
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger(__name__)


class RegistryClient:
    
    def __init__(self):
        self.registry_url = settings.REGISTRY_CONFIG["base_url"].rstrip('/')
        self.auth = HTTPBasicAuth(settings.REGISTRY_CONFIG["username"], settings.REGISTRY_CONFIG["password"])
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def get_all_repositories(self) -> List[Dict]:
        try:
            url = f"{self.registry_url}/v2/_catalog"
            response = self.session.get(url)
            response.raise_for_status()
            
            repositories = response.json().get('repositories', [])
            return repositories
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories: {e}")
            raise Exception(f"Failed to fetch repositories: {str(e)}")
    
    def get_single_repository(self, repository: str) -> Dict:
        """
        Dobavi podatke o jednom repozitorijumu sa svim njegovim tagovima
        
        Args:
            repository: Ime repozitorijuma (npr. 'mongo')
            
        Returns:
            Dictionary sa podacima:
            {
                'name': 'mongo',
                'tags': [
                    {
                        'name': 'latest',
                        'digest': 'sha256:abc123...',
                        'full_name': 'localhost:5000/mongo:latest'
                    },
                    ...
                ],
                'tags_count': 2
            }
        """
        try:
            # Dobavi sve tagove za repozitorijum
            url = f"{self.registry_url}/v2/{repository}/tags/list"
            response = self.session.get(url)
            response.raise_for_status()
            
            tags_list = response.json().get('tags', [])
            tags_data = []
            
            # Za svaki tag dobavi detaljne podatke
            for tag_name in tags_list:
                try:
                    tag_data = self.get_single_tag(repository, tag_name)
                    tags_data.append(tag_data)
                except Exception as e:
                    logger.warning(f"Could not fetch data for tag {repository}:{tag_name}: {e}")
                    tags_data.append({
                        'name': tag_name,
                        'digest': None,
                        'full_name': f"{self.registry_url.replace('http://', '').replace('https://', '')}/{repository}:{tag_name}",
                        'error': str(e)
                    })
            
            return {
                'name': repository,
                'tags': tags_data,
                'tags_count': len(tags_data)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repository {repository}: {e}")
            raise Exception(f"Failed to fetch repository {repository}: {str(e)}")
    
    def get_single_tag(self, repository: str, tag: str) -> Dict:
        """
        Dobavi podatke o jednom tagu
        
        Args:
            repository: Ime repozitorijuma (npr. 'mongo')
            tag: Ime taga (npr. 'latest')
            
        Returns:
            Dictionary sa podacima:
            {
                'name': 'latest',
                'digest': 'sha256:abc123...',
                'full_name': 'localhost:5000/mongo:latest',
                'repository': 'mongo'
            }
        """
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
        """
        Proveri da li je registry dostupan
        
        Returns:
            True ako je registry dostupan
        """
        try:
            url = f"{self.registry_url}/v2/"
            response = self.session.get(url)
            return response.status_code == 200
        except:
            return False

    