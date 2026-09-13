# Rapport Phase 4 — Réservation et paiement

Commits : `c7877d1` (API), `fd16924` (front).

## Fait

- Devis instantané (`GET /listings/properties/{slug}/quote/`) avec disponibilité, puis demande de réservation depuis la fiche (dates, voyageurs, message). Règles figées (ADR 0003 / 0005) : nuitée 10 % voyageur, mensuel 5 % et annuel 3 % hôte déduits de l'acompte ; acompte = 30 % (nuit) ou un mois de loyer ; expiration 48 h avec rappel hôte à 24 h ; devis figé sur la demande.
- Acceptation → `Booking` en attente d'acompte, bloc `booked` protégé par la contrainte d'exclusion PostgreSQL, refus automatique des demandes concurrentes, emails (reçue, acceptée, refusée, expirée, acompte payé, annulée).
- Paiement via `PaymentProvider` : implémentation mock avec page de checkout simulée (`/paiement/mock`) et webhook HMAC signé avec `SECRET_KEY` (non forgeable depuis le front), idempotent, contrôle du montant. Interface prête pour Konnect / ClicToPay / Flouci.
- Confirmation → adresse exacte et téléphone de l'hôte révélés au voyageur (accès journalisé), contrat PDF WeasyPrint pour les modes mensuel / annuel (bucket privé, URL signée).
- Annulation : remboursement de l'acompte si voyageur ≥ 7 jours avant l'arrivée ou si annulation par l'hôte / l'équipe ; libération des dates ; passage automatique en cours / terminée par tâche Celery.
- Espace voyageur : demandes (retrait), réservations, paiement, contrat, identité.

## Tester

- `make e2e` (`search-booking.spec.ts`), puis côté hôte accepter la demande, côté voyageur « Payer l'acompte » → page mock → « Simuler un paiement réussi ».
- API : `bookings/tests/test_pricing.py` (exhaustif), `test_services.py` (transitions valides et interdites, paiement, remboursement), `test_api.py` (rôles, webhook forgé refusé).

## Reste / questions ouvertes

- Prestataire réel : Konnect est le plus simple à intégrer (checkout hébergé + webhook) ; prévoir l'endpoint `/bookings/webhooks/konnect/` et la vérification de signature spécifique.
- Solde : payé hors plateforme au MVP ; le modèle `Payment.kind = balance` est prêt.
- Politique d'annulation (7 jours, 30 % d'acompte nuitée) à valider par le métier avant production.
