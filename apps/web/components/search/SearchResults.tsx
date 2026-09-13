"use client";

import { List, Map as MapIcon, SlidersHorizontal } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PropertyCard } from "@/components/listing/PropertyCard";
import { PropertyGridSkeleton } from "@/components/listing/PropertyCardSkeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, buildQuery, type Query } from "@/lib/api/client";
import type {
  Amenity,
  CitySummary,
  NeighborhoodSummary,
  Paginated,
  PropertyCard as PropertyCardData,
} from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { cn, RENTAL_MODE_TITLE } from "@/lib/utils";

import { EMPTY_FILTERS, Filters, type FilterValues } from "./Filters";

const MapView = dynamic(() => import("./MapView").then((m) => m.MapView), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-muted" />,
});

interface Props {
  initial: Paginated<PropertyCardData>;
  cities: CitySummary[];
  amenities: Amenity[];
  initialParams: Record<string, string>;
}

const PAGE_SIZE = 20;

function paramsToFilters(params: URLSearchParams | Record<string, string>): FilterValues {
  const get = (key: string) =>
    (params instanceof URLSearchParams ? params.get(key) : params[key]) ?? "";
  return {
    city: get("city"),
    neighborhood: get("neighborhood"),
    rental_mode: get("rental_mode") || "monthly",
    min_price: get("min_price"),
    max_price: get("max_price"),
    property_type: get("property_type") ? get("property_type").split(",") : [],
    bedrooms_min: get("bedrooms_min"),
    guests: get("guests"),
    furnished: get("furnished") === "true",
    amenities: get("amenities") ? get("amenities").split(",") : [],
    start: get("start"),
    end: get("end"),
    ordering: get("ordering") || "newest",
  };
}

export function filtersToQuery(f: FilterValues, extra: Query = {}): Query {
  return {
    city: f.city,
    neighborhood: f.neighborhood,
    rental_mode: f.rental_mode,
    min_price: f.min_price,
    max_price: f.max_price,
    property_type: f.property_type,
    bedrooms_min: f.bedrooms_min,
    guests: f.guests,
    furnished: f.furnished ? "true" : "",
    amenities: f.amenities.join(","),
    start: f.start && f.end ? f.start : "",
    end: f.start && f.end ? f.end : "",
    ordering: f.ordering === "newest" ? "" : f.ordering,
    ...extra,
  };
}

function urlQuery(f: FilterValues, page: number): string {
  return buildQuery({
    ...filtersToQuery(f),
    property_type: f.property_type.join(","),
    page: page > 1 ? page : "",
  });
}

