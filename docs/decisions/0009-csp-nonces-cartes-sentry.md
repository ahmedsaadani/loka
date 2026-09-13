# ADR 0009 — CSP par nonce, fond de carte MapTiler, Sentry

Date : 2026-09-13 · Statut : accepté

## CSP sans `unsafe-inline` ni `unsafe-eval`

- `apps/web/middleware.ts` génère un nonce par requête HTML, le place dans l'en-tête de requête
  `x-nonce` et dans `Content-Security-Policy` (requête et réponse). Next.js applique ce nonce à
  ses propres balises `<script>` et `<style>` ; `'strict-dynamic'` autorise les scripts chargés par
  un script noncé (chunks Next, MapLibre chargé dynamiquement).
- Production : `script-src 'self' 'nonce-…' 'strict-dynamic'`, `object-src 'none'`, `base-uri 'self'`,
  `form-action 'self'`, `upgrade-insecure-requests`. Aucun `'unsafe-inline'` ni `'unsafe-eval'` pour
  les scripts.
- Développement : `'unsafe-eval'` ajouté à `script-src` (source maps, Fast Refresh). Jamais en
  production.
- **Exception assumée : `style-src 'self' 'unsafe-inline'`.** `next/image` rend `style="color:transparent"`
  sur chaque image et Radix émet des attributs `style` côté serveur ; ces attributs ne peuvent pas
  recevoir de nonce. Autoriser les styles inline n'ouvre aucune exécution de script (le risque CSS
  résiduel est l'exfiltration par sélecteurs, sans impact ici : pas de secret dans le DOM).
- Conséquence Next.js : un nonce exige un rendu à la demande. `dynamic = "force-dynamic"` est posé
  sur le layout racine (toute page pré-rendue statiquement, y compris les espaces connectés, aurait
  des scripts sans nonce donc bloqués) ; les appels API
  gardent leur cache (`next: { revalidate }`) et le webhook de revalidation continue de le purger.
  Le pré-rendu statique (ISR) est abandonné au profit de la CSP stricte ; le rendu serveur d'une
  page coûte quelques dizaines de millisecondes avec les données en cache.
- La CSP a été retirée de `next.config.ts` (un en-tête statique ne peut pas porter de nonce).
- Vérification : build de production, navigation accueil / recherche (carte + filtres shadcn) /
  fiche (galerie, dialogues, calendrier) sans violation CSP de script dans la console.

## Fond de carte

- Production : MapTiler (`NEXT_PUBLIC_MAPTILER_KEY`, style `streets-v2`), quotas et conditions
  compatibles avec un usage commercial ; hôtes autorisés dans `img-src` et `connect-src`.
- Développement sans clé : tuiles raster OpenStreetMap (usage public limité par la politique
  OSM, jamais en production). En production sans clé, la carte affiche un message et rien n'est
  chargé : la clé fait partie de la checklist de mise en production.

## Sentry

- API : `sentry-sdk[django,celery]`, initialisé dans `settings/base.py` seulement si
  `SENTRY_DSN` est défini ; `environment` = `SENTRY_ENVIRONMENT`, `release` = `SENTRY_RELEASE`
  (posé par `deploy.sh` avec le tag d'image) ; `send_default_pii=False`.
- Front : `@sentry/nextjs` via `instrumentation.ts` (serveur/edge) et `instrumentation-client.ts`
  (navigateur), actifs seulement si `NEXT_PUBLIC_SENTRY_DSN` est défini ; replays désactivés.
- Les avertissements de contenu provisoire (`[À RÉDIGER]`) sont remontés à Sentry au démarrage
  en production (`core.checks.warn_if_placeholders_remain`).
