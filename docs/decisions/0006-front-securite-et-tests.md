# ADR 0006 — Sécurité côté front, garde des espaces connectés, stratégie de tests E2E

Date : 2026-09-13 · Statut : accepté

## Contexte

Les espaces connectés (voyageur, hôte, équipe) sont rendus côté client. Il faut décider où vit la sécurité, comment le front se protège (CSP, tokens) et comment tester les parcours critiques de façon fiable.

## Décisions

- **La sécurité est dans l'API, pas dans le front.** `RequireRole` redirige seulement pour l'expérience utilisateur ; chaque endpoint vérifie le rôle et la propriété objet par objet (tests d'accès interdits dans l'API).
- **Access token en mémoire, refresh en cookie httpOnly** (`path=/api/v1/auth/`, `SameSite=Lax`, `Secure` en prod). Le front ne stocke jamais de jeton dans `localStorage`. Un 401 déclenche une seule tentative de rafraîchissement.
- **CSP stricte côté Next** (`next.config.ts`) : `connect-src` limité à l'origine de l'API et aux tuiles OSM, `frame-ancestors 'none'`, `img-src` limité au stockage public. `'unsafe-inline'` / `'unsafe-eval'` pour `script-src` restent nécessaires à Next.js en dev ; à durcir avec des nonces avant la mise en production (risque documenté).
- **Rate limiting par usage** : `login` 20/min, `refresh` 120/min (appelé à chaque chargement de page), `register` 5/h, `booking_request` 10/h, `lead_import` 5/h, `upload` 60/h.
- **Revalidation ISR pilotée par l'API** : un webhook `/api/revalidate` protégé par secret est appelé (Celery) à la publication, mise en pause ou changement de prix d'un bien. Le build de production ne contacte jamais l'API (`API_INTERNAL_URL=http://build.invalid`) : les pages sont générées à la demande au premier accès.
- **Tests E2E Playwright** sur trois parcours : recherche → fiche → demande, création d'un bien par un hôte, validation par l'équipe, plus les gardes de rôle. Les données de préparation passent par l'API (jetons), jamais par la base. Un marqueur `html[data-hydrated]` posé par `AuthProvider` sert de signal d'interactivité ; sur le serveur de dev, un seul worker et des délais larges compensent la compilation à la volée.

## Conséquences

- Toute nouvelle page connectée doit être ajoutée à un layout avec `RequireRole` et appuyée par des permissions API testées.
- Les tests E2E tournent contre la stack docker seedée (`make dev && make seed`), puis `make e2e`.
- Avant production : nonces CSP, `NEXT_PUBLIC_S3_PUBLIC_URL` en HTTPS, `JWT_COOKIE_SECURE=1`.
