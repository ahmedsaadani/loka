# ADR 0001 — Next.js App Router avec rendu serveur pour toutes les pages publiques

Date : 2026-09-12 · Statut : accepté

## Contexte

Le SEO est une contrainte non négociable : les pages ville, quartier et fiche bien doivent être indexables et rapides sur mobile (Lighthouse ≥ 90). Une SPA classique rendue côté client ne répond pas à cette exigence.

## Décision

- Next.js 15, App Router, React Server Components.
- Pages `/location/[city]`, `/location/[city]/[neighborhood]`, `/logement/[slug]` en **SSG avec revalidation** (ISR). La revalidation est déclenchée à la demande par l'API (webhook `revalidatePath`) lors d'une publication ou d'un changement de prix.
- Page `/recherche` en SSR avec `noindex` : trop de combinaisons de filtres pour être indexée utilement.
- Les espaces connectés (`(account)`, `(host)`, `(admin)`) sont rendus côté client après authentification, avec `noindex`.
- Les images passent par `next/image` avec des variantes WebP déjà générées par l'API (pas d'optimisation à la volée coûteuse en prod).

## Conséquences

- Le front doit pouvoir appeler l'API côté serveur (`API_INTERNAL_URL`) et côté client (`NEXT_PUBLIC_API_URL`).
- Le sitemap et robots.txt sont générés par Next.js à partir de l'API.
- L'i18n s'appuiera sur des segments de route (`/ar/...`, `/en/...`) sans changement d'architecture.
