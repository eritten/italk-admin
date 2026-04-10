#!/usr/bin/env sh
set -eu

python manage.py migrate
python manage.py seed_initial_data
exec gunicorn config.wsgi:application --bind 0.0.0.0:3000 --workers 3 --timeout 60
