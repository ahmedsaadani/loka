/**
 * Test de contrat : les types écrits à la main (types.ts) doivent avoir exactement les mêmes
 * clés que le schéma OpenAPI généré (schema.d.ts, `make types`). Une divergence casse `tsc`.
 */
import { describe, expect, it } from "vitest";

import type { components } from "./schema.d";
import type * as T from "./types";

type S = components["schemas"];

type Equal<A, B> =
  (<X>() => X extends A ? 1 : 2) extends <X>() => X extends B ? 1 : 2 ? true : false;
type Expect<C extends true> = C;

type KeysMatch<Generated, Hand> = Equal<keyof Generated, keyof Hand>;

// Champs optionnels côté front (ajoutés selon le rôle) retirés de la comparaison stricte.
type WithoutOptional<X> = { [K in keyof X as undefined extends X[K] ? never : K]: X[K] };

type _Checks = [
  Expect<KeysMatch<S["PropertyCard"], T.PropertyCard>>,
  Expect<KeysMatch<S["PropertyDetail"], T.PropertyDetail>>,
  Expect<KeysMatch<S["PropertyHost"], T.PropertyHost>>,
  Expect<KeysMatch<S["PropertyStaff"], T.PropertyStaff>>,
  Expect<KeysMatch<S["Photo"], T.Photo>>,
  Expect<KeysMatch<S["PricingPlan"], T.PricingPlan>>,
  Expect<KeysMatch<S["Amenity"], T.Amenity>>,
  Expect<KeysMatch<S["CitySummary"], T.CitySummary>>,
  Expect<KeysMatch<S["CityDetail"], T.CityDetail>>,
  Expect<KeysMatch<S["NeighborhoodSummary"], T.NeighborhoodSummary>>,
  Expect<KeysMatch<S["NeighborhoodDetail"], T.NeighborhoodDetail>>,
  Expect<KeysMatch<S["User"], T.User>>,
  Expect<KeysMatch<S["HostProfile"], T.HostProfile>>,
  Expect<KeysMatch<S["IdentityDocument"], WithoutOptional<T.IdentityDocument>>>,
  Expect<KeysMatch<S["BookingRequest"], T.BookingRequest>>,
  Expect<KeysMatch<S["Booking"], WithoutOptional<T.Booking>>>,
  Expect<KeysMatch<S["Payment"], WithoutOptional<T.Payment>>>,
  Expect<KeysMatch<S["Lead"], T.Lead>>,
  Expect<KeysMatch<S["AvailabilityBlock"], T.AvailabilityBlock>>,
  Expect<KeysMatch<S["ExternalCalendar"], T.ExternalCalendar>>,
  Expect<KeysMatch<S["SignedUrl"], T.SignedUrl>>,
  Expect<KeysMatch<S["UnavailableRange"], T.UnavailableRange>>,
];

// Vérifications ponctuelles de types de champs typés côté API.
type _FieldChecks = [
  Expect<Equal<S["PropertyCard"]["slug"], string>>,
  Expect<Equal<S["PropertyCard"]["surface_m2"], number | null>>,
  Expect<Equal<S["User"]["is_identity_verified"], boolean>>,
  Expect<Equal<S["BookingRequest"]["guests"], number>>,
];

describe("contrat API", () => {
  it("les types manuels et le schéma généré ont les mêmes clés (vérifié par tsc)", () => {
    const checked: _Checks extends unknown[] ? true : false = true;
    const fields: _FieldChecks extends unknown[] ? true : false = true;
    expect(checked && fields).toBe(true);
  });
});
