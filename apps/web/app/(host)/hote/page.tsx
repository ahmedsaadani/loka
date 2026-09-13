"use client";

import { CalendarCheck, Home, Inbox, Plus } from "lucide-react";
import Link from "next/link";

import { PropertyStatusBadge } from "@/components/host/PropertyStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/api/auth-context";
import { useApi } from "@/lib/api/hooks";
import type { Booking, BookingRequest, Paginated, PropertyHost } from "@/lib/api/types";
import { formatDate, formatTnd } from "@/lib/utils";

export default function HostDashboardPage() {
  const { user } = useAuth();
  const properties = useApi<Paginated<PropertyHost>>("/listings/host/properties/", {
    page_size: 50,
  });
  const requests = useApi<Paginated<BookingRequest>>("/bookings/host/requests/", {
    status: "pending",
    page_size: 5,
  });
  const bookings = useApi<Paginated<Booking>>("/bookings/host/bookings/", {
    status: "confirmed",
    page_size: 5,
  });

  const props = properties.data?.results ?? [];
  const published = props.filter((p) => p.status === "published").length;
  const inReview = props.filter(
    (p) => p.status === "pending_review" || p.status === "needs_visit",
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl">
            Bonjour {user?.first_name || user?.host_profile?.display_name}
          </h1>
          <p className="text-muted-foreground">
            Vos biens, vos demandes et vos réservations en un coup d&apos;œil.
          </p>
        </div>
        <Button asChild data-testid="host-new-property">
          <Link href="/hote/biens/nouveau">
            <Plus /> Ajouter un bien
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={Home}
          label="Biens publiés"
          value={properties.loading ? null : `${published} / ${props.length}`}
          hint={inReview ? `${inReview} en cours de validation` : undefined}
          href="/hote/biens"
        />
        <Stat
          icon={Inbox}
          label="Demandes en attente"
          value={requests.loading ? null : String(requests.data?.count ?? 0)}
          href="/hote/demandes"
        />
        <Stat
          icon={CalendarCheck}
          label="Réservations confirmées"
          value={bookings.loading ? null : String(bookings.data?.count ?? 0)}
          href="/hote/reservations"
        />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Demandes à traiter</CardTitle>
          <Link href="/hote/demandes" className="text-sm underline">
            Tout voir
          </Link>
        </CardHeader>
        <CardContent>
          {requests.loading ? (
            <Skeleton className="h-16 w-full" />
          ) : requests.data && requests.data.results.length > 0 ? (
            <ul className="divide-y">
              {requests.data.results.map((r) => (
                <li
                  key={r.public_id}
                  className="flex items-center justify-between gap-3 py-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{r.property.title}</p>
                    <p className="text-muted-foreground">
                      {r.traveler.display_name} · {formatDate(r.start_date)} →{" "}
                      {formatDate(r.end_date)} · {formatTnd(r.quoted_total)}
                    </p>
                  </div>
                  <Button size="sm" variant="outline" asChild>
                    <Link href={`/hote/demandes?focus=${r.public_id}`}>Répondre</Link>
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Aucune demande en attente.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Mes biens</CardTitle>
          <Link href="/hote/biens" className="text-sm underline">
            Gérer
          </Link>
        </CardHeader>
        <CardContent>
          {properties.loading ? (
            <Skeleton className="h-16 w-full" />
          ) : props.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center">
              <p className="font-medium">Vous n&apos;avez pas encore de bien.</p>
              <p className="text-sm text-muted-foreground">
                Créez votre première annonce : nous la visitons et la publions.
              </p>
              <Button className="mt-3" asChild>
                <Link href="/hote/biens/nouveau">Créer mon premier bien</Link>
              </Button>
            </div>
          ) : (
            <ul className="divide-y">
              {props.slice(0, 5).map((p) => (
                <li
                  key={p.public_id}
                  className="flex items-center justify-between gap-3 py-3 text-sm"
                >
                  <Link
                    href={`/hote/biens/${p.public_id}`}
                    className="min-w-0 truncate font-medium hover:underline"
                  >
                    {p.title}
                  </Link>
                  <PropertyStatusBadge status={p.status} />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  hint,
  href,
}: {
  icon: typeof Home;
  label: string;
  value: string | null;
  hint?: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border bg-card p-4 shadow-card transition-shadow hover:shadow-float"
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" /> {label}
      </div>
      {value === null ? (
        <Skeleton className="mt-2 h-8 w-16" />
      ) : (
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      )}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </Link>
  );
}
