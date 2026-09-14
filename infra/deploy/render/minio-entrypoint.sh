#!/bin/sh
# Démarre MinIO sur $PORT (API S3) et crée les buckets attendus par l'API Loka.
set -e

PORT="${PORT:-9000}"
PUBLIC_BUCKET="${S3_BUCKET_PUBLIC:-loka-public}"
PRIVATE_BUCKET="${S3_BUCKET_PRIVATE:-loka-private}"

# MinIO utilise MINIO_ROOT_USER / MINIO_ROOT_PASSWORD (fournis par Render).
minio server /data --address ":${PORT}" --console-address ":9001" &
MINIO_PID=$!

# Attend que l'API réponde puis (re)crée les buckets, de façon idempotente.
until mc alias set local "http://127.0.0.1:${PORT}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 1
done
mc mb --ignore-existing "local/${PUBLIC_BUCKET}"
mc mb --ignore-existing "local/${PRIVATE_BUCKET}"
mc anonymous set download "local/${PUBLIC_BUCKET}"
mc anonymous set none "local/${PRIVATE_BUCKET}"
echo "MinIO prêt : buckets ${PUBLIC_BUCKET} (public) et ${PRIVATE_BUCKET} (privé)."

wait "$MINIO_PID"
