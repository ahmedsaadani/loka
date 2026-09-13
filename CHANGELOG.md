# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versionnage sémantique.

## [Unreleased]

### Phase 6 — Corrections métier, industrialisation, production

- ADR 0007 : prix annuel propre (`monthly_equivalent` indicatif), acomptes par mode, annulation 7 / 30 jours, modification d'un bien publié avec instantané public pendant la revue, identité vérifiée obligatoire pour publier, email « modifications en cours de vérification ».
- Instantané public `Property.published_snapshot`, commande `rebuild_snapshots`, contenus éditoriaux `SiteContent` (CGU, confidentialité, contact) gérés dans l'admin et servis via `/content/{key}/`, vérification système des textes `[À RÉDIGER]` (`manage.py check --deploy`, alerte Sentry au démarrage en prod).
- CSP par nonce (middleware Next), fond de carte MapTiler avec repli OSM en dev, Sentry API et front (désactivés sans DSN), carte de la fiche chargée à l'affichage, `scripts/lighthouse.sh`.
- Sauvegardes PostgreSQL chiffrées (Fernet) vers le bucket privé, rotation 7 jours / 4 semaines, tâche beat quotidienne, commandes `backup_db` / `restore_db` / `list_backups`, procédure documentée (`docs/backups.md`).
- Prestataire de paiement Konnect (`PAYMENT_PROVIDER=konnect`, sandbox, webhook vérifié par relecture de l'API, réconciliation `check_payment`), remboursements manuels tracés.
- Job CI Playwright desktop + mobile avec vidéos en cas d'échec ; `infra/deploy/` (compose prod, Nginx HTTPS Let's Encrypt, `deploy.sh` idempotent avec rollback, job `deploy:prod`) et `docs/deploy.md` (SMTP, SPF/DKIM/DMARC, checklist).

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
- Front Next.js 15 : design system (tokens, shadcn), client API typé avec contrat vérifié contre le schéma OpenAPI, page d'accueil.

### Phase 2 — Public et SEO

- Pages `/location/[ville]`, `/location/[ville]/[quartier]` (ISR, FAQ, JSON-LD, liens internes), fiche `/logement/[slug]` (galerie, tarifs par mode, calendrier, carte approximative, bloc réservation sticky, JSON-LD Accommodation/Offer), recherche `/recherche` (filtres, carte synchronisée, URL partageable, noindex), sitemap, robots, pages légales, 404/500.
- Revalidation ISR déclenchée par l'API (publication, pause, prix) via `/api/revalidate` signé.
- API : réinitialisation et changement de mot de passe, statistiques staff, mise à jour des dépendances (Django 5.2, DRF 3.17, Pillow 12, WeasyPrint 70).

### Phase 3 — Espace propriétaire

- Inscription hôte, tableau de bord, liste des biens, assistant en 6 étapes avec sauvegarde à chaque étape (infos, localisation sur carte, photos drag & drop et réordonnancement, tarifs par mode, calendrier et iCal, soumission avec liste de complétude), demandes (accepter / refuser), réservations (annulation, contrat PDF).

### Phase 4 — Réservation et paiement

- Devis instantané et demande depuis la fiche, espace voyageur (demandes, réservations, paiement de l'acompte via page mock signée HMAC, adresse exacte révélée après confirmation, identité), emails transactionnels, contrat PDF pour les modes mensuel et annuel.

### Phase 5 — Back-office équipe

- Tableau de bord, file de validation, revue d'un bien (adresse exacte journalisée, photos équipe, visite, publication, rejet), demandes et réservations, vérification des identités (URL signées), leads (import CSV/JSON, workflow, conversion).
- Tests Playwright : recherche → fiche → demande, création d'un bien, validation par l'équipe, gardes de rôle.
- ADR 0006 (sécurité front et stratégie E2E), rapports de phase dans `docs/reports/`.
