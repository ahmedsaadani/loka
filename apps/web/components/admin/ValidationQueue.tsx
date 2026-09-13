"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

import {
  EmptyNote,
  ErrorNote,
  ListSkeleton,
  Pagination,
  parsePage,
} from "@/components/admin/shared";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/lib/api/hooks";
import type { Paginated, PropertyStaff, PropertyStatus } from "@/lib/api/types";
import { PROPERTY_STATUS_LABEL, formatDate } from "@/lib/utils";

const STATUSES: PropertyStatus[] = [
  "pending_review",
  "needs_visit",
  "published",
  "paused",
  "rejected",
  "draft",
];

function isStatus(value: string | null): value is PropertyStatus {
  return STATUSES.includes(value as PropertyStatus);
}

export function ValidationQueue() {
  const router = useRouter();
  const params = useSearchParams();
  const rawStatus = params.get("status");
  const status: PropertyStatus = isStatus(rawStatus) ? rawStatus : "pending_review";
  const page = parsePage(params.get("page"));

  const { data, error, loading } = useApi<Paginated<PropertyStaff>>("/listings/staff/properties/", {
    status,
    page,
  });

  const navigate = useCallback(
    (next: { status?: PropertyStatus; page?: number }) => {
      const sp = new URLSearchParams();
      sp.set("status", next.status ?? status);
      const p = next.page ?? 1;
      if (p > 1) sp.set("page", String(p));
      router.push(`/admin/validation?${sp.toString()}`);
    },
    [router, status],
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Validation des biens</h1>
        <p className="text-sm text-muted-foreground">
          Biens à vérifier, visiter et publier par l&apos;équipe.
        </p>
      </div>

      <Tabs value={status} onValueChange={(v) => navigate({ status: v as PropertyStatus })}>
        <TabsList className="h-auto flex-wrap justify-start">
          {STATUSES.map((s) => (
            <TabsTrigger key={s} value={s}>
              {PROPERTY_STATUS_LABEL[s]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <ErrorNote error={error} />

      {loading && !data ? (
        <ListSkeleton />
      ) : data && data.results.length === 0 ? (
        <EmptyNote>Aucun bien dans cet état.</EmptyNote>
      ) : (
        <ul className="divide-y rounded-md border bg-card">
          {data?.results.map((p) => (
            <li key={p.public_id} data-testid="validation-row">
              <Link
                href={`/admin/biens/${p.public_id}`}
                className="flex flex-col gap-1 p-4 hover:bg-accent/40 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="truncate font-medium">{p.title || "Sans titre"}</p>
                  <p className="text-xs text-muted-foreground">
                    {p.city.name}
                    {p.neighborhood ? ` · ${p.neighborhood.name}` : ""} · {p.host_email} ·{" "}
                    {p.photos.length} photo{p.photos.length > 1 ? "s" : ""}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Mis à jour le {formatDate(p.updated_at)}
                    {p.visit_scheduled_at &&
                      ` · Visite le ${formatDate(p.visit_scheduled_at, {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}`}
                  </p>
                </div>
                <StatusBadge kind="property" status={p.status} className="shrink-0" />
              </Link>
            </li>
          ))}
        </ul>
      )}

      {data && (
        <Pagination
          page={page}
          hasPrevious={Boolean(data.previous)}
          hasNext={Boolean(data.next)}
          count={data.count}
          onChange={(p) => navigate({ page: p })}
        />
      )}
    </div>
  );
}
