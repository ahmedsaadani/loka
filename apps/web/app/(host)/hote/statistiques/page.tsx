"use client";

import { BarChart3, CalendarCheck, Home, MessageSquare, Star, Wallet } from "lucide-react";
import type { ReactNode } from "react";

import { useApi } from "@/lib/api/hooks";
import type { HostStats } from "@/lib/api/types";
import { formatTnd } from "@/lib/utils";

function pct(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)} %`;
}

export default function HostStatsPage() {
  const { data, loading } = useApi<HostStats>("/bookings/host/stats/");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl">Statistiques</h1>
        <p className="text-muted-foreground">
          Vue d&apos;ensemble de vos biens, demandes et revenus sur Loka.
        </p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Chargement…</p>}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Card
              icon={<Wallet className="h-5 w-5" />}
              label="Revenus encaissés"
              value={formatTnd(data.revenue_completed)}
              hint="Séjours terminés"
            />
            <Card
              icon={<CalendarCheck className="h-5 w-5" />}
              label="Réservations actives"
              value={data.bookings_active}
              hint={`${data.bookings_completed} terminée(s)`}
            />
            <Card
              icon={<Home className="h-5 w-5" />}
              label="Biens publiés"
              value={data.properties_published}
              hint={`sur ${data.properties_total} au total`}
            />
            <Card
              icon={<MessageSquare className="h-5 w-5" />}
              label="Demandes reçues"
              value={data.requests_total}
              hint={`${data.requests_pending} en attente`}
            />
            <Card
              icon={<BarChart3 className="h-5 w-5" />}
              label="Taux d'acceptation"
              value={pct(data.acceptance_rate)}
              hint={`Réponse : ${pct(data.response_rate)}`}
            />
            <Card
              icon={<Star className="h-5 w-5" />}
              label="Note moyenne"
              value={data.average_rating ? data.average_rating.toFixed(1) : "—"}
              hint={`${data.reviews_total} avis`}
            />
          </div>

          {data.requests_pending > 0 && (
            <p className="rounded-lg border bg-accent/40 p-3 text-sm">
              Vous avez <strong>{data.requests_pending}</strong> demande(s) en attente. Répondez
              vite : un bon taux de réponse rassure les voyageurs.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function Card({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
