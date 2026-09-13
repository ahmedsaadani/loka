"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import {
  EmptyNote,
  ErrorNote,
  ListSkeleton,
  Pagination,
  ReasonDialog,
  errorMessage,
  parsePage,
} from "@/components/admin/shared";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { Booking, BookingRequest, Paginated } from "@/lib/api/types";
import {
  BOOKING_STATUS_LABEL,
  formatDate,
  formatTnd,
  RENTAL_MODE_TITLE,
  REQUEST_STATUS_LABEL,
} from "@/lib/utils";

function StaffBookings() {
  const params = useSearchParams();
  const router = useRouter();
  const tab = params.get("tab") === "bookings" ? "bookings" : "requests";
  const status = params.get("status") ?? "";
  const page = parsePage(params.get("page"));
  const [cancelling, setCancelling] = useState<Booking | null>(null);

  const requests = useApi<Paginated<BookingRequest>>(
    tab === "requests" ? "/bookings/staff/requests/" : null,
    { status, page },
  );
  const bookings = useApi<Paginated<Booking>>(
    tab === "bookings" ? "/bookings/staff/bookings/" : null,
    { status, page },
  );

  function setParams(next: Record<string, string>) {
    const sp = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) sp.set(k, v);
      else sp.delete(k);
    }
    router.replace(`/admin/reservations?${sp.toString()}`);
  }

  const statusOptions = tab === "requests" ? REQUEST_STATUS_LABEL : BOOKING_STATUS_LABEL;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl md:text-3xl">Demandes et réservations</h1>
      <div className="flex flex-wrap items-center gap-3">
        <Tabs value={tab} onValueChange={(v) => setParams({ tab: v, status: "", page: "" })}>
          <TabsList>
            <TabsTrigger value="requests">Demandes</TabsTrigger>
            <TabsTrigger value="bookings">Réservations</TabsTrigger>
          </TabsList>
        </Tabs>
        <Select
          value={status || "all"}
          onValueChange={(v) => setParams({ status: v === "all" ? "" : v, page: "" })}
        >
          <SelectTrigger className="w-[220px]" aria-label="Filtrer par statut">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les statuts</SelectItem>
            {Object.entries(statusOptions).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {tab === "requests" && (
        <>
          <ErrorNote error={requests.error} />
          {requests.loading && !requests.data ? (
            <ListSkeleton />
          ) : !requests.data || requests.data.results.length === 0 ? (
            <EmptyNote>Aucune demande.</EmptyNote>
          ) : (
            <ul className="divide-y rounded-xl border bg-card">
              {requests.data.results.map((r) => (
                <li
                  key={r.public_id}
                  className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm"
                >
                  <div className="min-w-0">
                    <Link
                      href={`/logement/${r.property.slug}`}
                      className="font-medium hover:underline"
                    >
                      {r.property.title}
                    </Link>
                    <p className="text-muted-foreground">
                      {r.traveler.display_name} · {RENTAL_MODE_TITLE[r.rental_mode]} ·{" "}
                      {formatDate(r.start_date)} → {formatDate(r.end_date)} ·{" "}
                      {formatTnd(r.quoted_total)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Créée le {formatDate(r.created_at)} · expire le {formatDate(r.expires_at)}
                    </p>
                  </div>
                  <StatusBadge kind="request" status={r.status} />
                </li>
              ))}
            </ul>
          )}
          {requests.data && (
            <Pagination
              page={page}
              hasPrevious={Boolean(requests.data.previous)}
              hasNext={Boolean(requests.data.next)}
              count={requests.data.count}
              onChange={(p) => setParams({ page: String(p) })}
            />
          )}
        </>
      )}

      {tab === "bookings" && (
        <>
          <ErrorNote error={bookings.error} />
          {bookings.loading && !bookings.data ? (
            <ListSkeleton />
          ) : !bookings.data || bookings.data.results.length === 0 ? (
            <EmptyNote>Aucune réservation.</EmptyNote>
          ) : (
            <ul className="divide-y rounded-xl border bg-card">
              {bookings.data.results.map((b) => (
                <li
                  key={b.public_id}
                  className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm"
                >
                  <div className="min-w-0">
                    <Link
                      href={`/logement/${b.property.slug}`}
                      className="font-medium hover:underline"
                    >
                      {b.property.title}
                    </Link>
                    <p className="text-muted-foreground">
                      {b.traveler.display_name} chez {b.host.display_name} ·{" "}
                      {formatDate(b.start_date)} → {formatDate(b.end_date)} · total{" "}
                      {formatTnd(b.total_amount)} · acompte {formatTnd(b.deposit_amount)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Paiements :{" "}
                      {b.payments.length === 0
                        ? "aucun"
                        : b.payments.map((p) => `${p.kind} ${p.status}`).join(", ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge kind="booking" status={b.status} />
                    {(b.status === "awaiting_deposit" || b.status === "confirmed") && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => setCancelling(b)}
                      >
                        Annuler
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          {bookings.data && (
            <Pagination
              page={page}
              hasPrevious={Boolean(bookings.data.previous)}
              hasNext={Boolean(bookings.data.next)}
              count={bookings.data.count}
              onChange={(p) => setParams({ page: String(p) })}
            />
          )}
        </>
      )}

      <ReasonDialog
        open={cancelling !== null}
        onOpenChange={(open) => !open && setCancelling(null)}
        title="Annuler la réservation"
        description="L'acompte du voyageur sera remboursé intégralement (annulation par l'équipe)."
        confirmLabel="Annuler la réservation"
        destructive
        onConfirm={async (reason) => {
          if (!cancelling) return;
          try {
            await api.post(`/bookings/staff/bookings/${cancelling.public_id}/cancel/`, { reason });
            toast.success("Réservation annulée.");
            await bookings.refetch();
          } catch (error) {
            toast.error(errorMessage(error));
          }
        }}
      />
    </div>
  );
}

export default function StaffBookingsPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <StaffBookings />
    </Suspense>
  );
}
