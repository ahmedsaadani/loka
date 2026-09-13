# Rapport Phase 5 — Back-office équipe

Commit : `2e1ae73`.

## Fait

- Tableau de bord (`/admin`) : biens publiés, en attente, demandes du mois, taux d'acceptation, réservations confirmées, identités en attente, nouveaux leads, hôtes / voyageurs (`GET /staff/stats/`).
- File de validation par statut, revue d'un bien : adresse exacte (accès journalisé), complétude, photos de l'équipe (`taken_by_team`), planification de visite, retour en validation, publication (niveau `verified` / `selection`, grade d'état, notes internes), rejet avec motif ; emails à l'hôte.
- Demandes et réservations globales, annulation par l'équipe (remboursement intégral).
- Identités : file d'attente, consultation via URL signée journalisée, approbation / rejet.
- Leads : filtres, création manuelle, import CSV / JSON (doublons ignorés sur l'URL source), notes, workflow de statuts, conversion en brouillon de bien rattaché à un hôte.
- Tests Playwright des trois parcours critiques + gardes de rôle (`apps/web/tests/e2e/`).

## Tester

- `admin@loka.tn` / `loka-admin` (ou `staff@loka.tn` / `loka-staff`) sur http://localhost:3000/admin.
- `make e2e` (`admin-validation.spec.ts`).

## Reste / questions ouvertes

- Modération des contenus (signalements, suspension d'un hôte) : hors MVP.
- Export des statistiques et graphiques d'évolution : non fait, l'endpoint expose les compteurs bruts.
- Attribution des leads à un membre de l'équipe : possible via PATCH `assigned_to`, pas encore de liste par assigné dans l'interface.
