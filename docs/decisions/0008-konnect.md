# ADR 0008 — Konnect comme premier prestataire de paiement réel

Date : 2026-09-13 · Statut : accepté

## Contexte

Le MVP encaisse l'acompte via un prestataire mock. Pour ouvrir de vraies réservations en Tunisie,
il faut une passerelle acceptant les cartes locales et internationales, e-DINAR et les wallets, avec
une API simple et un environnement sandbox. Konnect répond à ces critères ; ClicToPay et Flouci
restent envisageables plus tard grâce à l'abstraction `PaymentProvider` (ADR 0003).

Contraintes : montants en millimes chez Konnect, webhook non signé d'après la documentation
publique, pas d'endpoint de remboursement documenté.

## Décisions

- **`KonnectPaymentProvider`** implémente le contrat `PaymentProvider` sans nouvelle dépendance
  (`urllib`, délai 15 s, `KonnectError` typé sans jamais exposer la clé API). Sélection par
  `PAYMENT_PROVIDER=konnect` ; `ImproperlyConfigured` si `KONNECT_API_KEY` ou `KONNECT_WALLET_ID`
  manquent. Sandbox par défaut (`KONNECT_SANDBOX=1`).
- **Conversion exacte TND ↔ millimes** : `Decimal` → entier, refus de tout montant non
  représentable. Seule la devise TND est acceptée.
- **Le webhook n'est jamais cru.** `parse_webhook` relit `GET /payments/{ref}` avec la clé API et
  n'applique que `status == completed`. Défense en profondeur : l'URL de webhook porte un jeton
  secret (`KONNECT_WEBHOOK_TOKEN`) vérifié en temps constant par la vue (403 sinon), qui est
  également désactivée quand le prestataire actif n'est pas Konnect.
- **La vue répond vite** : 200 avec le statut du paiement, 404 si la référence est inconnue, 502
  si Konnect est injoignable (pour laisser Konnect réessayer). Rate limit scope `auth`.
- **Réconciliation manuelle** par `manage.py check_payment <provider_ref>`, qui réutilise le même
  `handle_payment_result` idempotent que le webhook.
- **Remboursements manuels** : `refund` lève `NotImplementedError` tant que Konnect ne documente pas
  d'endpoint. `services.cancel_booking` n'est pas modifié ; l'exception remonte et la transaction
  est annulée (point ouvert, voir docs/payments.md).

## Conséquences

- Nouvelles variables d'environnement `KONNECT_*` ; `KONNECT_WEBHOOK_URL` doit être l'URL publique
  de l'API, joignable par Konnect (tunnel en dev).
- Les tests du prestataire mockent la couche HTTP avec des réponses enregistrées
  (`bookings/tests/fixtures/konnect/`). Aucun test n'appelle Konnect.
- À faire avant d'annuler des réservations confirmées en production : traiter le cas
  `NotImplementedError` dans `cancel_booking` (remboursement à solder manuellement) et confirmer les
  points listés dans docs/payments.md avec le support Konnect.
