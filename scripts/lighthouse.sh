#!/usr/bin/env bash
# Mesure Lighthouse (mobile) des pages publiques sur l'image de production du front.
# Usage : scripts/lighthouse.sh [--no-build] [--threshold 85] [--base http://localhost:3000]
#   - construit l'image loka-web:prod, la lance sur le port 3000 (l'API doit tourner : make dev),
#   - audite l'accueil, une page ville et une fiche bien (slug pris dans l'API),
#   - échoue si le score performance mobile d'une page est sous le seuil (85 par défaut).
# Prérequis : Node 20+, Chrome/Chromium installé (Lighthouse utilise le Chrome de la machine).
set -euo pipefail

THRESHOLD=85
BASE_URL="http://localhost:3000"
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:18000/api/v1}"
BUILD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --threshold) THRESHOLD="$2"; shift ;;
    --base) BASE_URL="$2"; shift ;;
    *) echo "Option inconnue : $1" >&2; exit 2 ;;
  esac
  shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/.lighthouse"
mkdir -p "$OUT"

if [[ "$BUILD" == "1" ]]; then
  echo "▶ Build de l'image de production loka-web:prod"
  docker build -f "$ROOT/infra/docker/web.Dockerfile" --target prod \
    --build-arg NEXT_PUBLIC_API_URL="$API_URL" -t loka-web:prod "$ROOT/apps/web" >/dev/null
fi

if [[ "$BASE_URL" == "http://localhost:3000" ]]; then
  echo "▶ Démarrage du conteneur loka-web-lighthouse sur :3000"
  docker rm -f loka-web-lighthouse >/dev/null 2>&1 || true
  docker run -d --name loka-web-lighthouse --network loka_default -p 3000:3000 \
    -e API_INTERNAL_URL=http://api:8000/api/v1 -e NEXT_PUBLIC_SITE_URL="$BASE_URL" \
    loka-web:prod >/dev/null
  trap 'docker rm -f loka-web-lighthouse >/dev/null 2>&1 || true' EXIT
  for _ in $(seq 1 30); do
    curl -fs -o /dev/null "$BASE_URL/" && break
    sleep 2
  done
fi

CITY="$(curl -fs "$API_URL/geo/cities/?page_size=1" | python -c 'import json,sys; print(json.load(sys.stdin)["results"][0]["slug"])')"
SLUG="$(curl -fs "$API_URL/listings/properties/?page_size=1" | python -c 'import json,sys; print(json.load(sys.stdin)["results"][0]["slug"])')"
PAGES=("/" "/location/$CITY" "/logement/$SLUG")

STATUS=0
for page in "${PAGES[@]}"; do
  name="$(echo "$page" | tr '/' '_' | sed 's/^_//')"; [[ -z "$name" ]] && name="accueil"
  echo "▶ Audit mobile : $BASE_URL$page"
  npx --yes lighthouse@12 "$BASE_URL$page" --preset=perf --form-factor=mobile --screenEmulation.mobile \
    --only-categories=performance,accessibility,best-practices,seo --quiet \
    --chrome-flags="--headless=new --no-sandbox" --output=json --output=html \
    --output-path="$OUT/$name" >/dev/null
  SCORES="$(python - "$OUT/$name.report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))["categories"]
print(" ".join(f"{k}={round(v['score']*100)}" for k, v in r.items()))
PY
)"
  PERF="$(echo "$SCORES" | sed -E 's/.*performance=([0-9]+).*/\1/')"
  echo "   $SCORES"
  if (( PERF < THRESHOLD )); then
    echo "   ✖ performance $PERF < $THRESHOLD"
    STATUS=1
  fi
done

echo "Rapports HTML : $OUT/*.report.html"
exit $STATUS
