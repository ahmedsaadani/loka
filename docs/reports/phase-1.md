# Rapport Phase 1 — Socle

Commits : `f3857f3` (monorepo), `c7877d1` (API), `2d04b7e` (front).

## Fait

- Monorepo `apps/api` (Django 5.2, DRF 3.17, PostGIS 16, Redis, Celery, MinIO) et `apps/web` (Next.js 15, Tailwind, shadcn), docker compose, Dockerfiles multi-stage, Makefile et `scripts/dev.ps1`, GitLab CI (lint, tests avec PostGIS, sécurité, build, déploiement manuel).
- Modèle de données complet (ADR 0003, `docs/data-model.md`) : User custom email dès la première migration, profils hôte, documents d'identité, géographie PostGIS, biens, photos, plans tarifaires, disponibilités avec contrainte d'exclusion `btree_gist`, demandes, réservations, paiements, leads, avis (squelette).
- Machines à états explicites (`core.state.transition`) journalisées dans `StatusLog` ; journal d'accès sensible (`SensitiveAccessLog`).
- Sécurité : JWT court + refresh httpOnly avec rotation et blacklist, rate limiting par scope, CSP et en-têtes, uploads validés par type réel et ré-encodés, buckets public / privé avec URLs signées (ADR 0004), UUID dans les URLs.
- Seed : 3 villes, 10 quartiers, 25 biens avec photos WebP générées, 4 comptes, leads.
- Front : tokens de design (terracotta appliqué, bleu méditerranée en réserve), primitives UI, header / footer / navigation mobile, client API typé, contrat de types vérifié contre le schéma OpenAPI généré.

## Tester

```bash
cp .env.example .env
make dev && make seed
make lint && make test && make audit
```

API : http://localhost:18000/api/v1/docs/ · Web : http://localhost:3000

## Reste / questions ouvertes

- OTP SMS (prévu plus tard), i18n AR/EN (structure prête, contenu FR).
- `make` absent sur la machine de dev : utiliser `powershell -File scripts/dev.ps1 <cible>`.
- Ports hôtes déplacés (API 18000, PostgreSQL 15432, Redis 16379) pour cohabiter avec d'autres projets Docker de la machine.
