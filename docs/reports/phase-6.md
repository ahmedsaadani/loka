# Rapport Phase 6 — Corrections métier, industrialisation, production

Date : 2026-09-13

## 1. Résultats des tests

| Vérification | Résultat |
|---|---|
| pytest API | 403 tests verts (313 en Phase 5 → +90 : règles v2, instantané, identité, annulation par mode, sauvegardes, Konnect, stats) |
| ruff, mypy strict, bandit, pip-audit | 0 erreur, 0 finding, 0 vulnérabilité |
| tsc strict, eslint, prettier | 0 erreur |
| vitest | 16 tests verts (contrat OpenAPI régénéré et vérifié) |
| Playwright desktop + mobile | 10 / 10 verts sur le build de production avec la CSP par nonce (2 min 18 s) |
| Build web de production | OK (`next build`, 185 kB de JS partagé au premier chargement) |
| Vérification CSP navigateur | build de production : scripts tous noncés (51/53, les 2 restants sont les blocs JSON-LD non exécutables), carte MapLibre rendue (canvas + 14 marqueurs), formulaires shadcn fonctionnels |
| Sauvegarde / restauration | testée de bout en bout : dump chiffré → bucket privé → restauration dans une base de secours → comptage identique à la source |

## 2. Ce qui change par rapport à l'ADR 0005 (voir ADR 0007)

