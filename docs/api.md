# API Loka

Base : `/api/v1/`. Schéma OpenAPI : `/api/v1/schema/`, documentation interactive : `/api/v1/docs/`.
Le front génère ses types depuis le schéma (`make types` → `apps/web/lib/api/schema.d.ts`).

## Conventions

- Authentification : `Authorization: Bearer <access>`. L'access token dure 15 min ; le refresh token est un cookie httpOnly `loka_refresh` (path `/api/v1/auth/`), rotation à chaque `POST /auth/refresh/`, l'ancien est blacklisté.
- Identifiants publics : `public_id` (UUID) ou `slug`. Jamais d'ID séquentiel.
- Erreurs : `{"detail": str, "code": str, "errors"?: {champ: [messages]}}`. Codes utiles : `validation_error`, `not_found`, `permission_denied`, `invalid_transition` (409), `unavailable` (409), `throttled` (429).
- Listes : paginées (`page`, `page_size` ≤ 50) → `{count, next, previous, results}`.
- Rate limiting : anonymes 120/min, connectés 600/min, `auth` 10/min, `register` 5/h, `booking_request` 10/h, `lead_import` 5/h, `upload` 60/h.

## Endpoints

### Public (sans authentification)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/health/` | Santé API + base |
| GET | `/geo/cities/?is_featured=true` | Villes avec nombre de biens et prix moyens |
| GET | `/geo/cities/{slug}/` | Ville + quartiers + textes SEO |
| GET | `/geo/neighborhoods/?city__slug=` | Quartiers |
| GET | `/geo/cities/{city}/neighborhoods/{slug}/` | Quartier + textes SEO |
| GET | `/listings/properties/` | Recherche : `city`, `neighborhood`, `rental_mode`, `min_price`, `max_price`, `property_type` (multi), `bedrooms_min`, `guests`, `furnished`, `amenities=wifi,ac`, `bbox=minLng,minLat,maxLng,maxLat`, `start`, `end`, `ordering=newest|price|-price` |
| GET | `/listings/properties/{slug}/` | Fiche complète (photos, équipements, hôte, infos pratiques) |
| GET | `/listings/properties/{slug}/availability/?from&to` | Périodes indisponibles fusionnées |
| GET | `/listings/properties/{slug}/quote/?rental_mode&start&end` | Devis + disponibilité |
| GET | `/listings/amenities/` | Référentiel des équipements |

### Auth

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/auth/register/` | Inscription voyageur ou hôte → `{access, user}` + cookie |
| POST | `/auth/login/` | Connexion |
| POST | `/auth/refresh/` | Nouveau access token (cookie requis) |
| POST | `/auth/logout/` | Blacklist + suppression du cookie |
| GET / PATCH | `/auth/me/` | Profil |
| GET / POST | `/auth/identity-documents/` | Mes pièces d'identité (upload multipart `doc_type`, `file`) |
| GET | `/auth/identity-documents/{id}/download/` | URL signée 5 min (journalisé) |
| GET | `/auth/identity-documents/pending/` | Staff : file d'attente |
| POST | `/auth/identity-documents/{id}/approve/` · `/reject/` | Staff |

### Hôte (`role` host)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET / POST | `/listings/host/properties/` | Mes biens / créer un brouillon |
| GET / PATCH / DELETE | `/listings/host/properties/{id}/` | Détail, modification (draft ou rejected), suppression (draft) |
| POST | `.../submit/` `.../withdraw/` `.../pause/` `.../resume/` | Transitions |
| POST | `.../photos/` | Upload (multipart `image`, `alt_text`) |
| POST | `.../photos/reorder/` | `{order: [uuid...]}` |
| DELETE | `.../photos/{photo_id}/` | Supprimer |
| POST | `.../pricing/` | Créer / mettre à jour un plan `{rental_mode, price, min_duration, max_duration}` |
| DELETE | `.../pricing/{mode}/` | Supprimer un plan |
| GET / POST | `/availability/host/properties/{id}/blocks/` | Calendrier / bloquer des dates |
| DELETE | `/availability/host/properties/{id}/blocks/{block_id}/` | Débloquer |
| GET / POST | `/availability/host/properties/{id}/calendars/` | iCal externes (HTTPS) |
| POST / DELETE | `/availability/host/properties/{id}/calendars/{cal_id}/` | Resynchroniser / supprimer |
| GET | `/bookings/host/requests/?status=` | Demandes reçues |
| POST | `/bookings/host/requests/{id}/accept/` · `/decline/` | Réponse |
| GET | `/bookings/host/bookings/` | Réservations |
| POST | `/bookings/host/bookings/{id}/cancel/` | Annulation (remboursement intégral) |
| GET | `/bookings/host/bookings/{id}/contract/` | URL signée du contrat |

### Voyageur

| Méthode | Chemin | Rôle |
|---|---|---|
| GET / POST | `/bookings/requests/` | Mes demandes / nouvelle demande `{property (slug), rental_mode, start_date, end_date, guests, message}` |
| POST | `/bookings/requests/{id}/cancel/` | Retirer |
| GET | `/bookings/bookings/` · `/{id}/` | Réservations (adresse exacte après confirmation, journalisé) |
| POST | `/bookings/bookings/{id}/pay-deposit/` | Crée le paiement → `checkout_url` |
| POST | `/bookings/bookings/{id}/cancel/` | Annulation (remboursement selon ADR 0005) |
| GET | `/bookings/bookings/{id}/contract/` | URL signée du contrat |

### Équipe (`role` staff / admin)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/listings/staff/properties/?status=pending_review` | File de validation |
| GET | `/listings/staff/properties/{id}/` | Détail avec adresse exacte (journalisé) |
| POST | `.../schedule-visit/` `{visit_at, note}` · `.../back-to-review/` · `.../publish/` `{verification_level, condition_grade, notes}` · `.../reject/` `{reason}` | Transitions |
| POST | `.../photos/` | Photo équipe (`taken_by_team`) |
| GET | `/bookings/staff/requests/` · `/bookings/staff/bookings/` | Vue globale |
| GET / POST / PATCH | `/leads/` | Leads |
| POST | `/leads/{id}/status/` `{status, note}` · `/leads/{id}/convert/` `{host_email, city}` | Suivi / conversion |
| POST | `/leads/import/` | multipart `file` CSV ou JSON |

### Webhooks

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/bookings/webhooks/mock/` | Prestataire mock : `{provider_ref, outcome, amount, currency, signature}` (HMAC-SHA256 de `ref:outcome` avec `SECRET_KEY`) |
| GET | `/bookings/mock/sign/{provider_ref}/` | Dev : signatures pour la page `/paiement/mock` (voyageur concerné ou staff) |

Les prestataires réels (Konnect, ClicToPay, Flouci) implémenteront `bookings.payments.base.PaymentProvider` et un endpoint de webhook dédié.
