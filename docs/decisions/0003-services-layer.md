# ADR 0003 — Logique métier dans des services, machines à états explicites

Date : 2026-09-12 · Statut : accepté

## Contexte

Les statuts de `Property`, `BookingRequest` et `Booking` conditionnent la visibilité publique, les paiements et les emails. Les modifier depuis n'importe quelle vue ou depuis l'admin rendrait le comportement imprévisible et impossible à tester.

## Décision

- Chaque app expose un module `services.py` : fonctions pures d'orchestration (`create_booking_request`, `accept_request`, `publish_property`…), appelées par les vues, l'admin, les tâches Celery et les tests.
- Les transitions de statut sont déclarées dans un dictionnaire `TRANSITIONS = {from: {to, ...}}` par modèle et appliquées par `core.state.transition(instance, to_status, by=user)`. Une transition non listée lève `InvalidTransition`. Chaque transition est journalisée (`StatusLog`).
- Le calcul de prix vit dans `bookings/pricing.py`, sans accès base, pour être testable exhaustivement.
- Les serializers valident la forme des données, pas le métier.

## Règles métier fixées (confirmées le 2026-09-12)

| Règle | Valeur | Emplacement |
|---|---|---|
| Frais de service | nuitée 10 % à la charge du voyageur ; mensuel 5 % et annuel 3 % à la charge de l'hôte, déduits de l'acompte | `settings.PLATFORM_FEE` |
| Expiration d'une demande | 48 h, rappel à l'hôte à 24 h | `settings.BOOKING_REQUEST_TTL_HOURS`, `BOOKING_REQUEST_REMINDER_HOURS` |
| Taux EUR | fixe, indicatif | `settings.EUR_RATE` |
| URL signée privée | 5 min | `settings.S3_PRIVATE_URL_EXPIRY_SECONDS` |

## Conséquences

- Aucune vue ne fait `obj.status = ...`. Une revue de code le refuse.
- Les tests unitaires des services couvrent toutes les transitions, valides et invalides.
