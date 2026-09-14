#!/usr/bin/env sh
# Démarrage de l'API sur Render (plan gratuit : ni startCommand ni preDeployCommand).
# Active PostGIS, applique les migrations et les fichiers statiques, puis lance gunicorn.
set -e

# L'extension peut déjà exister ; IF NOT EXISTS rend l'appel idempotent.
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS postgis'

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 2 --timeout 120
