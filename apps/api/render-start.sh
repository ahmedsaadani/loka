#!/usr/bin/env sh
# Démarrage de l'API sur Render (plan gratuit : ni startCommand ni preDeployCommand).
# Active PostGIS, applique les migrations et les fichiers statiques, charge les données de
# démonstration au premier démarrage, puis lance gunicorn.
set -e

# L'extension peut déjà exister ; IF NOT EXISTS rend l'appel idempotent.
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS postgis'

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Données de démo au premier démarrage (base vide) : SANS traitement d'images au runtime
# (trop lourd sur le plan gratuit → risque de plantage). Les photos sont servies en statique
# par le front (mode --photo-mode static), donc pas de dépendance à MinIO ni de génération.
if [ "$(python -c 'import django; django.setup(); from listings.models import Property; print(1 if Property.objects.exists() else 0)' 2>/dev/null)" = "0" ]; then
  echo "Base vide : chargement des données de démonstration (photos statiques)."
  python manage.py seed --photo-mode static || echo "seed échoué, on continue."
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 1 --timeout 120
