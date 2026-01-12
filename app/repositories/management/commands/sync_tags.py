"""
Management command for synchronizing Docker registry tags with Django database.

Usage:
    python manage.py sync_tags                    # Sync all repositories
    python manage.py sync_tags --repo myapp       # Sync specific repository
    python manage.py sync_tags --verbose          # Verbose output
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from repositories.services import SyncService
from repositories.models import Repository

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            type=str,
            help="Sync tags only for specified repository name",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )

    def handle(self, *args, **options):
        """Execute the tag synchronization command."""
        # Configure logging based on verbosity
        if options["verbose"]:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
            )

        repo_name = options.get("repo")
        try:
            service = SyncService()

            if repo_name:
                self._sync_single_repository(service, repo_name)
            else:
                self._sync_all_repositories(service)

        except DatabaseError as e:
            raise CommandError(f"Database error: {e}")
        except Exception as e:
            raise CommandError(f"Sync failed: {e}")

    def _sync_single_repository(self, service: SyncService, repo_name: str):
        """Sync tags for a single repository."""
        self.stdout.write(f"Synchronizing repository: {repo_name}")
        try:
            created, updated, deleted = service.sync_repository_by_name(repo_name)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Repository {repo_name}: "
                    f"{created} created, {updated} updated, {deleted} deleted"
                )
            )

        except Repository.DoesNotExist:
            raise CommandError(
                f'Repository "{repo_name}" not found in database. '
                f"Please create the repository first."
            )
        except Exception as e:
            raise CommandError(f"Failed to sync repository {repo_name}: {e}")

    def _sync_all_repositories(self, service: SyncService):
        """Sync tags for all active repositories."""
        self.stdout.write("Synchronizing repositories...")
        stats = service.sync_all_tags()

        # Output results
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Synchronization complete!"))
        self.stdout.write(f"  Repositories processed: {stats.repos_processed}")
        self.stdout.write(f"  Repositories skipped:   {stats.repos_skipped}")
        self.stdout.write(f"  Tags created:           {stats.tags_created}")
        self.stdout.write(f"  Tags updated:           {stats.tags_updated}")
        self.stdout.write(f"  Tags deleted:           {stats.tags_deleted}")
        if stats.errors:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"Errors ({len(stats.errors)}):"))
            for error in stats.errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        # Exit with error code if there were errors
        if stats.errors and stats.repos_processed == 0:
            raise CommandError("All repositories failed to sync")
