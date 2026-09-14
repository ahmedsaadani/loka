# Rapport Phase 8 — Dernière passe avant déploiement

Date : 2026-09-14 · Décision associée : ADR 0011 · Un commit par point.

## 1. Les six points

| # | Point | État | Commit |
|---|---|---|---|
| 1 | Regroupement des marqueurs sur la carte de recherche | fait, vérifié dans le navigateur et par Playwright (desktop) | `feat(web): cluster search map markers` |
| 2 | `REVALIDATE_URL` en dev + purge après `seed --reset` | fait, vérifié (le worker journalise `revalidate_front … succeeded: True`) | `chore(dev): purge the Next cache automatically after seed` |
| 3 | Écran admin « Contenus à rédiger », masquage public | fait, 12 tests (rendu Markdown, inventaire, écran, aperçu, masquage API) | `feat(admin): « Contenus à rédiger » screen and public masking of placeholders` |
| 4 | Retouche automatique des photos de l'équipe | fait, 6 tests (invariants de retouche, respect du drapeau, original intact) | `feat(api): automatic retouch of team photos in the WebP pipeline` |
| 5 | Pages « Comment ça marche » et « Devenir hôte », lead + email staff | fait, 10 tests API + 3 scénarios Playwright | `feat: « Comment ça marche » and « Devenir hôte » pages with owner contact form` |
| 6 | `check --deploy` sans avertissement, `docs/deploy.md` à jour | fait (22 avertissements → 0) ; Dockerfile web, CI, `.env.prod.example`, doc alignés | `fix(api): clean OpenAPI schema…` + `docs(deploy): …` |

## 2. Détails utiles

**Carte.** Groupes avec compteur (taille selon l'effectif), clic = zoom d'éclatement, étiquette de
prix à partir du zoom 13 (point simple en dessous). Sur Ariana avec les données de démo : trois
groupes (5, 2, 2) au cadrage initial. La liste suit la carte comme avant (bbox à chaque
déplacement, y compris après un clic sur un groupe).

**Contenus.** `/admin/contenus-a-rediger/` liste chaque champ encore marqué (pages légales,
villes, quartiers ; intro, titre et description SEO), éditeur + aperçu identique au rendu du
site, enregistrement = publication + purge du cache. Côté public, un texte marqué n'est plus
jamais affiché : intro de ville/quartier absente, page légale réduite à une notice. L'index de
l'admin affiche le nombre de contenus restants.

**Photos.** La retouche ne touche que les variantes WebP ; l'original privé est intact (test).
Réglages doux et bornés (balance des blancs ±12 % max, étirement des niveaux ≤ ×1,5). Pour
appliquer aux photos déjà en ligne : action admin « Régénérer les variantes WebP ».

**Propriétaires.** Formulaire nom / téléphone / ville / type de bien / message, throttle 5 par
heure et par IP, champ piège. Chaque envoi crée un lead `manual` visible dans le back-office
(`/admin/leads`) et envoie un email à chaque membre staff/admin actif. Titre du lead :
« Appartement à Ariana — Nom ».

**Déploiement.** `check --deploy` : 0 avertissement avec `config.settings.prod`. Écart
corrigé au passage : seule `NEXT_PUBLIC_API_URL` était passée au build de l'image web, donc
`NEXT_PUBLIC_MAPTILER_KEY` et `NEXT_PUBLIC_S3_PUBLIC_URL` auraient manqué en production
(carte indisponible, hôte des photos non autorisé par `next/image`). Le Dockerfile, le job
`build:web`, `.env.prod.example` et `docs/deploy.md` (variables CI, checklist, notes de
migration Phase 8, commandes avec `--env-file`) sont alignés.

## 3. Vérifications

| Vérification | Résultat |
|---|---|
| ruff, ruff format, mypy strict, bandit (API) | 0 erreur |
| pytest API (suite complète) | 431 tests verts (403 avant cette passe) |
| `manage.py check --deploy` (réglages prod) | 0 issue |
| tsc, eslint, prettier, vitest (web, contrat OpenAPI régénéré) | 0 erreur, 16 tests verts |
| Playwright `marketing.spec.ts` (dev server, desktop + mobile) | 5 verts, 1 ignoré (carte sur mobile) |
| Contrôle navigateur | groupes visibles sur `/recherche?city=ariana`, formulaire `/devenir-hote` |

## 4. Actions humaines

- Renseigner les variables CI `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_S3_PUBLIC_URL`, `NEXT_PUBLIC_MAPTILER_KEY` (et `NEXT_PUBLIC_SENTRY_DSN`) avant le prochain `build:web`.
- Rédiger les contenus dans l'écran admin (13 quartiers, 4 villes, 3 pages) ; tant que ce n'est pas fait, les sections restent masquées.
- Créer les comptes `staff` de l'équipe : ce sont eux qui reçoivent les emails « nouveau propriétaire ».
- Décider si un CAPTCHA est souhaité sur le formulaire propriétaire après observation du volume de spam (throttle + champ piège en place).
