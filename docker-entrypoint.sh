#!/usr/bin/env sh
set -eu

attempt=0
until python manage.py migrate; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 20 ]; then
    echo "Database did not become ready in time." >&2
    exit 1
  fi
  echo "Waiting for database to become ready..."
  sleep 3
done

python manage.py seed_initial_data
exec gunicorn config.wsgi:application --bind 0.0.0.0:3000 --workers 3 --timeout 60
