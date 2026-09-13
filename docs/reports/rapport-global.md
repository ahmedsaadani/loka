# Rapport global — MVP Loka (Phases 1 à 5)

Date : 2026-09-13 · Branche `main`, 7 commits, dépôt local sans remote.

## État

| Domaine | Livré | Vérification |
|---|---|---|
| API Django 5.2 / DRF 3.17 | 8 apps, 76 routes documentées OpenAPI, machines à états, sécurité (ADR 0004) | 313 tests pytest, couverture 93 %, ruff, mypy strict, bandit 0, pip-audit 0 |
| Front Next.js 15 | public SEO, auth, espaces voyageur / hôte / équipe, paiement mock | tsc strict (0 `any`), eslint, prettier, 16 tests vitest dont contrat de types vs OpenAPI |
| Parcours critiques | recherche → fiche → demande, création d'un bien, validation équipe, gardes de rôle | 5 tests Playwright, verts sur desktop et mobile |
| Infra | docker compose dev, images prod multi-stage, CI GitLab (lint, sécurité, tests PostGIS, build) | `make lint test audit build` |

Couverture pytest : 3 519 lignes analysées, 256 non couvertes (essentiellement `seed.py`, la tâche iCal réseau et les tâches Celery de rappel).

## Performance (Lighthouse mobile, image de production locale)

Mesure sur `loka-web:prod` lancé en Docker sur la machine de développement (chargée : Docker Desktop, WSL, PostgreSQL, MinIO), émulation mobile Lighthouse avec CPU ralenti ×4. Deux séries de mesures ont donné des résultats instables (performance 40 à 51 selon la charge machine), ce qui rend le chiffre local peu fiable.

| Page | Performance | Accessibilité | Bonnes pratiques | SEO |
|---|---|---|---|---|
| Accueil | 46 à 51 | 92 | 96 | 100 |
| `/location/ariana` | 44 à 49 | 96 | 96 | 100 |
| `/logement/[slug]` | 40 à 44 | 96 | 96 | 100 |

**L'objectif « performance ≥ 90 sur mobile » n'est pas atteint dans cet environnement et doit être considéré comme non vérifié.** Ce qui a été fait : images en WebP redimensionnées côté API, `next/image` avec `sizes`, MapLibre chargé à la demande hors du bundle initial (fiche : 437 kB → 165 kB, assistant hôte : 451 kB → 179 kB), pages statiques ISR, polices système. Le poste principal restant est le temps de blocage JavaScript (hydratation React + Radix sur l'en-tête, la barre de recherche et le bloc de réservation).

Pistes concrètes, dans l'ordre : mesurer sur l'hébergement cible avec PageSpeed Insights (réseau et CPU réels) ; convertir l'en-tête en composant serveur avec un seul îlot client pour le menu ; charger le bloc de réservation et la barre de recherche à l'interaction (`next/dynamic`) ; servir les images via un CDN avec `Cache-Control` long ; activer l'optimisation d'images Next en production (elle est désactivée seulement quand le stockage est `localhost`).

## Risques restants

1. **Paiement** : seul le prestataire mock existe. Konnect / ClicToPay / Flouci restent à implémenter derrière `PaymentProvider`, avec vérification de signature propre à chaque prestataire et tests de webhook rejoués.
2. **CSP front** : `script-src` accepte `'unsafe-inline'` et `'unsafe-eval'` (contrainte Next.js sans nonces). À durcir avec des nonces via middleware avant production.
3. **Tuiles cartographiques** : tuiles OSM publiques, interdites pour un usage commercial soutenu. Prévoir MapTiler / Stadia (clé, CSP à mettre à jour).
4. **Règles métier prises par défaut** (ADR 0005) : acompte 30 % en nuitée, annulation gratuite à 7 jours, prix annuel = loyer mensuel × 12. À valider avec le métier ; les constantes sont dans `settings`.
5. **Identité non obligatoire** pour publier ou réserver : la vérification existe mais n'est pas imposée par l'API (choix prudent : l'équipe tranche à la validation). Une règle d'une ligne suffit à l'imposer.
6. **Emails** : backend console en dev ; SMTP à configurer, SPF / DKIM à poser, et pas encore de préférence de désinscription.
7. **Secrets et prod** : `SECRET_KEY` ≥ 50 caractères imposée, `ALLOWED_HOSTS` strict, cookies `Secure` ; mais pas de gestion de secrets externalisée (Vault / variables CI protégées) ni de sauvegardes automatiques PostgreSQL / MinIO.
8. **Observabilité** : logs structurés en console (`loka.audit`), aucun agrégateur ni alerting (Sentry, Prometheus).
9. **Tests E2E** : dépendent d'une stack seedée et tournent en ~5 min ; pas encore intégrés au pipeline CI (job à ajouter avec services docker-in-docker).
10. **i18n** : structure prête, contenu FR uniquement ; les slugs et textes SEO ne sont pas traduits.
11. **Photos** : originaux privés et variantes WebP, mais pas de détection de doublons ni de limite de nombre par bien.
12. **Rate limiting** : par IP via Redis ; derrière un proxy, `X-Forwarded-For` doit être fiabilisé (ne pas faire confiance à l'en-tête sans `SECURE_PROXY_SSL_HEADER` et une liste de proxys de confiance).

## Recommandations avant mise en production

1. Valider les règles de l'ADR 0005 et les CGU / confidentialité avec un conseil juridique (loi 2004-63).
2. Intégrer Konnect (checkout hébergé) et rejouer les tests de webhook (`bookings/tests/test_api.py`) contre son sandbox.
3. Passer la CSP en nonces, servir MinIO / S3 en HTTPS derrière un CDN, activer `JWT_COOKIE_SECURE=1`.
4. Ajouter Sentry (API + front), sauvegardes quotidiennes PostgreSQL et MinIO, et un job CI Playwright.
5. Remplacer les tuiles OSM par un fournisseur avec clé et compléter les textes SEO des villes / quartiers.
6. Charger de vraies données de visites (photos équipe) et mesurer Lighthouse sur l'hébergement cible, pas seulement en local.
7. Décider si la vérification d'identité devient obligatoire pour publier (hôte) et pour réserver (voyageur).

## Comment reprendre

```bash
cp .env.example .env && make dev && make seed      # stack + données
make lint && make test && make audit               # portes de qualité
make e2e                                           # Playwright contre la stack
```

Documentation : `README.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/api.md`, `docs/decisions/0001-0006`, `docs/reports/phase-1..5.md`.
