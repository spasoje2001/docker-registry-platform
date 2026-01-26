from django.core.management.base import BaseCommand

from ...services import LogIndexer


class Command(BaseCommand):
    help = 'Index Django log files into Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            choices=['app', 'access', 'error'],
            help='Index only specific log file'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Re-index all logs (ignore position tracking)'
        )

    def handle(self, *args, **options):
        indexer = LogIndexer()

        if not indexer.connect():
            self.stderr.write(
                self.style.ERROR('Failed to connect to Elasticsearch')
            )
            return

        file_option = options.get('file')
        full_reindex = options.get('full', False)

        if file_option:
            # Index specific file
            from pathlib import Path
            from django.conf import settings

            log_path = Path(settings.BASE_DIR) / "logs" / f"{file_option}.log"
            self.stdout.write(f"Indexing {file_option}.log...")

            stats = indexer.index_log_file(log_path, full_reindex)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Indexed: {stats['indexed']}, "
                    f"Skipped: {stats['skipped']}, "
                    f"Errors: {stats['errors']}"
                )
            )
        else:
            # Index all files
            self.stdout.write("Indexing all log files...")
            stats = indexer.index_all_logs(full_reindex)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Total - Indexed: {stats['indexed']}, "
                    f"Skipped: {stats['skipped']}, "
                    f"Errors: {stats['errors']}"
                )
            )
