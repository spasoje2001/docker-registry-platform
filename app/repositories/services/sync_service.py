"""
Service for synchronizing Docker registry tags with Django database.

"""
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

from django.db import transaction, models
from django.utils import timezone

from ..models import Repository, Tag
from repositories.clients.registry_client import RegistryClient


logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Statistics from a tag synchronization operation."""
    repos_processed: int = 0
    repos_skipped: int = 0
    tags_created: int = 0
    tags_updated: int = 0
    tags_deleted: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def __str__(self):
        return (
            f"Sync completed: {self.repos_processed} repos processed, "
            f"{self.repos_skipped} skipped, {self.tags_created} tags created, "
            f"{self.tags_updated} updated, {self.tags_deleted} deleted, "
            f"{len(self.errors)} errors"
        )


class SyncService:
    """Service for synchronizing registry tags with database."""

    def __init__(self, registry_client: RegistryClient = None):
        """Initialize the tag sync service."""

        self.registry_client = registry_client or RegistryClient()
        self.stats = SyncStats()

    def sync_all_tags(self) -> SyncStats:
        """Synchronize tags for all repositories in the database."""

        logger.info("Starting full tag synchronization")
        repositories = Repository.objects.all()
        
        for repo in repositories:
            try:
                self.sync_repository_tags(repo)
            except Exception as e:
                error_msg = f"Failed to sync repository {repo.name}: {str(e)}"
                logger.error(error_msg)
                self.stats.errors.append(error_msg)
                self.stats.repos_skipped += 1
        
        logger.info(str(self.stats))
        return self.stats

    def sync_repository_tags(self, repository: Repository) -> Tuple[int, int, int]:
        """Synchronize tags for a specific repository."""

        logger.info(f"Syncing tags for repository: {repository.name}")

        try:
            registry_tags = self._fetch_registry_tags(repository.name)
        except Exception as e:
            logger.error(f"Failed to fetch tags from registry for {repository.name}: {e}")
            raise

        with transaction.atomic():
            created, updated, deleted = self._sync_tags_transaction(
                repository, registry_tags
            )

        self.stats.repos_processed += 1
        self.stats.tags_created += created
        self.stats.tags_updated += updated
        self.stats.tags_deleted += deleted

        logger.info(
            f"Repository {repository.name}: "
            f"{created} created, {updated} updated, {deleted} deleted"
        )

        return created, updated, deleted

    def _fetch_registry_tags(self, repo_name: str) -> Dict[str, Dict]:
        """Fetch tags and their digests from the registry."""

        tags_list = self.registry_client.get_tags_for_repository(repo_name)
        tags = {}

        if tags_list:
            for tag_name in tags_list:
                try:
                    manifest = self.registry_client.get_manifest(repo_name, tag_name)   
                    digest = manifest.get('digest')        
                    size = manifest.get('size', 0)
                    os = manifest.get('os', '')
                    arch = manifest.get('arch', '')
                    image_type = manifest.get('mediaType', '').split('.')[-3]
                    
                    tags[tag_name] = {
                        'digest': digest,
                        'size': size,
                        'os': os,
                        'arch': arch,
                        'image_type': image_type
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to get digest for {repo_name}:{tag_name}: {e}"
                    )
                    continue
        
        return tags

    def _sync_tags_transaction(
        self, 
        repository: Repository, 
        registry_tags: Dict[str, Dict]
    ) -> Tuple[int, int, int]:
        """Synchronize tags within a database transaction."""

        created_count = 0
        updated_count = 0
        deleted_count = 0

        # Get existing tags for this repository
        existing_tags = {
            tag.name: tag 
            for tag in Tag.objects.filter(repository=repository)
        }

        registry_tag_names = set(registry_tags.keys())
        existing_tag_names = set(existing_tags.keys())

        if registry_tags:
            new_tag_names = registry_tag_names - existing_tag_names
            for tag_name in new_tag_names:
                tag_data = registry_tags[tag_name]

                Tag.objects.create(
                    repository=repository,
                    name=tag_name,
                    digest=tag_data.get('digest', ''),
                    size=tag_data.get('size', 0),
                    os=tag_data.get('os', ''),
                    arch=tag_data.get('arch', ''),
                    image_type=tag_data.get('image_type', ''),
                    last_synced=timezone.now()
                )
                created_count += 1
                logger.debug(f"Created tag: {repository.name}:{tag_name}")

            common_tag_names = registry_tag_names & existing_tag_names
            for tag_name in common_tag_names:
                tag = existing_tags[tag_name]
                tag_data = registry_tags[tag_name]
                new_digest = tag_data.get('digest', '')
                
                if tag.digest != new_digest:
                    tag.digest = new_digest
                    tag.size = tag_data.get('size', 0)
                    tag.os = tag_data.get('os', '')
                    tag.arch = tag_data.get('arch', '')
                    tag.image_type = tag_data.get('image_type', '')
                    tag.last_synced = timezone.now()
                    tag.save(update_fields=[
                        'digest', 'size', 'os', 'arch', 'image_type',
                        'last_synced'
                    ])
                    updated_count += 1
                    logger.debug(
                        f"Updated tag: {repository.name}:{tag_name} "
                        f"(digest changed)"
                    )
                else:
                    tag.last_synced = timezone.now()
                    tag.save(update_fields=['last_synced'])

        deleted_tag_names = existing_tag_names - registry_tag_names
        for tag_name in deleted_tag_names:
            tag = existing_tags[tag_name]
            Tag.objects.filter(repository=repository, name=tag_name).delete()
            deleted_count += 1
            logger.debug(f"Deleted tag: {repository.name}:{tag_name}")

        return created_count, updated_count, deleted_count

    def sync_repository_by_name(self, repo_name: str) -> Tuple[int, int, int]:
        """Synchronize tags for a repository by name"""
        repository = Repository.objects.get(name=repo_name)
        return self.sync_repository_tags(repository)