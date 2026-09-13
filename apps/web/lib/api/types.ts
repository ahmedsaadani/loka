/**
 * Types du contrat API Loka. Miroir des serializers DRF ; la compatibilité avec le schéma
 * OpenAPI généré (lib/api/schema.d.ts, `make types`) est vérifiée dans lib/api/contract.test.ts.
 */

export type Role = "traveler" | "host" | "staff" | "admin";
export type RentalMode = "nightly" | "monthly" | "yearly";
export type PropertyType = "studio" | "apartment" | "villa" | "room_in_shared_flat";
export type PropertyStatus =
  "draft" | "pending_review" | "needs_visit" | "published" | "paused" | "rejected";
export type VerificationLevel = "verified" | "selection";
export type ConditionGrade = "basic" | "good" | "excellent";
export type LocationPrecision = "exact" | "approximate";
export type RequestStatus = "pending" | "accepted" | "declined" | "expired" | "cancelled";
export type BookingStatus =
  "awaiting_deposit" | "confirmed" | "in_progress" | "completed" | "cancelled";
export type IdentityStatus = "pending" | "approved" | "rejected";
export type LeadStatus = "new" | "contacted" | "visit_scheduled" | "converted" | "rejected";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail: string;
  code: string;
  errors?: Record<string, string[] | string>;
}

export interface LatLng {
  lat: number;
  lng: number;
}

// ---------------------------------------------------------------- comptes

export interface HostProfile {
  display_name: string;
  bio: string;
  company_name: string;
  bank_details_masked: string;
}

export interface User {
  public_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: Role;
  is_identity_verified: boolean;
  preferred_language: string;
  host_profile: HostProfile | null;
  created_at: string;
}

export interface AuthResponse {
  access: string;
  user: User;
}

export interface IdentityDocument {
  public_id: string;
  doc_type: "cin" | "passport";
  status: IdentityStatus;
  rejection_reason: string;
  created_at: string;
  reviewed_at: string | null;
  user_email?: string;
  user_public_id?: string;
}

export interface SignedUrl {
  url: string;
  expires_in: number;
}

// ---------------------------------------------------------------- géo

export interface Governorate {
  name: string;
  slug: string;
}

export interface CitySummary {
  name: string;
  slug: string;
  governorate: Governorate;
  centroid: LatLng;
  is_featured: boolean;
  property_count: number;
  avg_monthly_price: string | null;
  avg_nightly_price: string | null;
}

export interface NeighborhoodSummary {
  name: string;
  slug: string;
  city_slug: string;
  centroid: LatLng;
  property_count: number;
  avg_monthly_price: string | null;
}

export interface CityDetail extends CitySummary {
  seo_title: string;
  seo_description: string;
  intro_text: string;
  neighborhoods: NeighborhoodSummary[];
}

export interface NeighborhoodDetail extends NeighborhoodSummary {
  city: CitySummary;
  seo_title: string;
  seo_description: string;
  intro_text: string;
}

// ---------------------------------------------------------------- biens

export interface Photo {
  public_id: string;
  variants: Partial<Record<"thumb" | "card" | "gallery" | "og", string>>;
  width: number;
  height: number;
  alt_text: string;
  is_cover: boolean;
  taken_by_team: boolean;
  order: number;
}

export interface PricingPlan {
  rental_mode: RentalMode;
  price: string;
  price_eur: string;
  min_duration: number;
  max_duration: number | null;
  is_active: boolean;
}

export interface Amenity {
  code: string;
  name: string;
  icon: string;
  category: "essential" | "comfort" | "building" | "safety";
}

export interface CityRef {
  name: string;
  slug: string;
}

export interface PropertyCard {
  public_id: string;
  slug: string;
  title: string;
  property_type: PropertyType;
  rooms_label: string;
  bedrooms: number;
  bathrooms: number;
  surface_m2: number | null;
  furnished: boolean;
  max_guests: number;
  city: CityRef;
  neighborhood: CityRef | null;
  location: LatLng | null;
  location_precision: LocationPrecision;
  cover_photo: Photo | null;
  pricing_plans: PricingPlan[];
  verification_level: VerificationLevel;
  condition_grade: ConditionGrade;
  verified_at: string | null;
  distance_notes: Record<string, string>;
}

export interface PropertyDetail extends PropertyCard {
  description: string;
  floor: number | null;
  has_elevator: boolean;
  photos: Photo[];
  amenities: Amenity[];
  charges_included: boolean;
  monthly_charges_estimate: string | null;
  deposit_months: number;
  min_lease_months: number;
  house_rules: Record<string, boolean>;
  meta_title: string;
  meta_description: string;
  published_at: string | null;
  host: { display_name: string; is_identity_verified: boolean; member_since: string };
}

export interface UnavailableRange {
  start: string;
  end: string;
}

