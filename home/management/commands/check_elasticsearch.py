from django.core.management.base import BaseCommand
from django.conf import settings
from elasticsearch import Elasticsearch


class Command(BaseCommand):
    help = 'Check Elasticsearch connection and index status'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Elasticsearch connection...")
        
        try:
            es_config = settings.ELASTICSEARCH_DSL['default']
            es = Elasticsearch(
                es_config['hosts'],
                http_auth=es_config['http_auth'],
                verify_certs=es_config.get('verify_certs', False),
                timeout=es_config.get('timeout', 30)
            )
            
            # Test connection
            info = es.info()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Connected to Elasticsearch cluster: {info['cluster_name']}")
            )
            self.stdout.write(f"   Version: {info['version']['number']}")
            self.stdout.write(f"   Host: {es_config['hosts']}")
            
            # Check cluster health
            health = es.cluster.health()
            status = health['status']
            if status == 'green':
                self.stdout.write(self.style.SUCCESS(f"✅ Cluster health: {status}"))
            elif status == 'yellow':
                self.stdout.write(self.style.WARNING(f"⚠️  Cluster health: {status}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Cluster health: {status}"))
            
            # Check indexes
            indexes = es.cat.indices(format='json')
            search_indexes = [idx for idx in indexes if idx['index'].startswith(
                ('clients', 'tasks', 'invoices', 'employees', 'leads', 'gst_details')
            )]
            
            if search_indexes:
                self.stdout.write(f"📊 Found {len(search_indexes)} search indexes:")
                for idx in search_indexes:
                    docs_count = idx.get('docs.count', '0')
                    size = idx.get('store.size', '0b')
                    self.stdout.write(f"   - {idx['index']}: {docs_count} documents ({size})")
            else:
                self.stdout.write(
                    self.style.WARNING("⚠️  No search indexes found. Run: python manage.py search_index --rebuild -f")
                )
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Elasticsearch connection failed: {e}")
            )
            self.stdout.write(
                self.style.WARNING("⚠️  Search will fallback to database queries")
            )
            return False