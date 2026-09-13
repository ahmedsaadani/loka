#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Obtention du PREMIER certificat Let's Encrypt pour ${DOMAIN} (et www.${DOMAIN}).
#
# À lancer une seule fois depuis /opt/loka, après avoir créé .env.prod et vérifié
# que les enregistrements DNS pointent vers ce serveur :
#
#   ./init-letsencrypt.sh            # certificat de production
#   ./init-letsencrypt.sh --staging  # certificat de test (pas de quota, non reconnu par les navigateurs)
#   ./init-letsencrypt.sh --no-www   # ne pas inclure www.${DOMAIN}
#
# Étapes : nginx en configuration d'amorçage (HTTP seul, défi ACME) -> certbot
# certonly (webroot) -> nginx en configuration réelle (HTTPS).
# Les renouvellements sont ensuite assurés par le conteneur `certbot` du compose.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_PATH=$(readlink -f "$0")
cd "$(dirname "$SCRIPT_PATH")"

ENV_FILE=.env.prod
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)

STAGING=0
WITH_WWW=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --staging) STAGING=1 ;;
    --no-www)  WITH_WWW=0 ;;
    -h|--help) sed -n '2,15p' "$SCRIPT_PATH"; exit 0 ;;
    *) echo "Option inconnue : $1" >&2; exit 2 ;;
  esac
  shift
done

# Lecture d'une variable dans .env.prod (sans `source` : les valeurs contiennent des '<').
env_get() {
  local line
  line=$(grep -E "^$1=" "$ENV_FILE" | tail -n1 || true)
  line=${line#*=}
  line=${line%\"}; line=${line#\"}
  line=${line%\'}; line=${line#\'}
  printf '%s' "$line"
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier $ENV_FILE introuvable (cp .env.prod.example .env.prod)." >&2
  exit 1
fi

DOMAIN=$(env_get DOMAIN)
EMAIL=$(env_get LETSENCRYPT_EMAIL)
if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "DOMAIN et LETSENCRYPT_EMAIL doivent être définis dans $ENV_FILE." >&2
  exit 1
fi

DOMAIN_ARGS=(-d "$DOMAIN")
[[ $WITH_WWW -eq 1 ]] && DOMAIN_ARGS+=(-d "www.$DOMAIN")
STAGING_ARGS=()
[[ $STAGING -eq 1 ]] && STAGING_ARGS=(--staging)

# Certificat déjà présent ?
if "${COMPOSE[@]}" run --rm --no-deps --entrypoint sh certbot \
     -c "test -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem" 2>/dev/null; then
  echo "Un certificat existe déjà pour $DOMAIN (/etc/letsencrypt/live/$DOMAIN)."
  echo "Pour le régénérer : docker compose --env-file $ENV_FILE -f docker-compose.prod.yml run --rm certbot delete --cert-name $DOMAIN"
  exit 0
fi

echo "==> 1/4 Démarrage de nginx en configuration d'amorçage (HTTP seul)"
"${COMPOSE[@]}" stop nginx >/dev/null 2>&1 || true
NGINX_TEMPLATE=bootstrap.conf.template "${COMPOSE[@]}" up -d --no-deps --force-recreate nginx

echo "==> 2/4 Vérification que le défi ACME est joignable en local"
for i in $(seq 1 10); do
  if curl -fsS "http://127.0.0.1/healthz" >/dev/null 2>&1; then break; fi
  sleep 2
  [[ $i -eq 10 ]] && { echo "nginx ne répond pas sur le port 80." >&2; exit 1; }
done

echo "==> 3/4 Demande du certificat (${DOMAIN_ARGS[*]}) ${STAGING_ARGS[*]:-}"
"${COMPOSE[@]}" run --rm --no-deps --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  "${DOMAIN_ARGS[@]}" \
  --email "$EMAIL" --agree-tos --no-eff-email \
  --rsa-key-size 4096 --non-interactive \
  "${STAGING_ARGS[@]}"

echo "==> 4/4 Bascule de nginx sur la configuration HTTPS"
"${COMPOSE[@]}" up -d --no-deps --force-recreate nginx
"${COMPOSE[@]}" up -d certbot

echo "Certificat obtenu. Vérifier : curl -I https://$DOMAIN/healthz"
[[ $STAGING -eq 1 ]] && echo "ATTENTION : certificat de STAGING. Relancer sans --staging après suppression (certbot delete --cert-name $DOMAIN)."
exit 0
