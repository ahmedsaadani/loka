# ADR 0005 — Acompte, annulation, modification d'un bien publié

Date : 2026-09-12 · Statut : accepté (choix prudents pris en autonomie, à confirmer)

## Contexte

Les règles suivantes n'étaient pas fixées dans le cahier des charges. Sans réponse disponible, l'option la plus prudente pour les utilisateurs a été retenue et centralisée dans `settings`.

## Décisions

| Sujet | Règle | Constante |
|---|---|---|
| Acompte nuitée | 30 % du total voyageur (sous-total + frais 10 %) | `BOOKING_DEPOSIT_RATE_NIGHTLY` |
| Acompte mensuel / annuel | un mois de loyer ; les frais hôte (5 % / 3 % du total) sont déduits de cet acompte avant reversement | `PLATFORM_FEE`, `PLATFORM_FEE_PAYER` |
| Prix annuel | `PricingPlan.price` en mode `yearly` est un **loyer mensuel** pour un bail de 12 mois exactement ; total = 12 × prix | `bookings/pricing.py` |
| Durée mensuelle | la date de fin doit tomber le même jour du mois que le début (mois entiers) | `months_between` |
| Caution | `Property.deposit_months` × loyer mensuel, versée hors plateforme, affichée à titre informatif | — |
| Annulation par le voyageur | acompte remboursé si annulation ≥ 7 jours avant l'arrivée, sinon conservé par l'hôte | `BOOKING_FREE_CANCELLATION_DAYS` |
| Annulation par l'hôte ou le staff | acompte toujours remboursé | — |
| Solde | payé hors plateforme au MVP (hors périmètre) | — |
| Modification d'un bien publié | interdite ; l'hôte met en pause, repasse en brouillon, modifie et resoumet à validation | `HostPropertyViewSet.partial_update` |
| Acceptation d'une demande | refuse automatiquement les autres demandes en attente sur des dates qui chevauchent | `bookings.services._decline_conflicting_requests` |
| Demande expirée à l'acceptation | passée en `expired` et refus 409 | `accept_request` |
| Statut de séjour | `confirmed → in_progress` le jour d'arrivée, `in_progress → completed` le jour de départ, par tâche Celery horaire | `advance_booking_statuses` |

## Conséquences

- Ces valeurs sont toutes dans `config/settings/base.py` avec un commentaire ; les changer ne demande aucune migration.
- Les tests de `bookings/tests/test_pricing.py` et `test_services.py` fixent le comportement ; toute modification de règle doit les mettre à jour.
- À valider avec le métier avant la mise en production : taux d'acompte nuitée, délai d'annulation gratuite, politique de remboursement partiel.