export interface Quote {
  rental_mode: RentalMode;
  units: number;
  unit_label: string;
  unit_price: string;
  subtotal: string;
  fee_rate: string;
  fee: string;
  fee_payer: "traveler" | "host";
  total: string;
  deposit: string;
  security_deposit: string;
  total_eur: string;
  available: boolean;
}

export interface PropertyHost {
  public_id: string;
  slug: string;
  title: string;
  description: string;
  property_type: PropertyType;
  rooms_label: string;
  bedrooms: number;
  bathrooms: number;
  surface_m2: number | null;
  floor: number | null;
  has_elevator: boolean;
  furnished: boolean;
  max_guests: number;
  city: CityRef;
  neighborhood: CityRef | null;
  address_private: string;
  location: LatLng | null;
  location_precision: LocationPrecision;
  status: PropertyStatus;
  rejection_reason: string;
  visit_scheduled_at: string | null;
  verification_level: VerificationLevel;
  condition_grade: ConditionGrade;
  verified_at: string | null;
  charges_included: boolean;
  monthly_charges_estimate: string | null;
  deposit_months: number;
  min_lease_months: number;
  distance_notes: Record<string, string>;
  house_rules: Record<string, boolean>;
  meta_title: string;
  meta_description: string;
  photos: Photo[];
  pricing_plans: PricingPlan[];
  amenities: Amenity[];
  readiness_errors: Record<string, string>;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyStaff extends PropertyHost {
  host_email: string;
  host_public_id: string;
  host_identity_verified: boolean;
  verification_notes: string;
}

export interface PropertyWrite {
  title?: string;
  description?: string;
  property_type?: PropertyType;
  rooms_label?: string;
  bedrooms?: number;
  bathrooms?: number;
  surface_m2?: number | null;
  floor?: number | null;
  has_elevator?: boolean;
  furnished?: boolean;
  max_guests?: number;
  city?: string;
  neighborhood?: string | null;
  address_private?: string;
  location?: LatLng | null;
  location_precision?: LocationPrecision;
  charges_included?: boolean;
  monthly_charges_estimate?: string | null;
  deposit_months?: number;
  min_lease_months?: number;
  distance_notes?: Record<string, string>;
  house_rules?: Record<string, boolean>;
  amenities?: string[];
}

// ---------------------------------------------------------------- disponibilités

export interface AvailabilityBlock {
  id: number;
  start: string;
  end: string;
  kind: "booked" | "blocked_by_host" | "external_ical" | "maintenance";
  note: string;
  booking_public_id: string | null;
  external_uid: string;
}

export interface ExternalCalendar {
  id: number;
  ical_url: string;
  source: "airbnb" | "booking" | "other";
  last_synced_at: string | null;
  last_error: string;
  created_at: string;
}

// ---------------------------------------------------------------- réservations

export interface PropertyRef {
  public_id: string;
  slug: string;
  title: string;
  city: string;
  cover_photo: Photo | null;
}

export interface Party {
  public_id: string;
  display_name: string;
  is_identity_verified: boolean;
}

export interface BookingRequest {
  public_id: string;
  property: PropertyRef;
  traveler: Party;
  rental_mode: RentalMode;
  start_date: string;
  end_date: string;
  guests: number;
  message: string;
  status: RequestStatus;
  quoted_units: number;
  quoted_unit_price: string;
  quoted_subtotal: string;
  quoted_fee: string;
  quoted_total: string;
  quoted_deposit: string;
  expires_at: string;
  decline_reason: string;
  booking_public_id: string | null;
  created_at: string;
}

export interface Payment {
  public_id: string;
  provider: string;
  amount: string;
  currency: string;
  kind: "deposit" | "balance" | "refund";
  status: "initiated" | "succeeded" | "failed" | "refunded";
  checkout_url: string;
  created_at: string;
  provider_ref?: string;
}

export interface Booking {
  public_id: string;
  property: PropertyRef;
  traveler: Party;
  host: Party;
  rental_mode: RentalMode;
  start_date: string;
  end_date: string;
  total_amount: string;
  deposit_amount: string;
  platform_fee: string;
  fee_payer: "traveler" | "host";
  status: BookingStatus;
  cancellation_reason: string;
  payments: Payment[];
  has_contract: boolean;
  created_at: string;
  address_private?: string;
  host_phone?: string;
}

// ---------------------------------------------------------------- leads

export interface Lead {
  public_id: string;
  source: "tayara" | "mubawab" | "facebook" | "manual";
  source_url: string;
  title: string;
  price: string | null;
  city: string;
  phone: string;
  raw_data: Record<string, unknown>;
  status: LeadStatus;
  assigned_to_email: string | null;
  notes: string;
  converted_property_public_id: string | null;
  created_at: string;
  updated_at: string;
}