export function SearchResults({ initial, cities, amenities, initialParams }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<FilterValues>(() => paramsToFilters(initialParams));
  const [page, setPage] = useState(Number(initialParams.page ?? "1") || 1);
  const [data, setData] = useState<Paginated<PropertyCardData>>(initial);
  const [loading, setLoading] = useState(false);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "map">("list");
  const [bbox, setBbox] = useState<string>("");
  const [neighborhoods, setNeighborhoods] = useState<NeighborhoodSummary[]>([]);
  const firstRender = useRef(true);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const fitKey = useMemo(() => JSON.stringify({ ...filters, page }), [filters, page]);

  // Quartiers de la ville sélectionnée
  useEffect(() => {
    if (!filters.city) {
      setNeighborhoods([]);
      return;
    }
    api
      .get<Paginated<NeighborhoodSummary>>("/geo/neighborhoods/", {
        city__slug: filters.city,
        page_size: 50,
      })
      .then((r) => setNeighborhoods(r.results))
      .catch(() => setNeighborhoods([]));
  }, [filters.city]);

  // Synchronise l'URL et recharge les résultats
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    router.replace(`${pathname}${urlQuery(filters, page)}`, { scroll: false });
    api
      .get<Paginated<PropertyCardData>>(
        "/listings/properties/",
        filtersToQuery(filters, { page, page_size: PAGE_SIZE, bbox }),
        controller.signal,
      )
      .then(setData)
      .catch(() => undefined)
      .finally(() => setLoading(false));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page, bbox]);

  // Navigation arrière / avant du navigateur
  useEffect(() => {
    const fromUrl = paramsToFilters(searchParams);
    if (JSON.stringify(fromUrl) !== JSON.stringify(filters)) setFilters(fromUrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const updateFilters = useCallback((next: FilterValues) => {
    setBbox("");
    setPage(1);
    setFilters(next);
  }, []);

  const scrollToCard = useCallback((publicId: string) => {
    setHighlighted(publicId);
    setView("list");
    cardRefs.current.get(publicId)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE));
  const cityName = cities.find((c) => c.slug === filters.city)?.name;

  return (
    <div className="container py-4 md:py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl md:text-2xl">
            {cityName ? `Logements vérifiés à ${cityName}` : "Logements vérifiés en Tunisie"}
          </h1>
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {loading ? t.common.loading : `${data.count} ${t.search.results}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Tabs
            value={filters.rental_mode}
            onValueChange={(v) => updateFilters({ ...filters, rental_mode: v })}
          >
            <TabsList>
              {(["nightly", "monthly", "yearly"] as const).map((m) => (
                <TabsTrigger key={m} value={m}>
                  {RENTAL_MODE_TITLE[m]}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <Select
            value={filters.ordering}
            onValueChange={(v) => updateFilters({ ...filters, ordering: v })}
          >
            <SelectTrigger className="w-[160px]" aria-label={t.search.sort}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">{t.search.sortNewest}</SelectItem>
              <SelectItem value="price">{t.search.sortPriceAsc}</SelectItem>
              <SelectItem value="-price">{t.search.sortPriceDesc}</SelectItem>
            </SelectContent>
          </Select>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" className="lg:hidden" data-testid="filters-open">
                <SlidersHorizontal /> {t.search.filters}
              </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto">
              <SheetTitle>{t.search.filters}</SheetTitle>
              <div className="mt-4">
                <Filters
                  values={filters}
                  onChange={updateFilters}
                  onReset={() =>
                    updateFilters({ ...EMPTY_FILTERS, rental_mode: filters.rental_mode })
                  }
                  cities={cities}
                  neighborhoods={neighborhoods}
                  amenities={amenities}
                />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      <div className="mt-4 grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-20 rounded-xl border bg-card p-4">
            <Filters
              values={filters}
              onChange={updateFilters}
              onReset={() => updateFilters({ ...EMPTY_FILTERS, rental_mode: filters.rental_mode })}
              cities={cities}
              neighborhoods={neighborhoods}
              amenities={amenities}
            />
          </div>
        </aside>

        <div className="grid gap-4 xl:grid-cols-[1fr_minmax(320px,42%)]">
          <section aria-label="Résultats" className={cn(view === "map" && "hidden xl:block")}>
            {loading && data.results.length === 0 ? (
              <PropertyGridSkeleton count={4} />
            ) : data.results.length === 0 ? (
              <div className="rounded-xl border bg-card p-8 text-center">
                <p className="font-medium">{t.search.noResults}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t.search.noResultsHint}</p>
                {filters.neighborhood && cityName && (
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => updateFilters({ ...filters, neighborhood: "" })}
                  >
                    Voir tout {cityName}
                  </Button>
                )}
              </div>
            ) : (
              <div className={cn("grid gap-4 sm:grid-cols-2", loading && "opacity-60")}>
                {data.results.map((property, index) => (
                  <div
                    key={property.public_id}
                    ref={(el) => {
                      if (el) cardRefs.current.set(property.public_id, el);
                      else cardRefs.current.delete(property.public_id);
                    }}
                  >
                    <PropertyCard
                      property={property}
                      preferredMode={filters.rental_mode}
                      priority={index < 2}
                      onHover={setHighlighted}
                      highlighted={highlighted === property.public_id}
                    />
                  </div>
                ))}
              </div>
            )}
            {totalPages > 1 && (
              <nav className="mt-6 flex items-center justify-center gap-2" aria-label="Pagination">
                <Button
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  {t.common.previous}
                </Button>
                <span className="text-sm text-muted-foreground">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t.common.next}
                </Button>
              </nav>
            )}
            {filters.city && (
              <p className="mt-6 text-sm text-muted-foreground">
                Guide complet :{" "}
                <Link href={`/location/${filters.city}`} className="underline">
                  louer à {cityName}
                </Link>
              </p>
            )}
          </section>

          <div
            className={cn(
              "xl:sticky xl:top-20 xl:h-[calc(100vh-6rem)]",
              view === "list" && "hidden xl:block",
            )}
          >
            <div className="h-[60vh] overflow-hidden rounded-xl border xl:h-full">
              <MapView
                properties={data.results}
                highlighted={highlighted}
                preferredMode={filters.rental_mode}
                fitKey={fitKey}
                onMarkerClick={scrollToCard}
                onMoveEnd={(b) => {
                  setPage(1);
                  setBbox(b);
                }}
                className="h-full w-full"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="fixed bottom-4 left-1/2 z-30 -translate-x-1/2 xl:hidden">
        <Button
          className="shadow-float"
          onClick={() => setView((v) => (v === "list" ? "map" : "list"))}
          data-testid="toggle-view"
        >
          {view === "list" ? (
            <>
              <MapIcon /> {t.search.map}
            </>
          ) : (
            <>
              <List /> {t.search.list}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
