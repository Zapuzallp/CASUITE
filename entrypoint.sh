#!/bin/bash
set -e

echo "Waiting for MySQL ($DB_HOST:$DB_PORT) to be ready..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "✅ MySQL is up - continuing..."

# Wait for Elasticsearch if configured
if [ ! -z "$ELASTICSEARCH_HOST" ]; then
  echo "Waiting for Elasticsearch to be ready..."
  until curl -s -u "$ELASTICSEARCH_USER:$ELASTICSEARCH_PASSWORD" "$ELASTICSEARCH_HOST/_cluster/health" > /dev/null 2>&1; do
    echo "Elasticsearch not ready, waiting..."
    sleep 5
  done
  echo "✅ Elasticsearch is up - continuing..."
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Build Elasticsearch indexes if available
if [ ! -z "$ELASTICSEARCH_HOST" ]; then
  echo "Checking Elasticsearch connection..."
  python manage.py check_elasticsearch || echo "⚠️ Elasticsearch not available, will use database fallback"

  echo "Building search indexes..."
  python manage.py search_index --rebuild -f || echo "⚠️ Failed to build search indexes, will use database fallback"
fi

echo "Starting Django server..."
exec gunicorn CASUITE.wsgi:application --bind 0.0.0.0:8000 --timeout 120