# ADR 0007 — Règles métier v2 (amende l'ADR 0005)

Date : 2026-09-13 · Statut : accepté (décisions du propriétaire du produit, Phase 6)

## Contexte

L'ADR 0005 avait fixé des règles prudentes en l'absence de décision métier. Le produit a tranché : prix annuel propre, délais d'annulation par mode, modification des biens publiés sans repasser systématiquement par le brouillon, et identité vérifiée obligatoire pour publier.

## Décisions

| Sujet | ADR 0005 (avant) | ADR 0007 (maintenant) | Emplacement |
|---|---|---|---|
| Prix annuel | loyer mensuel × 12 | **prix annuel saisi par l'hôte** (`PricingPlan.price` en mode `yearly` = montant pour 12 mois). L'API expose `monthly_equivalent` (= prix / 12, arrondi) affiché « soit X DT/mois » à titre indicatif. | `bookings/pricing.py`, `listings/serializers.py` |
| Acompte | idem | nuitée : 30 % du total voyageur ; mensuel : un mois de loyer ; annuel : un douzième du prix annuel (un mois). | `BOOKING_DEPOSIT_RATE_NIGHTLY`, `pricing.py` |
| Annulation voyageur | 7 jours pour tous les modes | remboursement intégral de l'acompte si annulation **≥ 7 jours** avant l'arrivée (nuitée), **≥ 30 jours** (mensuel, annuel) ; au-delà l'acompte reste acquis à l'hôte. | `BOOKING_FREE_CANCELLATION_DAYS = {mode: jours}` |
| Annulation hôte ou staff | remboursement intégral | idem, avec une ligne d'audit dédiée `booking_cancelled_by_host` (acteur, montant remboursé). | `bookings/services.cancel_booking` |
| Modification d'un bien publié | interdite (pause → brouillon → resoumission) | autorisée. Deux familles de champs : **sans revalidation** (prix et plans tarifaires, calendrier et iCal, règles de la maison, conditions tarifaires : charges, caution, durée minimale) ; **avec revalidation** (photos ajoutées ou supprimées, titre, description, type, pièces, surface, étage, ascenseur, meublé, capacité, adresse, position, ville, quartier, équipements, distances). Une modification avec revalidation fait passer le bien en `pending_review` ; **la version publiée reste visible et réservable pendant la revue** grâce à un instantané (`Property.published_snapshot`) servi par l'API publique tant que le statut est `pending_review` ou `needs_visit`. Le réordonnancement des photos reste sans revalidation. | `listings/services.update_property`, `add_photo`, `delete_photo`, `PropertyQuerySet.publicly_visible` |
| Réservation pendant la revue | — | autorisée sur la version publiée (l'instantané est la seule version visible ; les prix sont lus en direct car ils ne passent pas par la revue). | `bookings/services.create_booking_request` |
| Fin de revue | — | publication → l'instantané est régénéré ; rejet → le bien disparaît du site (statut `rejected`, instantané effacé) et l'hôte est prévenu par email ; retour en brouillon → instantané effacé. | `listings/services.publish`, `reject`, `withdraw_to_draft` |
| Identité de l'hôte | facultative | **obligatoire pour soumettre un bien à validation** : `submit_for_review` refuse tant qu'aucun document d'identité de l'hôte n'est `approved` (code `identity_required`). Facultative pour réserver. | `listings/services.readiness_errors` |
| Transitions ajoutées | — | `published → pending_review`, `paused → pending_review` (modification avec revalidation). | `Property.TRANSITIONS` |

## Conséquences

- Nouveau champ `Property.published_snapshot` (JSON) : représentation publique « carte » et « fiche » figée à la publication. Les serializers publics renvoient l'instantané quand `is_serving_snapshot` est vrai.
- Les filtres de recherche (ville, quartier, prix) lisent les champs vivants : pendant une revue, un bien dont l'hôte a changé de quartier peut apparaître dans le nouveau quartier avec l'ancienne fiche. Cas rare, accepté, corrigé à la fin de la revue.
- Les variantes WebP d'une photo supprimée restent dans le bucket public jusqu'à la prochaine publication (l'instantané y fait référence). Nettoyage à la publication.
- Emails ajoutés : `property_changes_under_review` (hôte), l'email de rejet mentionne que l'annonce a été retirée.
- Tests mis à jour : tarification annuelle, politique d'annulation par mode, table des transitions, modification d'un bien publié (chaque famille de champs), visibilité de l'instantané, identité requise.
