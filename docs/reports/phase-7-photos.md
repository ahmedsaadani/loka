# Rapport Phase 7 — Photos réelles et catalogue de démonstration

Date : 2026-09-14 · Décision associée : ADR 0010

## 1. Ce qui a été livré

| Élément | Détail |
|---|---|
| Banque de photos | `apps/api/seed/photos/` : 110 photos Unsplash (licence Unsplash), 10 catégories (salon 15, chambre 7, cuisine 11, salle de bain 13, balcon/vue 9, façade 11, villa piscine 10, villa extérieur 8, studio 14, chambre étudiante 12). Fichiers JPEG ré-encodés, grand côté ≤ 1600 px, non versionnés (≈ 30 Mo). |
| Script | `scripts/fetch_seed_photos.py` : sans clé, télécharge la liste vérifiée `sources.json` depuis le CDN Unsplash (HTTP 200 + décodage Pillow + ré-encodage) ; avec `UNSPLASH_ACCESS_KEY` ou `PEXELS_API_KEY`, passe par les API officielles. Idempotent, `--check` pour vérifier la banque hors ligne. Génère `manifest.json` et `CREDITS.md`. |
| Crédits | `apps/api/seed/photos/CREDITS.md` : auteur, lien de la page, licence pour chaque photo, avec avertissement « démo uniquement, jamais pour une annonce réelle ». |
| Catalogue | `apps/api/core/seed_catalog.py` : 33 biens rédigés à la main : 25 appartements et studios (Ariana, Tunis, Sousse), 5 villas (Hammamet Nord, Yasmine Hammamet, Hammamet Centre, Kantaoui, La Marsa), 3 chambres en colocation à Ghazela près d'ESPRIT. Titres et descriptions en français, prix 2026 en DT, équipements variés (21 codes), distances réalistes, états répartis (simple 7 / bon état 15 / excellent 11), niveaux « Vérifié » et « Sélection Loka ». |
| Seed | `manage.py seed` réécrit : ville de Hammamet (gouvernorat Nabeul, 3 quartiers), plans de photos par type (5 à 8 photos, couverture = séjour ou extérieur, studio sans piscine, villa avec façade + extérieur + piscine), `alt_text` français, `taken_by_team=True`, pipeline réel (`services.add_photo` → original privé → variantes WebP par le worker Celery, attente `--wait-variants`), `--reset`, `make seed-reset`. Prix annuel désormais un vrai prix annuel (ADR 0007), l'ancien seed le calculait comme un loyer mensuel. |
| Captures | `docs/screenshots/` : accueil, page ville Ariana, fiche appartement, fiche villa, recherche avec carte, en desktop (1440 px) et mobile (iPhone 13), générées par `node apps/web/scripts/screenshots.mjs`. |

## 2. Sélection des photos

Sans clé API (Unsplash et Pexels bloquent le scraping direct), les identifiants ont été relevés
depuis les pages de recherche publiques Unsplash (requêtes : salon méditerranéen, chambre
lumineuse, cuisine moderne, salle de bain, balcon vue mer, immeuble blanc, villa piscine, villa
extérieur, studio, chambre étudiante), puis chaque photo a été contrôlée sur planche-contact.
27 photos écartées : gros plans de literie, scènes de nuit, personnes visibles, immeubles orange
ou enseignes, manoirs non méditerranéens, lit à baldaquin. Aucune neige, aucun gratte-ciel.

Limite connue : 7 photos de chambre seulement, donc des chambres se répètent entre appartements
(jamais au sein d'un même bien). Ajouter des photos = ajouter des entrées dans `sources.json`
puis relancer le script.

## 3. Contrôle visuel (captures)

Problèmes détectés et corrigés :

- **Recherche mobile** : la barre d'outils (modes + tri + filtres) débordait de 78 px à droite ; passage en `flex-wrap` et tri à 150 px.
- **Cartes de bien** : le badge d'état (« Bon état ») se coupait sur deux lignes sous un prix long (3 tarifs) ; badge en `whitespace-nowrap shrink-0`.
- **Accueil** : avec 4 villes, la grille 3 colonnes laissait Hammamet seule sur une ligne ; grille à 4 colonnes en large écran.

Observations restantes, sans correction dans cette phase :

- Sur la carte de recherche, les étiquettes de prix se chevauchent quand plusieurs biens sont dans le même quartier (pas de regroupement de marqueurs). Un clustering MapLibre serait la suite logique.
- Les textes `[À RÉDIGER]` des villes et quartiers restent visibles sur les pages publiques (contenu à saisir dans l'admin, Phase 6).
- Les photos étant toutes en paysage, la mosaïque desktop de la galerie (1 grande + 4 petites) et les cartes 4:3 recadrent légèrement en hauteur : aucune coupe gênante constatée.

## 4. Vérifications

| Vérification | Résultat |
|---|---|
| Seed réel sur la stack Docker (`seed --reset`) | 33 biens, 216 photos passées par `add_photo` (original privé MinIO), 216 × 4 variantes WebP générées par le worker Celery, 38 instantanés reconstruits |
| ruff, ruff format, mypy strict, bandit (API) | 0 erreur |
| pytest API | 403 tests verts (suite complète) |
| tsc, eslint, prettier, vitest (web) | 0 erreur, 16 tests verts |
| Captures Playwright | 10 captures, aucun débordement horizontal après corrections |

## 5. Actions humaines

- Sur un nouveau poste : `python scripts/fetch_seed_photos.py` avant `make seed` (banque non versionnée).
- Définir `REVALIDATE_URL` côté API en dev (`http://host.docker.internal:3000/api/revalidate`) pour que le seed purge le cache du front ; sinon, redémarrer `npm run dev` après un `seed --reset`.
- Le jour où une clé Unsplash ou Pexels est disponible, relancer le script avec la clé : métadonnées rafraîchies et déclaration des téléchargements conformes aux conditions des API.
- Ne jamais réutiliser ces photos pour une annonce réelle (CREDITS.md).
