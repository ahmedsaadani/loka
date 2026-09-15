import {
  BadgeCheck,
  Bath,
  BedDouble,
  Building2,
  Info,
  MapPin,
  Ruler,
  Sofa,
  Star,
  Users,
} from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JsonLd } from "@/components/JsonLd";
import { AvailabilityCalendar } from "@/components/listing/AvailabilityCalendar";
import { BookingBox } from "@/components/listing/BookingBox";
import { ConditionBadge } from "@/components/listing/ConditionBadge";
import { Gallery } from "@/components/listing/Gallery";
import { MobileBookingBar } from "@/components/listing/MobileBookingBar";
import { PropertyMapLazy } from "@/components/listing/PropertyMapLazy";
import { ShareButton } from "@/components/listing/ShareButton";
import { PricingTabs } from "@/components/listing/PricingTabs";
import { PropertyCard } from "@/components/listing/PropertyCard";
import { VerifiedBadge } from "@/components/listing/VerifiedBadge";
import { Separator } from "@/components/ui/separator";
import { ApiRequestError, serverApi } from "@/lib/api/client";
import type { Paginated, PropertyCard as PropertyCardData, PropertyDetail } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { accommodationJsonLd, breadcrumbJsonLd, pageMetadata } from "@/lib/seo";
import { CONDITION_LABEL, formatDate, formatTnd, PROPERTY_TYPE_LABEL } from "@/lib/utils";

interface Params {
  slug: string;
}

