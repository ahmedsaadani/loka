# ADR 0011 — Dernière passe avant déploiement

Date : 2026-09-14 · Statut : accepté

Six décisions structurantes prises lors de la passe finale (rapport `docs/reports/phase-8.md`).

## 1. Regroupement des marqueurs de la carte

- Regroupement fait par la source GeoJSON de MapLibre (`cluster: true`, rayon 48 px, jusqu'au
  zoom 15) : aucune dépendance supplémentaire, calcul côté navigateur.
- Les groupes et les biens sont rendus en **marqueurs DOM** (pas en couche symbole) : le fond
  OSM de développement n'a pas de glyphes, et les étiquettes restent stylées comme le reste
  de l'interface. Une couche `circle` invisible ancre la source pour que MapLibre la charge.
- Étiquette de prix visible à partir du zoom 13, simple point en dessous ; clic sur un
  groupe = zoom d'éclatement (`getClusterExpansionZoom`). La synchronisation liste ↔ carte
  est inchangée : bbox émise à chaque `moveend` (donc aussi après un clic sur un groupe),
  survol d'une carte = marqueur actif, clic sur un marqueur = défilement vers la carte.

## 2. Purge du cache du front

- `REVALIDATE_URL` est défini par défaut dans le compose de dev vers
  `host.docker.internal:3000` (front lancé nativement, cas documenté sur Windows) avec le
  mapping `host-gateway` ; `.env.example` documente l'alternative `http://web:3000`.
- Le seed, la publication d'un bien et l'écran « Contenus à rédiger » passent par la même
  tâche `notifications.tasks.revalidate_front` ; en test, `REVALIDATE_URL` est vide (no-op).

## 3. Contenus à rédiger

- Un texte contenant `[À RÉDIGER]` **n'est jamais servi** par l'API publique : les
  sérialiseurs de ville / quartier et la vue `SiteContent` renvoient une chaîne vide, le
  front masque la section (pages légales : courte notice « en cours de rédaction »).
  Décision prise côté API plutôt que côté front pour que tout client (sitemap, futur mobile)
  bénéficie du masquage.
- L'écran admin est une vue Django classique (`/admin/contenus-a-rediger/`) protégée par
  `staff_member_required`, avec aperçu rendu **côté serveur** par `core/markdown.py`, miroir
  volontairement strict du composant `Markdown.tsx` du front (mêmes règles, texte échappé,
  liens `https:`/`mailto:` seulement). Pas de bibliothèque Markdown ajoutée : parité de
  rendu garantie par test.
- Les intros de ville et de quartier sont désormais rendues en Markdown sur le site.

## 4. Retouche automatique des photos

- Appliquée **en mémoire** à la génération des variantes WebP (worker Celery) ; l'original
  du bucket privé n'est jamais réécrit (test dédié).
- Ordre : orientation EXIF → balance des blancs « gray world » atténuée (50 %, gain borné
  à ±12 %) → auto-niveaux sur la luminance (percentiles 0,5 %, pente plafonnée à 1,5, même
  courbe pour les trois canaux donc sans dérive de teinte) → contraste 1,06 → netteté 1,08.
  Réglages doux : l'objectif est de corriger une photo de téléphone terne ou jaunâtre, pas de
  la transformer.
- `PropertyPhoto.auto_enhance` (défaut vrai) désactive la retouche photo par photo depuis
  l'admin ; changer la valeur régénère les variantes, et une action régénère toutes les
  variantes d'un bien.

## 5. Recrutement des propriétaires

- Point d'entrée public `POST /leads/owner-contact/` : `AllowAny`, throttle dédié
  `owner_contact` (5/h par IP), champ piège `website` (réponse 201 mais rien n'est créé :
  un robot ne doit pas savoir qu'il est détecté). Pas de CAPTCHA à ce stade.
- Crée un `Lead` source `manual` (titre « Type à Ville — Nom », téléphone, ville, message
  dans `notes` et `raw_data`) : l'équipe le traite dans le back-office existant, sans
  nouveau modèle.
- Notification : un email par compte `staff` / `admin` actif (première notification
  « équipe » du projet, helper `staff_recipients`).
- Pages `/devenir-hote` (pitch + formulaire) et `/comment-ca-marche` ; « Proposer un bien »
  pointe désormais vers `/devenir-hote`, la création de compte propriétaire reste accessible
  depuis cette page et le pied de page.

## 6. Conformité déploiement

- `manage.py check --deploy` avec les réglages de production ne remonte plus aucun
  avertissement : schéma OpenAPI nettoyé (querysets factices pour la génération, typage des
  champs `{lat, lng}`, noms d'énumérations, identifiants d'opération).
- Les variables `NEXT_PUBLIC_*` (API, site, bucket public, MapTiler, Sentry) sont figées au
  build de l'image web : Dockerfile, CI et `docs/deploy.md` alignés. Sans
  `NEXT_PUBLIC_MAPTILER_KEY` au build, la carte serait indisponible en production.
