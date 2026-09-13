import type { MetadataRoute } from "next";

import { serverApi } from "@/lib/api/client";
import type { CityDetail, CitySummary, Paginated, PropertyCard } from "@/lib/api/types";
import { absoluteUrl } from "@/lib/seo";

export const revalidate = 3600;

async function allProperties(): Promise<PropertyCard[]> {
  const items: PropertyCard[] = [];
  let page = 1;
  for (;;) {
    const data = await serverApi.get<Paginated<PropertyCard>>(
      "/listings/properties/",
      { page, page_size: 50 },
      { revalidate: 3600 },
    );
    items.push(...data.results);
    if (!data.next || page >= 40) break;
    page += 1;
  }
  return items;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [
    { url: absoluteUrl("/"), changeFrequency: "daily", priority: 1 },
    { url: absoluteUrl("/cgu"), changeFrequency: "yearly", priority: 0.2 },
    { url: absoluteUrl("/confidentialite"), changeFrequency: "yearly", priority: 0.2 },
    { url: absoluteUrl("/contact"), changeFrequency: "yearly", priority: 0.3 },
  ];
  try {
    const cities = await serverApi.get<Paginated<CitySummary>>(
      "/geo/cities/",
      { page_size: 50 },
      { revalidate: 3600 },
    );
    for (const city of cities.results) {
      entries.push({
        url: absoluteUrl(`/location/${city.slug}`),
        changeFrequency: "daily",
        priority: 0.9,
      });
      const detail = await serverApi.get<CityDetail>(`/geo/cities/${city.slug}/`, undefined, {
        revalidate: 3600,
      });
      for (const n of detail.neighborhoods) {
        entries.push({
          url: absoluteUrl(`/location/${city.slug}/${n.slug}`),
          changeFrequency: "daily",
          priority: 0.8,
        });
      }
    }
    for (const property of await allProperties()) {
      entries.push({
        url: absoluteUrl(`/logement/${property.slug}`),
        changeFrequency: "weekly",
        priority: 0.7,
      });
    }
  } catch {
    // API indisponible : sitemap minimal
  }
  return entries;
}
