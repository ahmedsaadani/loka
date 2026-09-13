#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Déploiement Loka sur le VPS (idempotent). À lancer depuis /opt/loka :
#
#   ./deploy.sh                       # déploie IMAGE_TAG de .env.prod
#   ./deploy.sh --tag a1b2c3d4        # déploie un tag précis (SHA court CI)
#   ./deploy.sh --tag a1b2c3d4 --no-migrate
#   ./deploy.sh --rollback            # revient au tag précédent (.deploy/previous_tag)
#
# Étapes : login registre -> pull -> migrate + collectstatic (conteneur éphémère)
# -> up -d -> attente des healthchecks -> revalidation ISR de / -> prune.
# En cas d'échec APRÈS `up`, retour automatique au tag précédent (images seulement :
# les migrations ne sont pas annulées, elles doivent rester rétro-compatibles).
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_PATH=$(readlink -f "$0")
cd "$(dirname "$SCRIPT_PATH")"

ENV_FILE=.env.prod
COMPOSE_FILE=docker-compose.prod.yml
STATE_DIR=.deploy
HEALTH_TIMEOUT=${HEALTH_TIMEOUT:-180}

# --- affichage --------------------------------------------------------------
if [[ -t 1 ]]; then
  C_INFO=$'\033[1;34m'; C_OK=$'\033[1;32m'; C_WARN=$'\033[1;33m'; C_ERR=$'\033[1;31m'; C_END=$'\033[0m'
else
  C_INFO=; C_OK=; C_WARN=; C_ERR=; C_END=
fi
log()  { printf '%s[deploy]%s %s\n' "$C_INFO" "$C_END" "$*"; }
ok()   { printf '%s[  ok  ]%s %s\n' "$C_OK" "$C_END" "$*"; }
warn() { printf '%s[ warn ]%s %s\n' "$C_WARN" "$C_END" "$*" >&2; }
err()  { printf '%s[ erreur ]%s %s\n' "$C_ERR" "$C_END" "$*" >&2; }

# --- arguments --------------------------------------------------------------
TAG=""
MIGRATE=1
ROLLBACK=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) [[ $# -ge 2 ]] || { err "--tag attend une valeur"; exit 2; }; TAG=$2; shift ;;
    --tag=*) TAG=${1#--tag=} ;;
    --no-migrate) MIGRATE=0 ;;
    --rollback) ROLLBACK=1 ;;
    -h|--help) sed -n '2,14p' "$SCRIPT_PATH"; exit 0 ;;
    *) err "Option inconnue : $1"; exit 2 ;;
  esac
  shift
done

# --- helpers ----------------------------------------------------------------
[[ -f "$ENV_FILE" ]] || { err "$ENV_FILE introuvable (cp .env.prod.example .env.prod)"; exit 1; }
[[ -f "$COMPOSE_FILE" ]] || { err "$COMPOSE_FILE introuvable"; exit 1; }
mkdir -p "$STATE_DIR"

