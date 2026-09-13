# Rapport Phase 2 — Public et SEO

Commit : `2d04b7e` (avec le socle front).

## Fait

- Accueil : barre de recherche (ville, dates, voyageurs, mode Nuit / Mois / Année), villes populaires avec compteurs et prix moyens, derniers biens vérifiés, « Comment ça marche », appel aux propriétaires.
- `/location/[ville]` et `/location/[ville]/[quartier]` : ISR (`revalidate` 600 s), H1 optimisé, texte d'intro, grille de biens, prix moyens calculés par l'API, FAQ générée, liens internes (quartiers, villes voisines), JSON-LD BreadcrumbList + FAQPage.
- `/logement/[slug]` : galerie (mosaïque desktop, carrousel mobile, plein écran), badge « Vérifié par Loka » daté, grade d'état, tarifs par mode avec équivalent EUR, calendrier de disponibilités, équipements, infos pratiques (charges, caution, durée minimale, distances, règles), carte approximative (cercle 100 m) ou exacte, bloc de réservation sticky sur mobile, JSON-LD Accommodation + Offer, métadonnées Open Graph.
- `/recherche` : liste + carte MapLibre synchronisées (survol, clic marqueur, recadrage), filtres (mode, prix, type, chambres, voyageurs, meublé, quartier, équipements, dates), tri, pagination, URL partageable, `noindex`.
- `sitemap.xml` dynamique, `robots.txt`, canonical, pages CGU / confidentialité / contact, 404 et 500 propres.
- Revalidation ISR pilotée par l'API à la publication / pause / changement de prix (webhook signé).

## Tester

- `make dev && make seed`, puis ouvrir http://localhost:3000/location/ariana et une fiche.
- `curl -s http://localhost:3000/sitemap.xml | head`.
- Image de production : `docker build -f infra/docker/web.Dockerfile --target prod apps/web` (le build ne dépend pas de l'API).

## Reste / questions ouvertes

- Lighthouse : mesuré sur l'image de production locale (voir rapport global) ; les polices restent système (pas de téléchargement Google Fonts) pour préserver la performance et la disponibilité hors ligne au build.
- Tuiles OpenStreetMap publiques : à remplacer par un fournisseur avec clé (MapTiler, Stadia) avant un trafic réel, conformément à la politique d'usage OSM.
- Textes SEO des villes et quartiers : les valeurs du seed sont des exemples ; à rédiger par l'équipe dans l'admin Django.
