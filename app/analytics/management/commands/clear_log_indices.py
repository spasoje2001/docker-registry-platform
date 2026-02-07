"""
Management command to clear all log indices from Elasticsearch.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from elasticsearch import Elasticsearch


class Command(BaseCommand):
    help = 'Delete all log indices from Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        es = Elasticsearch([settings.ELASTICSEARCH_URL])

        if not es.ping():
            self.stderr.write(
                self.style.ERROR('Failed to connect to Elasticsearch')
            )
            return

        # Get all log indices
        try:
            indices = es.indices.get(index='docker-registry-logs-*')
        except Exception:
            indices = {}

        if not indices:
            self.stdout.write('No log indices found.')
            return

        self.stdout.write(f'Found {len(indices)} indices:')
        for name in indices.keys():
            self.stdout.write(f'  - {name}')

        # Confirm deletion
        if not options['yes']:
            confirm = input('\nDelete all these indices? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled.')
                return

        # Delete each index
        deleted = 0
        for index_name in indices.keys():
            try:
                es.indices.delete(index=index_name)
                self.stdout.write(f'Deleted: {index_name}')
                deleted += 1
            except Exception as e:
                self.stderr.write(f'Failed to delete {index_name}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'\nDeleted {deleted} indices.')
        )

        # Also clear the indexer state file
        from pathlib import Path
        state_file = Path(settings.BASE_DIR) / "logs" / ".indexer_state.json"
        if state_file.exists():
            state_file.unlink()
            self.stdout.write('Cleared indexer state file.')