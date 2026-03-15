from django.core.management.base import BaseCommand
from django_elasticsearch_dsl.management.commands import search_index


class Command(BaseCommand):
    help = 'Rebuild Elasticsearch search indexes for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            type=str,
            help='Specific models to rebuild (e.g., clients tasks invoices)',
        )
        parser.add_argument(
            '--populate',
            action='store_true',
            help='Populate the index after rebuilding',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Elasticsearch index rebuild...'))
        
        # Use the built-in search_index command
        from django.core.management import call_command
        
        try:
            # Rebuild and populate indexes
            self.stdout.write('Rebuilding indexes...')
            call_command('search_index', '--rebuild', '-f')
            
            self.stdout.write(self.style.SUCCESS('✓ Elasticsearch indexes rebuilt successfully!'))
            self.stdout.write(self.style.SUCCESS('All data has been indexed.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error rebuilding indexes: {str(e)}'))
            raise