async function loadProperty(slug: string): Promise<PropertyDetail | null> {
  try {
    return await serverApi.get<PropertyDetail>(`/listings/properties/${slug}/`, undefined, {
      revalidate: 300,
      tags: [`property:${slug}`],
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return null;
    throw error;
  }
}

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const property = await loadProperty(slug);
  if (!property) return { title: t.common.notFound };
  const typeLabel = property.rooms_label || PROPERTY_TYPE_LABEL[property.property_type];
  const title =
    property.meta_title ||
    `${typeLabel} à ${property.neighborhood?.name ?? property.city.name} · ${property.title}`;
  const description =
    property.meta_description ||
    `${typeLabel} ${property.furnished ? "meublé" : ""} à ${property.city.name}, vérifié par Loka le ${property.verified_at ? formatDate(property.verified_at) : ""}. ${property.description.slice(0, 140)}`;
  return pageMetadata({
    title,
    description,
    path: `/logement/${property.slug}`,
    image: property.cover_photo?.variants.og,
  });
}

export default async function PropertyPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const property = await loadProperty(slug);
  if (!property) notFound();

  const similar = await serverApi
    .get<Paginated<PropertyCardData>>(
      "/listings/properties/",
      { city: property.city.slug, page_size: 4 },
      { revalidate: 300 },
    )
    .then((r) => r.results.filter((p) => p.public_id !== property.public_id).slice(0, 3))
    .catch(() => []);

  const crumbs = [
    { name: t.nav.home, path: "/" },
    { name: property.city.name, path: `/location/${property.city.slug}` },
    ...(property.neighborhood
      ? [
          {
            name: property.neighborhood.name,
            path: `/location/${property.city.slug}/${property.neighborhood.slug}`,
          },
        ]
      : []),
    { name: property.title, path: `/logement/${property.slug}` },
  ];
  const typeLabel = property.rooms_label
    ? `${PROPERTY_TYPE_LABEL[property.property_type]} ${property.rooms_label}`
    : PROPERTY_TYPE_LABEL[property.property_type];
  const rules = Object.entries(property.house_rules);

  return (
    <article className="container py-4 md:py-8">
      <nav aria-label="Fil d'Ariane" className="mb-3 text-sm text-muted-foreground">
        <ol className="flex flex-wrap gap-1">
          {crumbs.slice(0, -1).map((c) => (
            <li key={c.path}>
              <Link href={c.path} className="hover:text-foreground">
                {c.name}
              </Link>
              <span className="mx-1">/</span>
            </li>
          ))}
          <li className="text-foreground">{typeLabel}</li>
        </ol>
      </nav>

      <Gallery photos={property.photos} title={property.title} />

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-8">
          <header>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <VerifiedBadge
                  level={property.verification_level}
                  verifiedAt={property.verified_at}
                  showDate
                />
                <ConditionBadge grade={property.condition_grade} />
              </div>
              <ShareButton title={property.title} />
            </div>
            <h1 className="mt-3 text-2xl md:text-4xl">{property.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-muted-foreground">
              {property.rating && (
                <span className="inline-flex items-center gap-1 font-medium text-foreground">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  {Number(property.rating).toFixed(1)}
                  <span className="font-normal text-muted-foreground">
                    · {property.review_count} avis
                  </span>
                </span>
              )}
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {typeLabel} · {property.neighborhood ? `${property.neighborhood.name}, ` : ""}
                {property.city.name}
              </span>
            </div>
            <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm">
              <li className="inline-flex items-center gap-1.5">
                <Users className="h-4 w-4 text-muted-foreground" /> {property.max_guests}{" "}
                {t.listing.guests}
              </li>
              <li className="inline-flex items-center gap-1.5">
                <BedDouble className="h-4 w-4 text-muted-foreground" /> {property.bedrooms}{" "}
                {t.listing.bedrooms}
              </li>
              <li className="inline-flex items-center gap-1.5">
                <Bath className="h-4 w-4 text-muted-foreground" /> {property.bathrooms}{" "}
                {t.listing.bathrooms}
              </li>
              {property.surface_m2 && (
                <li className="inline-flex items-center gap-1.5">
                  <Ruler className="h-4 w-4 text-muted-foreground" /> {property.surface_m2}{" "}
                  {t.listing.surface}
                </li>
              )}
              {property.floor !== null && (
                <li className="inline-flex items-center gap-1.5">
                  <Building2 className="h-4 w-4 text-muted-foreground" /> {t.listing.floor}{" "}
                  {property.floor}
                  {property.has_elevator ? ` · ${t.listing.elevator}` : ""}
                </li>
              )}
              {property.furnished && (
                <li className="inline-flex items-center gap-1.5">
                  <Sofa className="h-4 w-4 text-muted-foreground" /> {t.listing.furnished}
                </li>
              )}
            </ul>
          </header>

          <section aria-labelledby="prix">
            <h2 id="prix" className="mb-3 text-lg">
              Tarifs
            </h2>
            <PricingTabs plans={property.pricing_plans} />
          </section>

          <section
            className="rounded-xl border bg-verified-soft/60 p-4"
            aria-label="Vérification Loka"
          >
            <div className="flex gap-3">
              <BadgeCheck className="mt-0.5 h-5 w-5 shrink-0 text-verified" />
              <div className="text-sm">
                <p className="font-semibold text-verified">
                  {property.verification_level === "selection"
                    ? t.listing.selection
                    : t.listing.verifiedBy}
                  {property.verified_at
                    ? ` · ${t.listing.verifiedOn} ${formatDate(property.verified_at)}`
                    : ""}
                </p>
                <p className="mt-1 text-muted-foreground">
                  Notre équipe a visité ce logement, pris les photos et évalué son état :{" "}
                  {CONDITION_LABEL[property.condition_grade]?.toLowerCase()}.
                  {property.photos.some((p) => p.taken_by_team)
                    ? " Les photos sont celles de l'équipe Loka."
                    : ""}
                </p>
              </div>
            </div>
          </section>

          <section aria-labelledby="description">
            <h2 id="description" className="mb-3 text-lg">
              {t.listing.description}
            </h2>
            <div className="whitespace-pre-line leading-relaxed text-foreground/90">
              {property.description}
            </div>
          </section>

          {property.amenities.length > 0 && (
            <section aria-labelledby="equipements">
              <h2 id="equipements" className="mb-3 text-lg">
                {t.listing.amenities}
              </h2>
              <ul className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                {property.amenities.map((a) => (
                  <li
                    key={a.code}
                    className="flex items-center gap-2 rounded-md border bg-card px-3 py-2"
                  >
                    <BadgeCheck className="h-4 w-4 text-verified" /> {a.name}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="pratique">
            <h2 id="pratique" className="mb-3 text-lg">
              {t.listing.practical}
            </h2>
            <dl className="grid gap-3 rounded-xl border bg-card p-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">{t.listing.charges}</dt>
                <dd className="font-medium">
                  {property.charges_included
                    ? t.listing.chargesIncluded
                    : t.listing.chargesExcluded}
                  {!property.charges_included && property.monthly_charges_estimate
                    ? ` (${t.listing.chargesEstimate} ${formatTnd(property.monthly_charges_estimate)} / mois)`
                    : ""}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t.listing.deposit}</dt>
                <dd className="font-medium">
                  {property.deposit_months} {t.listing.depositMonths}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t.listing.minLease}</dt>
                <dd className="font-medium">{property.min_lease_months} mois (location au mois)</dd>
              </div>
              {rules.length > 0 && (
                <div>
                  <dt className="text-muted-foreground">Règles</dt>
                  <dd className="font-medium">
                    {rules
                      .map(
                        ([k, v]) =>
                          `${{ smoking: "Fumeur", pets: "Animaux", parties: "Fêtes" }[k] ?? k} : ${v ? "oui" : "non"}`,
                      )
                      .join(" · ")}
                  </dd>
                </div>
              )}
            </dl>
            {Object.keys(property.distance_notes).length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-sm font-semibold">{t.listing.distances}</h3>
                <ul className="flex flex-wrap gap-2 text-sm">
                  {Object.entries(property.distance_notes).map(([place, dist]) => (
                    <li key={place} className="rounded-full bg-muted px-3 py-1">
                      <span className="font-medium">{place}</span> · {dist}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {property.location && (
            <section aria-labelledby="localisation">
              <h2 id="localisation" className="mb-3 text-lg">
                {t.listing.location}
              </h2>
              <PropertyMapLazy
                location={property.location}
                approximate={property.location_precision === "approximate"}
                className="h-72 w-full overflow-hidden rounded-xl border"
              />
              {property.location_precision === "approximate" && (
                <p className="mt-2 flex items-start gap-1.5 text-xs text-muted-foreground">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {t.listing.approximateLocation}
                </p>
              )}
            </section>
          )}

          <section aria-labelledby="dispo">
            <h2 id="dispo" className="mb-3 text-lg">
              {t.listing.calendar}
            </h2>
            <AvailabilityCalendar slug={property.slug} />
          </section>

          <Separator />

          <section aria-labelledby="hote" className="flex items-center gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-full bg-accent text-lg font-semibold text-accent-foreground">
              {property.host.display_name.slice(0, 1).toUpperCase()}
            </div>
            <div>
              <h2 id="hote" className="text-base">
                {t.listing.host} : {property.host.display_name}
              </h2>
              <p className="text-sm text-muted-foreground">
                {property.host.is_identity_verified ? `${t.listing.hostVerified} · ` : ""}
                {t.listing.memberSince}{" "}
                {formatDate(property.host.member_since, { month: "long", year: "numeric" })}
              </p>
            </div>
          </section>
        </div>

        <aside className="lg:sticky lg:top-20 lg:self-start">
          <div className="hidden lg:block">
            <BookingBox
              slug={property.slug}
              plans={property.pricing_plans}
              maxGuests={property.max_guests}
            />
          </div>
        </aside>
      </div>

      {similar.length > 0 && (
        <section className="mt-12" aria-labelledby="similaires">
          <h2 id="similaires" className="mb-4 text-xl">
            {t.listing.similar}
          </h2>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {similar.map((p) => (
              <PropertyCard key={p.public_id} property={p} />
            ))}
          </div>
        </section>
      )}

      <MobileBookingBar
        slug={property.slug}
        plans={property.pricing_plans}
        maxGuests={property.max_guests}
      />

      <JsonLd data={[accommodationJsonLd(property), breadcrumbJsonLd(crumbs)]} />
    </article>
  );
}
