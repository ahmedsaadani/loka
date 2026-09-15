"use client";

import { Heart } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PropertyCard } from "@/components/listing/PropertyCard";
import { Button } from "@/components/ui/button";
import { PropertyCardSkeleton } from "@/components/listing/PropertyCardSkeleton";
import { api } from "@/lib/api/client";
import type { Paginated, PropertyCard as PropertyCardData } from "@/lib/api/types";
import { useFavorites } from "@/lib/favorites";

export default function FavoritesPage() {
  const { favorites, ready } = useFavorites();
  const [all, setAll] = useState<PropertyCardData[] | null>(null);

  useEffect(() => {
    let active = true;
    api
      .get<Paginated<PropertyCardData>>("/listings/properties/", { page_size: 50 })
      .then((d) => active && setAll(d.results))
      .catch(() => active && setAll([]));
    return () => {
      active = false;
    };
  }, []);

  const loading = !ready || all === null;
  const items = all?.filter((p) => favorites.includes(p.public_id)) ?? [];

  return (
    <div className="container py-8 md:py-12">
      <div className="mb-6 flex items-center gap-3">
        <Heart className="h-6 w-6 fill-primary text-primary" />
        <h1 className="text-2xl md:text-3xl">Mes favoris</h1>
      </div>

      {loading ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <PropertyCardSkeleton key={i} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border bg-card p-10 text-center">
          <Heart className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-4 text-lg font-medium">Aucun favori pour l&apos;instant</p>
          <p className="mt-1 text-muted-foreground">
            Cliquez sur le cœur d&apos;un logement pour le retrouver ici.
          </p>
          <Button asChild className="mt-6">
            <Link href="/recherche">Parcourir les logements</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((property) => (
            <PropertyCard key={property.public_id} property={property} />
          ))}
        </div>
      )}
    </div>
  );
}
