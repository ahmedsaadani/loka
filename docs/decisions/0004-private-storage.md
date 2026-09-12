# ADR 0004 — Deux buckets S3, données sensibles uniquement via URLs signées

Date : 2026-09-12 · Statut : accepté

## Contexte

La plateforme stocke des documents d'identité (CIN, passeport), des contrats, les originaux des photos et l'adresse exacte des biens. Une fuite serait grave pour les utilisateurs et pour la crédibilité de Loka.

## Décision

- Deux buckets : `loka-public` (lecture anonyme, variantes WebP des photos, images OG) et `loka-private` (aucun accès anonyme).
- Tout ce qui est sensible va dans `loka-private` : `IdentityDocument.file`, `Booking.contract_pdf`, originaux des `PropertyPhoto`. Le stockage privé est un backend `django-storages` distinct (`core.storages.PrivateMediaStorage`), `querystring_auth=True`, expiration 5 min.
- L'API ne renvoie jamais une clé S3 privée. Elle expose des endpoints dédiés (`/identity-documents/{id}/download/`, `/bookings/{id}/contract/`) qui vérifient la permission, journalisent l'accès (`core.models.SensitiveAccessLog` : qui, quoi, quand, IP) puis redirigent vers une URL signée.
- L'adresse exacte (`address_private`) n'est pas un fichier mais suit la même règle : champ absent des serializers publics, renvoyé par un serializer distinct réservé à l'hôte, au staff et au voyageur d'une réservation confirmée, avec journalisation.
- En dev, MinIO joue ce rôle ; `minio-init` applique la politique anonyme `download` sur le public et `none` sur le privé.

## Conséquences

- Les URLs signées ne sont jamais mises en cache ni loggées en clair.
- Le front n'embarque jamais une URL privée dans le HTML rendu ; il l'obtient à la demande via l'endpoint dédié.
