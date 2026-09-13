# ADR 0010 — Photos de démonstration libres de droits

Date : 2026-09-14 · Statut : accepté

## Contexte

Les biens de démonstration étaient illustrés par des aplats de couleur générés par Pillow. Pour
des démonstrations crédibles, il faut de vraies photos d'intérieurs et d'extérieurs
méditerranéens, sans risque juridique, et qui empruntent le pipeline réel (bucket privé,
variantes WebP via Celery) plutôt qu'un raccourci.

## Décision

- **Sources autorisées : Unsplash et Pexels uniquement** (licences autorisant l'usage
  commercial et la modification sans attribution obligatoire). Aucune autre source.
- **Banque locale non versionnée** : `apps/api/seed/photos/*.jpg` (~110 photos, ~30 Mo) est
  ignorée par git et par le contexte Docker (`apps/api/.dockerignore`). Elle est constituée une
  fois par `scripts/fetch_seed_photos.py`. Sont versionnés : `sources.json` (liste vérifiée),
  `manifest.json` (fichiers, auteurs, dimensions) et `CREDITS.md` (attribution et
  avertissement).
- **Sans clé API** (cas au moment de la décision), le script télécharge une liste d'identifiants
  Unsplash relevés à la main depuis les pages de recherche publiques, via le CDN
  `images.unsplash.com`, avec vérification HTTP 200 + décodage Pillow + ré-encodage JPEG.
  Chaque photo a été vérifiée visuellement (27 écartées : gros plans, scènes sombres,
  personnes visibles, architecture non méditerranéenne). Si `UNSPLASH_ACCESS_KEY` ou
  `PEXELS_API_KEY` sont définis, le script passe par les API officielles (métadonnées
  rafraîchies, déclaration `download_location` exigée par Unsplash, recherche Pexels).
- **Catalogue explicite** (`core/seed_catalog.py`) : 33 biens rédigés à la main (titres,
  descriptions, prix 2026, équipements, distances, état) plutôt que générés par combinaison
  aléatoire ; chaque bien reçoit 5 à 8 photos selon un plan par type (couverture = séjour ou
  extérieur, jamais de piscine pour un studio, façade + extérieur pour une villa), avec
  `alt_text` français et `taken_by_team=True`.
- **Pipeline réel** : le seed appelle `listings.services.add_photo` (validation, original
  privé, `enqueue(generate_photo_variants)`), attend le worker Celery (`--wait-variants`) puis
  reconstruit les instantanés publics. `--reset` supprime les biens de démo et leurs fichiers ;
  un bien de démo référencé par des réservations est retiré (brouillon, tag `[seed-retired]`)
  au lieu d'être supprimé.

## Conséquences

- Les photos de démo **ne doivent jamais** illustrer une annonce réelle ni être présentées
  comme prises par l'équipe : avertissement en tête de `CREDITS.md`, tag `[seed]` interne, et la
  checklist de mise en production impose l'absence des données de démo.
- Le job CI Playwright continue d'utiliser `seed --no-photos` (image sans banque).
- Un nouveau clone doit lancer le script de téléchargement avant `make seed` ; le seed échoue
  avec un message explicite si la banque manque.
- `docs/screenshots/` contient les captures de contrôle (desktop + mobile) générées par
  `apps/web/scripts/screenshots.mjs`, à régénérer après un changement visuel.
