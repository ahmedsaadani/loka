"use client";

import { Plus } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { PropertyStatusBadge } from "@/components/host/PropertyStatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api/hooks";
import type { Paginated, PropertyHost } from "@/lib/api/types";
import { formatDate, formatTnd, RENTAL_MODE_LABEL } from "@/lib/utils";

const STATUS_HELP: Record<string, string> = {
  draft: "Complétez l'annonce puis soumettez-la à validation.",
  pending_review: "Notre équipe examine votre annonce et vous contactera pour la visite.",
  needs_visit: "Visite planifiée : nous prenons les photos et validons l'état du bien.",
  published: "En ligne. Mettez en pause pour la retirer temporairement.",
  paused: "Retirée temporairement. Réactivez-la quand vous voulez.",
  rejected: "Non validée. Corrigez l'annonce et soumettez-la à nouveau.",
};

export default function HostPropertiesPage() {
  const { data, loading } = useApi<Paginated<PropertyHost>>("/listings/host/properties/", {
    page_size: 50,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl md:text-3xl">Mes biens</h1>
        <Button asChild data-testid="host-new-property">
          <Link href="/hote/biens/nouveau">
            <Plus /> Ajouter un bien
          </Link>
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <div className="rounded-xl border border-dashed p-8 text-center">
          <p className="font-medium">Aucun bien pour le moment.</p>
          <Button className="mt-3" asChild>
            <Link href="/hote/biens/nouveau">Créer mon premier bien</Link>
          </Button>
        </div>
      ) : (
        <ul className="space-y-3">
          {data.results.map((p) => {
            const cover =
              p.photos.find((ph) => ph.is_cover && ph.variants.thumb) ??
              p.photos.find((ph) => ph.variants.thumb);
            const plan =
              p.pricing_plans.find((pl) => pl.rental_mode === "monthly") ?? p.pricing_plans[0];
            return (
              <li key={p.public_id} data-testid="host-property-row">
                <Link
                  href={`/hote/biens/${p.public_id}`}
                  className="flex gap-4 rounded-xl border bg-card p-3 shadow-card transition-shadow hover:shadow-float"
                >
                  <div className="relative h-24 w-32 shrink-0 overflow-hidden rounded-lg bg-muted">
                    {cover?.variants.thumb ? (
                      <Image
                        src={cover.variants.thumb}
                        alt=""
                        fill
                        sizes="128px"
                        className="object-cover"
                      />
                    ) : (
                      <span className="grid h-full place-items-center text-xs text-muted-foreground">
                        Sans photo
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate text-base font-semibold">{p.title}</h2>
                      <PropertyStatusBadge status={p.status} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {p.neighborhood ? `${p.neighborhood.name}, ` : ""}
                      {p.city.name} ·{" "}
                      {plan
                        ? `${formatTnd(plan.price)} / ${RENTAL_MODE_LABEL[plan.rental_mode]}`
                        : "Aucun tarif"}{" "}
                      · {p.photos.length} photo(s)
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {STATUS_HELP[p.status]}{" "}
                      {p.status === "rejected" && p.rejection_reason
                        ? `Motif : ${p.rejection_reason}`
                        : ""}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Mis à jour le {formatDate(p.updated_at)}
                    </p>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
