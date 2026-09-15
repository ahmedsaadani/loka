#!/usr/bin/env sh
# Démarrage de l'API sur Render (plan gratuit : ni startCommand ni preDeployCommand).
# Active PostGIS, applique les migrations et les fichiers statiques, charge les données de
# démonstration au premier démarrage, puis lance gunicorn.
set -e

# L'extension peut déjà exister ; IF NOT EXISTS rend l'appel idempotent.
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS postgis'

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Données de démonstration AVEC photos. Le traitement d'images tourne en arrière-plan pour ne
# pas retarder le démarrage de gunicorn ; il ne s'exécute qu'une fois (base vide, ou biens
# présents mais sans photos → seed --reset). Sur le plan gratuit le stockage est éphémère :
# après une longue mise en veille, relancer un seed régénère les photos.
HAS_PROP=$(python -c 'import django; django.setup(); from listings.models import Property; print(1 if Property.objects.exists() else 0)' 2>/dev/null)
HAS_PHOTO=$(python -c 'import django; django.setup(); from listings.models import PropertyPhoto; print(1 if PropertyPhoto.objects.exists() else 0)' 2>/dev/null)
if [ "$HAS_PROP" = "0" ]; then
  echo "Base vide : chargement des données de démonstration avec photos."
  (python manage.py seed || echo "seed échoué") &
elif [ "$HAS_PHOTO" = "0" ]; then
  echo "Biens sans photos : rechargement avec photos (seed --reset)."
  (python manage.py seed --reset || echo "seed --reset échoué") &
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 1 --timeout 120
