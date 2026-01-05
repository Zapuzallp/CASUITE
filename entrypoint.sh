#!/bin/bash
set -e

echo "Waiting for MySQL ($DB_HOST:$DB_PORT) to be ready..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "✅ MySQL is up - continuing..."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Django server..."
exec gunicorn CASUITE.wsgi:application --bind 0.0.0.0:8000 --timeout 60