# Lecture d'une variable dans .env.prod (sans `source` : certaines valeurs contiennent '<').
env_get() {
  local line
  line=$(grep -E "^$1=" "$ENV_FILE" | tail -n1 || true)
  line=${line#*=}
  line=${line%\"}; line=${line#\"}
  line=${line%\'}; line=${line#\'}
  printf '%s' "$line"
}

# Écrit (ou ajoute) KEY=value dans .env.prod.
env_set() {
  if grep -qE "^$1=" "$ENV_FILE"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"
  fi
}

DOMAIN=$(env_get DOMAIN)
REGISTRY_IMAGE=$(env_get REGISTRY_IMAGE)
REGISTRY_USER=${REGISTRY_USER:-$(env_get REGISTRY_USER)}
REGISTRY_PASSWORD=${REGISTRY_PASSWORD:-$(env_get REGISTRY_PASSWORD)}
REVALIDATE_SECRET=$(env_get REVALIDATE_SECRET)
export COMPOSE_PROFILES=${COMPOSE_PROFILES:-$(env_get COMPOSE_PROFILES)}

[[ -n "$DOMAIN" && -n "$REGISTRY_IMAGE" ]] || { err "DOMAIN et REGISTRY_IMAGE doivent être définis dans $ENV_FILE"; exit 1; }

# `IMAGE_TAG` est passé explicitement à chaque commande compose (prioritaire sur .env.prod).
compose() { IMAGE_TAG="$DEPLOY_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

container_health() {  # $1 = service ; affiche healthy|unhealthy|starting|none|missing
  local id
  id=$(compose ps -q "$1" 2>/dev/null | head -n1)
  [[ -n "$id" ]] || { echo missing; return; }
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id"
}

wait_healthy() {
  local deadline=$(( $(date +%s) + HEALTH_TIMEOUT )) svc status pending
  log "Attente des healthchecks (max ${HEALTH_TIMEOUT}s) : api, web, nginx"
  while :; do
    pending=""
    for svc in api web nginx; do
      status=$(container_health "$svc")
      case "$status" in
        healthy|none) ;;
        unhealthy) err "Service $svc : unhealthy"; compose logs --tail=50 "$svc" >&2 || true; return 1 ;;
        *) pending="$pending $svc($status)" ;;
      esac
    done
    [[ -z "$pending" ]] && break
    if (( $(date +%s) > deadline )); then
      err "Délai dépassé, services non prêts :$pending"
      return 1
    fi
    sleep 5
  done
  ok "Conteneurs api, web, nginx sains"

  if command -v curl >/dev/null 2>&1; then
    local url code
    for url in "https://$DOMAIN/api/v1/health/" "https://$DOMAIN/"; do
      code=""
      for _ in 1 2 3 4 5 6; do
        code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$url" || true)
        [[ "$code" == "200" ]] && break
        sleep 5
      done
      if [[ "$code" == "200" ]]; then ok "GET $url -> 200"; else err "GET $url -> ${code:-aucune réponse}"; return 1; fi
    done
  else
    warn "curl absent sur l'hôte : vérification HTTPS externe ignorée"
  fi
}

revalidate_home() {
  [[ -n "$REVALIDATE_SECRET" ]] || { warn "REVALIDATE_SECRET vide : revalidation ISR ignorée"; return 0; }
  log "Revalidation ISR de la page d'accueil"
  if compose exec -T web wget -qO- \
       --post-data='{"paths":["/"]}' \
       --header="Content-Type: application/json" \
       --header="X-Revalidate-Secret: $REVALIDATE_SECRET" \
       http://localhost:3000/api/revalidate >/dev/null; then
    ok "Page / revalidée"
  else
    warn "Revalidation ISR échouée (non bloquant)"
  fi
}

registry_login() {
  if [[ -n "$REGISTRY_USER" && -n "$REGISTRY_PASSWORD" ]]; then
    log "Connexion au registre ${REGISTRY_IMAGE%%/*}"
    printf '%s' "$REGISTRY_PASSWORD" | docker login -u "$REGISTRY_USER" --password-stdin "${REGISTRY_IMAGE%%/*}" >/dev/null
    ok "Authentifié sur le registre"
  fi
}

pull_and_up() {
  log "Pull des images $REGISTRY_IMAGE/{api,web}:$DEPLOY_TAG"
  compose pull --quiet
  ok "Images récupérées"

  # Les volumes nommés sont créés root ; l'API tourne en utilisateur `app`.
  log "Préparation des volumes (staticfiles, planning Celery beat)"
  compose run --rm --no-deps --user root --entrypoint sh api -c 'mkdir -p /app/staticfiles && chown -R app:app /app/staticfiles' >/dev/null
  compose run --rm --no-deps --user root --entrypoint sh beat -c 'mkdir -p /var/lib/celery && chown -R app:app /var/lib/celery' >/dev/null

  # `run` (sans --no-deps) démarre postgres et redis si nécessaire (premier déploiement).
  if [[ $MIGRATE -eq 1 ]]; then
    log "Migrations Django (forward-only)"
    compose run --rm --entrypoint python api manage.py migrate --noinput
    ok "Migrations appliquées"
  else
    warn "Migrations ignorées (--no-migrate)"
  fi

  log "collectstatic vers le volume django_static"
  compose run --rm --entrypoint python api manage.py collectstatic --noinput --clear >/dev/null
  ok "Statiques collectés"

  log "docker compose up -d --remove-orphans"
  compose up -d --remove-orphans
}

rollback_to_previous() {
  local prev
  prev=$(cat "$STATE_DIR/previous_tag" 2>/dev/null || true)
  if [[ -z "$prev" ]]; then
    err "Aucun tag précédent enregistré ($STATE_DIR/previous_tag) : rollback impossible"
    return 1
  fi
  warn "ROLLBACK vers le tag $prev (images uniquement, migrations conservées)"
  DEPLOY_TAG=$prev
  MIGRATE=0
  pull_and_up || return 1
  wait_healthy || return 1
  env_set IMAGE_TAG "$prev"
  echo "$prev" > "$STATE_DIR/current_tag"
  ok "Rollback terminé : $prev est en production"
}

# --- déroulé -----------------------------------------------------------------
CURRENT_TAG=$(cat "$STATE_DIR/current_tag" 2>/dev/null || env_get IMAGE_TAG)

if [[ $ROLLBACK -eq 1 ]]; then
  registry_login
  DEPLOY_TAG=$CURRENT_TAG
  rollback_to_previous
  exit $?
fi

DEPLOY_TAG=${TAG:-$(env_get IMAGE_TAG)}
[[ -n "$DEPLOY_TAG" ]] || { err "Aucun tag : --tag <IMAGE_TAG> ou IMAGE_TAG dans $ENV_FILE"; exit 1; }

log "Déploiement de $REGISTRY_IMAGE:$DEPLOY_TAG sur https://$DOMAIN (actuel : ${CURRENT_TAG:-aucun})"
registry_login

# Enregistre l'état avant de toucher aux conteneurs.
if [[ -n "$CURRENT_TAG" && "$CURRENT_TAG" != "$DEPLOY_TAG" ]]; then
  echo "$CURRENT_TAG" > "$STATE_DIR/previous_tag"
fi
echo "$DEPLOY_TAG" > "$STATE_DIR/current_tag"

# SENTRY_RELEASE suit le tag déployé, sauf si l'opérateur a fixé une valeur explicite.
SENTRY_RELEASE_FILE=$(env_get SENTRY_RELEASE)
if [[ -z "$SENTRY_RELEASE_FILE" || "$SENTRY_RELEASE_FILE" == "$CURRENT_TAG" ]]; then
  env_set SENTRY_RELEASE "$DEPLOY_TAG"
fi

pull_and_up
env_set IMAGE_TAG "$DEPLOY_TAG"

if ! wait_healthy; then
  err "Le déploiement de $DEPLOY_TAG a échoué après le démarrage"
  if [[ -f "$STATE_DIR/previous_tag" && "$(cat "$STATE_DIR/previous_tag")" != "$DEPLOY_TAG" ]]; then
    rollback_to_previous || err "Le rollback a lui aussi échoué : intervention manuelle requise"
  else
    err "Pas de version précédente différente : intervention manuelle requise"
  fi
  exit 1
fi

revalidate_home

log "Nettoyage des images inutilisées"
docker image prune -f --filter "until=72h" >/dev/null || true

ok "Déploiement de $DEPLOY_TAG terminé : https://$DOMAIN"
date -u +"%Y-%m-%dT%H:%M:%SZ $DEPLOY_TAG" >> "$STATE_DIR/history.log"
