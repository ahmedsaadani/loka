# Modèle de données

Toutes les entités publiques exposent un `public_id` (UUID) dans les URLs ; les IDs séquentiels ne sortent jamais de l'API. Les statuts changent uniquement via les services (ADR 0003) et chaque transition est journalisée dans `StatusLog`.

```mermaid
erDiagram
  User ||--o| HostProfile : "profil hôte"
  User ||--o{ IdentityDocument : "pièces d'identité"
  User ||--o{ Property : "héberge"
  User ||--o{ BookingRequest : "demande"
  User ||--o{ Booking : "voyage"

  Governorate ||--o{ City : contient
  City ||--o{ Neighborhood : contient
  City ||--o{ Property : localise
  Neighborhood ||--o{ Property : localise

  Property ||--o{ PropertyPhoto : photos
  Property ||--o{ PricingPlan : "0..3 plans"
  Property }o--o{ Amenity : "PropertyAmenity"
  Property ||--o{ AvailabilityBlock : indisponibilités
  Property ||--o{ ExternalCalendar : iCal
  Property ||--o{ BookingRequest : reçoit
  Property ||--o{ Booking : réservations

  BookingRequest ||--o| Booking : "si acceptée"
  Booking ||--o{ Payment : paiements
  Booking ||--o| AvailabilityBlock : "bloc booked"
  Booking ||--o| Review : "avis (hors MVP)"
  ExternalCalendar ||--o{ AvailabilityBlock : "blocs importés"

  Lead }o--o| Property : "converti en"
  Lead }o--o| User : "assigné à"

  User {
    uuid public_id
    string email UK
    string role "traveler|host|staff|admin"
    bool is_identity_verified
    string preferred_language
  }
  HostProfile {
    string display_name
    string bank_iban_private "jamais sérialisé"
    string bank_details_masked
  }
  IdentityDocument {
    uuid public_id
    string doc_type "cin|passport"
    file file "bucket private"
    string status "pending|approved|rejected"
  }
  City {
    string slug UK
    point centroid
    string seo_title
    text intro_text
    bool is_featured
  }
  Neighborhood {
    string slug
    point centroid
    multipolygon boundary
  }
  Property {
    uuid public_id
    string slug UK
    string property_type "studio|apartment|villa|room_in_shared_flat"
    string status "draft|pending_review|needs_visit|published|paused|rejected"
    string verification_level "verified|selection"
    string condition_grade "basic|good|excellent"
    string address_private "jamais public"
    point location
    string location_precision "exact|approximate"
    json distance_notes
    json house_rules
    json published_snapshot "version publique figée (ADR 0007)"
  }
  SiteContent {
    string key UK "cgu|confidentialite|contact"
    string title
    text body "Markdown"
    bool is_published
  }
  PropertyPhoto {
    uuid public_id
    image original "bucket private"
    json variants "thumb|card|gallery|og en WebP public"
    bool is_cover
    bool taken_by_team
  }
  PricingPlan {
    string rental_mode "nightly|monthly|yearly"
    decimal price "TND par nuit ou par mois"
    int min_duration
    int max_duration
  }
  AvailabilityBlock {
    date start
    date end "exclu"
    string kind "booked|blocked_by_host|external_ical|maintenance"
  }
  BookingRequest {
    uuid public_id
    string status "pending|accepted|declined|expired|cancelled"
    decimal quoted_total
    decimal quoted_deposit
    datetime expires_at "48 h"
  }
  Booking {
    uuid public_id
    string status "awaiting_deposit|confirmed|in_progress|completed|cancelled"
    decimal total_amount
    decimal deposit_amount
    decimal platform_fee
    string fee_payer "traveler|host"
    file contract_pdf "bucket private"
  }
  Payment {
    string provider
    string provider_ref
    string kind "deposit|balance|refund"
    string status "initiated|succeeded|failed|refunded"
  }
  Lead {
    string source "tayara|mubawab|facebook|manual"
    string status "new|contacted|visit_scheduled|converted|rejected"
    json raw_data
  }
```

## Machines à états

### Property

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> pending_review : hôte soumet (complétude vérifiée)
  pending_review --> needs_visit : équipe planifie une visite
  pending_review --> published : équipe publie
  pending_review --> rejected : équipe rejette (motif)
  pending_review --> draft : hôte retire
  needs_visit --> published : après visite
  needs_visit --> rejected
  needs_visit --> pending_review
  published --> paused : hôte met en pause
  published --> pending_review : modification descriptive (ancienne version visible)
  paused --> pending_review : modification descriptive
  paused --> published : hôte réactive
  paused --> draft : hôte modifie (re-validation)
  rejected --> draft : hôte corrige
```

ADR 0007 : un bien est modifiable dans tous les états. Sur un bien publié ou en pause, les champs descriptifs et les photos renvoient en `pending_review` tandis que `published_snapshot` (version publique figée à la publication) reste servie par l'API publique ; prix, calendrier, règles et conditions s'appliquent sans revalidation. La soumission exige une pièce d'identité approuvée pour l'hôte.

### BookingRequest

`pending` → `accepted` (crée un `Booking` et un bloc `booked`), `declined`, `expired` (tâche Celery après 48 h, rappel hôte à 24 h) ou `cancelled` (par le voyageur). Les états d'arrivée sont terminaux. Accepter une demande refuse automatiquement les autres demandes en attente qui chevauchent les dates.

### Booking

`awaiting_deposit` → `confirmed` (webhook de paiement) → `in_progress` (jour d'arrivée) → `completed` (jour de départ). `cancelled` est possible depuis `awaiting_deposit` et `confirmed` ; le bloc de disponibilité est libéré et le remboursement suit l'ADR 0005.

## Contraintes base de données

- `availability_no_overlapping_bookings` : contrainte d'exclusion PostgreSQL (`btree_gist`) sur `daterange(start, end, '[)') && ` et `property =`, limitée à `kind = 'booked'`. Deux réservations d'un même bien ne peuvent jamais se chevaucher, même en cas de course entre deux requêtes.
- `availability_end_after_start` : `end > start`.
- `lead_unique_source_url` : une URL d'annonce n'est importée qu'une fois.
- `PricingPlan (property, rental_mode)` unique : un plan par mode.

## Données sensibles

| Donnée | Stockage | Exposition |
|---|---|---|
| `Property.address_private` | colonne | hôte du bien, staff (journalisé), voyageur d'une réservation confirmée (journalisé) |
| `IdentityDocument.file` | bucket privé, nom généré | URL signée 5 min via `/download/`, journalisé |
| `PropertyPhoto.original` | bucket privé | jamais ; seules les variantes WebP publiques sont servies |
| `Booking.contract_pdf` | bucket privé | URL signée via `/contract/`, journalisé |
| `HostProfile.bank_iban_private` | colonne | jamais sérialisé ; seul `bank_details_masked` sort |
