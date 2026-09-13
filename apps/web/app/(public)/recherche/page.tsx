import { Suspense } from "react";

import { PropertyGridSkeleton } from "@/components/listing/PropertyCardSkeleton";
import { SearchResults } from "@/components/search/SearchResults";
import { serverApi } from "@/lib/api/client";
import type {
  Amenity,
  CitySummary,
  Paginated,
  PropertyCard as PropertyCardData,
} from "@/lib/api/types";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Rechercher un logement vérifié",
  description:
    "Filtrez par ville, quartier, durée, budget et équipements parmi les logements vérifiés par Loka.",
  path: "/recherche",
  noindex: true,
});

type SearchParams = Record<string, string | string[] | undefined>;

function flatten(params: SearchParams): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") out[key] = value;
    else if (Array.isArray(value) && value[0]) out[key] = value.join(",");
  }
  return out;
}

const EMPTY: Paginated<PropertyCardData> = { count: 0, next: null, previous: null, results: [] };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = flatten(await searchParams);
  const query = {
    ...params,
    rental_mode: params.rental_mode ?? "monthly",
    ordering: params.ordering === "newest" ? undefined : params.ordering,
    page_size: 20,
  };
  const [initial, cities, amenities] = await Promise.all([
    serverApi
      .get<Paginated<PropertyCardData>>("/listings/properties/", query, { revalidate: 0 })
      .catch(() => EMPTY),
    serverApi
      .get<Paginated<CitySummary>>("/geo/cities/", { page_size: 50 }, { revalidate: 3600 })
      .then((r) => r.results)
      .catch(() => []),
    serverApi
      .get<Amenity[]>("/listings/amenities/", undefined, { revalidate: 3600 })
      .catch(() => []),
  ]);

  return (
    <Suspense
      fallback={
        <div className="container py-6">
          <PropertyGridSkeleton />
        </div>
      }
    >
      <SearchResults
        initial={initial}
        cities={cities}
        amenities={amenities}
        initialParams={params}
      />
    </Suspense>
  );
}
