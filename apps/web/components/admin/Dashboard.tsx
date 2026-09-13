"use client";

import Link from "next/link";

import { ErrorNote } from "@/components/admin/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api/hooks";

export interface StaffStats {
  properties: Record<string, number>;
  properties_published: number;
  pending_review: number;
  requests: Record<string, number>;
  requests_this_month: number;
  acceptance_rate: number | null;
  bookings_confirmed: number;
  bookings_this_month: number;
  identity_pending: number;
  leads_new: number;
  hosts: number;
  travelers: number;
}

interface Tile {
  label: string;
  value: string;
  href?: string;
  hint?: string;
}

function buildTiles(s: StaffStats): Tile[] {
  return [
    {
      label: "Biens publiés",
      value: String(s.properties_published),
      href: "/admin/validation?status=published",
    },
    {
      label: "En attente de validation",
      value: String(s.pending_review),
      href: "/admin/validation?status=pending_review",
    },
    {
      label: "Demandes ce mois",
      value: String(s.requests_this_month),
      href: "/admin/reservations",
    },
    {
      label: "Taux d'acceptation",
      value: s.acceptance_rate === null ? "—" : `${Math.round(s.acceptance_rate)} %`,
      hint: s.acceptance_rate === null ? "Pas encore de demande traitée" : undefined,
    },
    {
      label: "Réservations confirmées",
      value: String(s.bookings_confirmed),
      href: "/admin/reservations?tab=bookings&status=confirmed",
      hint: `${s.bookings_this_month} ce mois`,
    },
    { label: "Identités en attente", value: String(s.identity_pending), href: "/admin/identites" },
    { label: "Nouveaux leads", value: String(s.leads_new), href: "/admin/leads?status=new" },
    { label: "Hôtes / voyageurs", value: `${s.hosts} / ${s.travelers}` },
  ];
}

const QUEUES = [
  { href: "/admin/validation", label: "File de validation" },
  { href: "/admin/reservations", label: "Demandes et réservations" },
  { href: "/admin/identites", label: "Identités à vérifier" },
  { href: "/admin/leads", label: "Leads" },
];

export function Dashboard() {
  const { data, error, loading } = useApi<StaffStats>("/staff/stats/");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Tableau de bord</h1>
        <p className="text-sm text-muted-foreground">
          Vue d&apos;ensemble de l&apos;activité Loka.
        </p>
      </div>

      <ErrorNote error={error} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="admin-stats">
        {loading && !data
          ? Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-28 w-full" />)
          : data &&
            buildTiles(data).map((tile) => {
              const body = (
                <Card className="h-full transition-colors hover:bg-accent/40">
                  <CardHeader className="pb-1">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {tile.label}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-semibold tabular-nums">{tile.value}</p>
                    {tile.hint && <p className="text-xs text-muted-foreground">{tile.hint}</p>}
                  </CardContent>
                </Card>
              );
              return tile.href ? (
                <Link key={tile.label} href={tile.href} className="block">
                  {body}
                </Link>
              ) : (
                <div key={tile.label}>{body}</div>
              );
            })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accès rapide</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {QUEUES.map((q) => (
            <Link
              key={q.href}
              href={q.href}
              className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
            >
              {q.label}
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
