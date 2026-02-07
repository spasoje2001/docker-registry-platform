from typing import List, Dict
from requests.auth import HTTPBasicAuth
import logging
import requests
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
                os.environ.get("REGISTRY_PASSWORD", "Admin123"),
            )
            self.registry_url = os.environ.get(
                "REGISTRY_URL", "http://localhost:5000"
            ).rstrip("/")
            self.session = requests.Session()
            self.session.auth = self.auth
            RegistryClient._initialized = True
            logger.info("Registry client initialized: %s", self.registry_url)

    def get_all_repositories(self) -> List[str]:
        try:
            url = f"{self.registry_url}/v2/_catalog"
            response = self.session.get(url)
            response.raise_for_status()
            repos = response.json().get("repositories", [])
            logger.debug("Fetched %d repositories from registry", len(repos))
            return repos
        except requests.exceptions.RequestException as e:
            logger.error("Registry connection failed: unable to fetch repositories - %s", str(e))
            raise Exception(f"Failed to fetch repositories: {str(e)}")

    def get_tags_for_repository(self, repository: str) -> List[str]:
        try:
            url = f"{self.registry_url}/v2/{repository}/tags/list"
            response = self.session.get(url)
            response.raise_for_status()
            tags_list = response.json().get("tags", [])
            logger.debug("Fetched %d tags for repository %s", len(tags_list) if tags_list else 0, repository)
            return tags_list

        except requests.exceptions.RequestException as e:
            logger.error("Registry connection failed: unable to fetch tags for %s - %s", repository, str(e))
            raise Exception(f"Failed to fetch repository {repository}: {str(e)}")

    def get_manifest(self, repository: str, tag_name: str) -> Dict:
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{tag_name}"
            headers = {
                "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.oci.image.manifest.v1+json, "
                "application/vnd.docker.distribution.manifest.list.v2+json, "
                "application/vnd.oci.image.index.v1+json"
            }

            response = self.session.get(url, headers=headers)
            response.raise_for_status()

            manifest = response.json()
            media_type = manifest.get("mediaType", "")

            manifest["digest"] = response.headers.get("Docker-Content-Digest")

            if media_type == "application/vnd.docker.distribution.manifest.v2+json":
                manifest["type"] = "Image"
            elif media_type == "application/vnd.oci.image.manifest.v1+json":
                manifest["type"] = "OCI Image"
            elif (
                media_type
                == "application/vnd.docker.distribution.manifest.list.v2+json"
            ):
                manifest["type"] = "Manifest List"
            elif media_type == "application/vnd.oci.image.index.v1+json":
                manifest["type"] = "Image"
            else:
                manifest["type"] = "Unknown"

            if "config" in manifest and "layers" in manifest:
                config_digest = manifest["config"]["digest"]
                config_url = f"{self.registry_url}/v2/{repository}/blobs/{config_digest}"
                config_response = self.session.get(
                    config_url, headers={"Accept": manifest["config"]["mediaType"]}
                )
                config_data = config_response.json()

                manifest["os"] = config_data.get("os", "unknown")
                manifest["arch"] = config_data.get("architecture", "unknown")
                manifest["size"] = sum(layer["size"] for layer in manifest["layers"])
            else:
                manifest["os"] = "multi-platform"
                if "manifests" in manifest:
                    manifest["size"] = sum(
                        m.get("size", 0) for m in manifest["manifests"]
                    )
                else:
                    manifest["size"] = 0

            logger.debug(
                "Fetched manifest for %s:%s (digest: %s, size: %d)",
                repository,
                tag_name,
                manifest.get("digest", "unknown")[:12],
                manifest.get("size", 0)
            )
            return manifest

        except requests.exceptions.RequestException as e:
            logger.error(
                "Registry connection failed: unable to fetch manifest for %s:%s - %s",
                repository,
                tag_name,
                str(e)
            )
            raise Exception(f"Failed to fetch tag {repository}:{tag_name}: {str(e)}")

    def get_config_blob(self, repository: str, digest: str) -> Dict:
        try:
            url = f"{self.registry_url}/v2/{repository}/blobs/{digest}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(
                "Registry connection failed: unable to fetch config blob for %s - %s",
                repository,
                str(e)
            )
            raise Exception(f"Failed to fetch config blob {repository}: {str(e)}")

    def delete_manifest(self, repository: str, digest: str) -> bool:
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{digest}"
            response = self.session.delete(url)
            response.raise_for_status()
            logger.info(
                "Manifest deleted from registry: %s (digest: %s)",
                repository,
                digest[:12] if digest else "unknown"
            )
            return True
        except Exception as e:
            logger.error(
                "Registry manifest deletion failed: %s (digest: %s) - %s",
                repository,
                digest[:12] if digest else "unknown",
                str(e)
            )
            return False

    def check_health(self) -> bool:
        try:
            url = f"{self.registry_url}/v2/"
            response = self.session.get(url)
            if response.status_code == 200:
                logger.debug("Registry health check passed: %s", self.registry_url)
                return True
            else:
                logger.warning(
                    "Registry health check failed: %s returned status %d",
                    self.registry_url,
                    response.status_code
                )
                return False
        except Exception as e:
            logger.warning(
                "Registry health check failed: %s - %s",
                self.registry_url,
                str(e)
            )
            return False

    def convert_size(self, size_in_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} TB"
