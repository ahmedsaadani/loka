# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versionnage sémantique.

## [Unreleased]

### Phase 1 — Socle

- Monorepo, docker compose (postgres/postgis, redis, minio, api, worker, web), Dockerfiles multi-stage.
- Makefile et équivalent PowerShell, `.env.example`, GitLab CI (lint, test, build, deploy manuel).
- Documentation : architecture, ADR 0001 à 0004.
- API Django 5.2 : apps `accounts`, `geo`, `listings`, `availability`, `bookings`, `leads`, `reviews` (squelette), `notifications`.
  - User custom (email identifiant), rôles, profils hôte, documents d'identité en bucket privé.
  - Biens avec machine à états, photos ré-encodées et variantes WebP, plans tarifaires par mode.
  - Disponibilités avec contrainte d'exclusion PostgreSQL (`btree_gist`), blocs hôte, import iCal.
  - Demandes de réservation avec devis figé, expiration 48 h et rappel 24 h, réservations, paiement mock signé HMAC, remboursement selon ADR 0005, contrat PDF (WeasyPrint).
  - Leads : import CSV/JSON, statuts, conversion en brouillon de bien.
  - Sécurité : JWT avec refresh en cookie httpOnly et rotation/blacklist, rate limiting par scope, en-têtes CSP, journal des accès sensibles, validation stricte des uploads, UUID dans les URLs.
  - Seed : 3 villes, 10 quartiers, 25 biens publiés avec photos, 4 comptes de test, leads de démo.
  - 297 tests (services, transitions, API par rôle), ruff, mypy strict, bandit, pip-audit.
- Documentation : modèle de données (Mermaid), ADR 0005 (règles de réservation).