| Sujet | ADR 0005 | Phase 6 |
|---|---|---|
| Prix annuel | loyer mensuel × 12 | prix annuel saisi par l'hôte ; « soit X DT/mois » affiché partout (fiche, carte, devis, éditeur) |
| Acompte | 30 % nuitée, 1 mois sinon | identique, l'annuel = un douzième du prix annuel |
| Annulation voyageur | 7 jours tous modes | 7 jours (nuitée), 30 jours (mensuel, annuel) ; hôte et staff remboursent toujours, avec audit `booking_cancelled_by_host` |
| Modification d'un bien publié | interdite | autorisée : prix, calendrier, iCal, règles et conditions immédiats ; photos, titre, description, type, adresse, équipements → `pending_review` avec l'ancienne version toujours visible et réservable (`published_snapshot`) ; email à l'hôte |
| Identité | facultative | obligatoire pour soumettre un bien (code `identity_required` côté hôte, message clair dans l'assistant) ; facultative pour réserver |
| Remboursement sans API prestataire | — | ligne `refund` en `initiated` + audit, annulation jamais bloquée (Konnect) |

## 3. Industrialisation

- **CI Playwright** : job `e2e:playwright` (stage `e2e`) avec PostGIS, Redis, MinIO et l'image API du commit en services, desktop + mobile, vidéos et rapport en artefacts en cas d'échec.
- **Sentry** : API (`sentry-sdk`, Django + Celery) et front (`@sentry/nextjs`), activés seulement si un DSN est défini, avec `environment` et `release` (tag d'image posé par `deploy.sh`).
- **Sauvegardes** : `pg_dump` chiffré Fernet vers le bucket privé, rotation 7 jours / 4 semaines, tâche beat 03:00, commandes `backup_db`, `list_backups`, `restore_db --yes` (garde `ALLOW_DB_RESTORE=1`), procédure dans `docs/backups.md`.
- **Emails** : backend SMTP configurable, templates finalisés (dont « modifications en cours de vérification »), SPF/DKIM/DMARC dans `docs/deploy.md`.
- **CSP** : nonce par requête (`middleware.ts`), `script-src` sans `unsafe-inline` ni `unsafe-eval` en production. Exception assumée et documentée : `style-src 'unsafe-inline'` (attributs `style` rendus par `next/image` et Radix). Conséquence : les pages publiques passent en rendu à la demande (le nonce exige un rendu dynamique), les données API restent en cache.
- **Cartes** : MapTiler via `NEXT_PUBLIC_MAPTILER_KEY` ; OSM seulement en dev (ou `NEXT_PUBLIC_MAP_FALLBACK_OSM=1` pour un build local de test).

## 4. Déploiement production

`infra/deploy/` : `docker-compose.prod.yml` (nginx seul exposé, certbot, api, worker, beat, web, postgres, redis, minio optionnel, healthchecks, redémarrage automatique, logs limités), Nginx HTTPS Let's Encrypt avec en-têtes, gzip, cache des assets, rate limiting sur l'auth, `init-letsencrypt.sh`, `deploy.sh` idempotent (pull, migrations, collectstatic, up, santé, revalidation ISR, rollback automatique), job `deploy:prod` GitLab. Procédure complète dans `docs/deploy.md` (résumé en section 6).

## 5. Paiement, performance, contenu

- **Konnect** : `KonnectPaymentProvider` (init-payment en millimes, redirection, webhook vérifié par relecture `GET /payments/{ref}` et jeton secret d'URL, réconciliation `check_payment`), sandbox, fixtures enregistrées, `docs/payments.md`, ADR 0008. Remboursement : pas d'API publique documentée → manuel, tracé. TODO explicites listés dans la doc.
- **Performance** : carte de la fiche montée à l'entrée dans le viewport (ou au clic), MapLibre hors bundle initial, `scripts/lighthouse.sh` (accueil, ville, fiche, mobile, seuil 85, hors CI). Aucune police web chargée (pile système), donc pas de `font-display` à gérer.
- **Contenu** : textes des villes, quartiers, CGU, confidentialité et contact remplacés par des placeholders `[À RÉDIGER]` gérés dans l'admin (`SiteContent`), `manage.py check --deploy` et alerte Sentry au démarrage en production tant qu'il en reste.

## 6. Déployer sur un VPS neuf (résumé de `docs/deploy.md`)

1. VPS Ubuntu 22.04/24.04, 2 vCPU / 4 Go, Docker Engine + plugin compose, utilisateur `deploy` dans le groupe docker, `ufw` 22/80/443, DNS A/AAAA de `DOMAIN` vers le serveur.
2. `mkdir -p /opt/loka && cp -r infra/deploy/* /opt/loka/ && cd /opt/loka && cp .env.prod.example .env.prod` puis remplir les secrets (`openssl rand -hex 32` pour `DJANGO_SECRET_KEY`, `REVALIDATE_SECRET`, `KONNECT_WEBHOOK_TOKEN` ; clé Fernet pour `BACKUP_ENCRYPTION_KEY`).
3. `./init-letsencrypt.sh` (option `--staging` pour tester) : nginx en mode bootstrap, certificat, bascule HTTPS.
4. Connexion au registre GitLab (`REGISTRY_USER` / `REGISTRY_PASSWORD` ou `docker login`), puis `./deploy.sh --tag <sha>` : pull, migrations, collectstatic, démarrage, contrôle de santé, revalidation.
5. Première mise en service : `docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser`, chargement des villes et quartiers (admin ou commande de seed géographique), `rebuild_snapshots`, `check --deploy`, rédaction des contenus `[À RÉDIGER]`.
6. Mises à jour : pipeline GitLab → job manuel `deploy:prod` (variables `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`) ou `./deploy.sh --tag` ; retour arrière : `./deploy.sh --rollback`.
7. Sauvegardes : automatiques chaque nuit ; restauration selon `docs/backups.md`.

## 7. Playwright

Exécution locale sur le build de production (port dédié 3002, CSP nonce active, MapTiler remplacé par OSM via l'opt-in de test) : **10 / 10 tests verts** (recherche → fiche → demande, création d'un bien par un hôte, validation par l'équipe, contrôles d'accès), desktop et mobile. Première tentative en échec : les pages des espaces connectés étaient pré-rendues statiquement, donc sans nonce ; corrigé en rendant toute l'application dynamique depuis le layout racine (ADR 0009).

## 8. Actions humaines requises

| Action | Où |
|---|---|
| Créer le compte Konnect, obtenir `KONNECT_API_KEY` et `KONNECT_WALLET_ID`, déclarer l'URL de webhook, passer `KONNECT_SANDBOX=0` après tests | `.env.prod`, `docs/payments.md` |
| Confirmer avec le support Konnect : signature de webhook, API de remboursement | TODO dans `bookings/payments/konnect.py` |
| Clé MapTiler (`NEXT_PUBLIC_MAPTILER_KEY`), compte gratuit ou payant selon le trafic | `.env.prod` |
| DSN Sentry API et front | `.env.prod` |
| DNS : A/AAAA du domaine, SPF / DKIM / DMARC du fournisseur SMTP, boîte `dmarc@` | `docs/deploy.md` |
| Fournisseur SMTP (Brevo, Mailgun, SES) et `DEFAULT_FROM_EMAIL` | `.env.prod` |
| Rédiger et faire valider CGU, confidentialité, contact ; textes SEO des villes et quartiers | admin Django (Socle > Contenus du site, Géographie) |
| Générer et conserver hors serveur `BACKUP_ENCRYPTION_KEY` ; tester une restauration après le premier déploiement | `docs/backups.md` |
| Compte registre GitLab pour le VPS, clé SSH de déploiement | variables CI |
| Valider les montants métier (acompte 30 %, délais 7 / 30 jours) avant ouverture | ADR 0007 |
