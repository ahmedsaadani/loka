#!/usr/bin/env sh
# Démarrage de l'API sur Render (plan gratuit : ni startCommand ni preDeployCommand).
# Active PostGIS, applique les migrations et les fichiers statiques, charge les données de
# démonstration au premier démarrage, puis lance gunicorn.
set -e

# L'extension peut déjà exister ; IF NOT EXISTS rend l'appel idempotent.
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS postgis'

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Données de démo au premier démarrage seulement (base vide). Sans photos : fiable sur le
# plan gratuit (le traitement d'images est lourd et le stockage y est éphémère). Les fiches
# sans image affichent proprement « Photos en préparation ».
if [ "$(python -c 'import django; django.setup(); from listings.models import Property; print(1 if Property.objects.exists() else 0)' 2>/dev/null)" = "0" ]; then
  echo "Base vide : chargement des données de démonstration (seed --no-photos)."
  python manage.py seed --no-photos || echo "seed a échoué, on continue quand même."
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 2 --timeout 120
