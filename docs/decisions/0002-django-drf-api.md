# ADR 0002 — API Django + DRF séparée, contrat OpenAPI, une app par domaine

Date : 2026-09-12 · Statut : accepté

## Contexte

Le projet est porté par un seul développeur qui doit pouvoir le reprendre après six mois. Le domaine (biens, disponibilités, réservations, validation par l'équipe) est riche en règles métier et en données sensibles.

## Décision

- Django 5 + Django REST Framework, API versionnée `/api/v1/`, schéma OpenAPI généré par drf-spectacular.
- Le front ne parle jamais à la base : il consomme l'API avec des types TypeScript générés depuis le schéma (`openapi-typescript`). Le contrat est la source de vérité.
- Une app Django par domaine : `accounts`, `geo`, `listings`, `availability`, `bookings`, `leads`, `notifications`, `reviews` (squelette). Pas de modèle « fourre-tout ».
- Auth JWT (simplejwt) : access token court en mémoire côté front, refresh token en cookie httpOnly, `SameSite=Lax`.
- Admin Django conservé comme outil interne de secours ; le back-office équipe est dans Next.js.

## Conséquences

- Tout changement d'API passe par le schéma puis `make types` ; un `tsc` qui casse signale un contrat rompu.
- Les tests d'API sont obligatoires par endpoint (pytest + APIClient).
- CORS restreint aux origines du front.
