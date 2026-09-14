#!/usr/bin/env sh
# Démarre MinIO sur $PORT (API S3) et crée les buckets attendus par l'API Loka.
# Les noms de buckets sont fixes (identiques au défaut applicatif) pour éviter toute
# dépendance à des variables d'environnement au démarrage.
set -e

PORT="${PORT:-10000}"

minio server /data --address ":${PORT}" --console-address ":9001" &
MINIO_PID=$!

# Attend que l'API réponde, puis (re)crée les buckets de façon idempotente.
until mc alias set local "http://127.0.0.1:${PORT}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 1
done
mc mb --ignore-existing local/loka-public
mc mb --ignore-existing local/loka-private
mc anonymous set download local/loka-public
mc anonymous set none local/loka-private
echo "MinIO prêt : buckets loka-public (public) et loka-private (privé)."

wait "$MINIO_PID"
