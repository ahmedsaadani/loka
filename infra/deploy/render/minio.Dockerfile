# MinIO pour un déploiement de test sur Render (stockage S3 compatible).
# Écoute l'API S3 sur $PORT (fourni par Render). Le bucket public est ouvert en lecture,
# le bucket privé reste protégé (URLs signées côté API).
#
# ATTENTION : sans disque persistant attaché (option payante Render), les fichiers sont
# perdus au redémarrage / à la mise en veille du service. Relancer `seed` régénère les photos.
FROM minio/mc:latest AS mc

FROM minio/minio:latest
COPY --from=mc /usr/bin/mc /usr/bin/mc
COPY infra/deploy/render/minio-entrypoint.sh /entrypoint.sh
# L'image minio tourne en root ; on rend le script exécutable.
USER root
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
