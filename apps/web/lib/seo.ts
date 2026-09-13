import type { Metadata } from "next";

import type { PropertyDetail } from "./api/types";

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const SITE_NAME = "Loka";

export function absoluteUrl(path: string): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

interface PageMeta {
  title: string;
  description: string;
  path: string;
  image?: string;
  noindex?: boolean;
}

export function pageMetadata({ title, description, path, image, noindex }: PageMeta): Metadata {
  const url = absoluteUrl(path);
  // Les titres qui nomment déjà la marque ne reçoivent pas le suffixe « | Loka » du template.
  const mentionsBrand = /Loka/.test(title);
  return {
    title: mentionsBrand ? { absolute: title } : title,
    description,
    alternates: { canonical: url },
    robots: noindex ? { index: false, follow: false } : { index: true, follow: true },
    openGraph: {
      title,
      description,
      url,
      siteName: SITE_NAME,
      locale: "fr_TN",
      type: "website",
      images: image ? [{ url: image, width: 1200, height: 630 }] : undefined,
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title,
      description,
      images: image ? [image] : undefined,
    },
  };
}

export interface Crumb {
  name: string;
  path: string;
}

export function breadcrumbJsonLd(crumbs: Crumb[]): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: absoluteUrl(crumb.path),
    })),
  };
}

const MODE_UNIT: Record<string, string> = { nightly: "DAY", monthly: "MON", yearly: "MON" };

export function accommodationJsonLd(property: PropertyDetail): Record<string, unknown> {
  const url = absoluteUrl(`/logement/${property.slug}`);
  return {
    "@context": "https://schema.org",
    "@type": property.property_type === "villa" ? "House" : "Apartment",
    name: property.title,
    description: property.meta_description || property.description.slice(0, 300),
    url,
    image: property.photos.map((p) => p.variants.gallery).filter(Boolean),
    numberOfRooms: property.bedrooms,
    numberOfBathroomsTotal: property.bathrooms,
    floorSize: property.surface_m2
      ? { "@type": "QuantitativeValue", value: property.surface_m2, unitCode: "MTK" }
      : undefined,
    occupancy: { "@type": "QuantitativeValue", maxValue: property.max_guests },
    address: {
      "@type": "PostalAddress",
      addressLocality: property.city.name,
      addressRegion: property.neighborhood?.name,
      addressCountry: "TN",
    },
    geo: property.location
      ? {
          "@type": "GeoCoordinates",
          latitude: property.location.lat,
          longitude: property.location.lng,
        }
      : undefined,
    amenityFeature: property.amenities.map((a) => ({
      "@type": "LocationFeatureSpecification",
      name: a.name,
      value: true,
    })),
    offers: property.pricing_plans.map((plan) => ({
      "@type": "Offer",
      url,
      priceCurrency: "TND",
      price: plan.price,
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: plan.price,
        priceCurrency: "TND",
        unitCode: MODE_UNIT[plan.rental_mode],
      },
      availability: "https://schema.org/InStock",
    })),
  };
}

export function organizationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    logo: absoluteUrl("/icon.svg"),
    areaServed: "TN",
  };
}

export function faqJsonLd(
  items: Array<{ question: string; answer: string }>,
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: { "@type": "Answer", text: item.answer },
    })),
  };
}
