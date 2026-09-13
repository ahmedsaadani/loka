"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import type { Booking, BookingStatus, SignedUrl } from "@/lib/api/types";
import { BOOKING_STATUS_LABEL, cn, formatDate, formatTnd, RENTAL_MODE_TITLE } from "@/lib/utils";

const VARIANT: Record<BookingStatus, BadgeProps["variant"]> = {
  awaiting_deposit: "default",
  confirmed: "verified",
  in_progress: "verified",
  completed: "muted",
  cancelled: "destructive",
};

export function BookingStatusBadge({ status }: { status: BookingStatus }) {
  return <Badge variant={VARIANT[status]}>{BOOKING_STATUS_LABEL[status]}</Badge>;
}

interface Props {
  bookings: Booking[] | null;
  loading: boolean;
  perspective: "host" | "traveler" | "staff";
  onChange: () => Promise<void> | void;
  focus?: string | null;
}

export function bookingBase(perspective: Props["perspective"]): string {
  return perspective === "host"
    ? "/bookings/host/bookings"
    : perspective === "staff"
      ? "/bookings/staff/bookings"
      : "/bookings/bookings";
}

export function BookingList({ bookings, loading, perspective, onChange, focus }: Props) {
  const [cancelling, setCancelling] = useState<Booking | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  async function cancel() {
    if (!cancelling) return;
    setBusy(true);
    try {
      await api.post(`${bookingBase(perspective)}/${cancelling.public_id}/cancel/`, { reason });
      toast.success("Réservation annulée.");
      setCancelling(null);
      setReason("");
      await onChange();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    } finally {
      setBusy(false);
    }
  }

  async function openContract(booking: Booking) {
    try {
      const signed = await api.get<SignedUrl>(
        `${bookingBase(perspective)}/${booking.public_id}/contract/`,
      );
      window.open(signed.url, "_blank", "noopener");
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Contrat indisponible.");
    }
  }

  if (loading && !bookings) return <Skeleton className="h-40 w-full" />;
  if (!bookings || bookings.length === 0)
    return (
      <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        Aucune réservation.
      </p>
    );

  return (
    <>
      <ul className="space-y-3">
        {bookings.map((b) => {
          const thumb = b.property.cover_photo?.variants.thumb;
          const cancellable = b.status === "awaiting_deposit" || b.status === "confirmed";
          return (
            <li
              key={b.public_id}
              className={cn(
                "rounded-xl border bg-card p-4 shadow-card",
                focus === b.public_id && "ring-2 ring-primary",
              )}
              data-testid="booking-row"
            >
              <div className="flex gap-4">
                <div className="relative hidden h-20 w-28 shrink-0 overflow-hidden rounded-lg bg-muted sm:block">
                  {thumb && (
                    <Image src={thumb} alt="" fill sizes="112px" className="object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      href={
                        perspective === "traveler"
                          ? `/compte/reservations/${b.public_id}`
                          : `/logement/${b.property.slug}`
                      }
                      className="truncate font-semibold hover:underline"
                    >
                      {b.property.title}
                    </Link>
                    <BookingStatusBadge status={b.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {RENTAL_MODE_TITLE[b.rental_mode]} · {formatDate(b.start_date)} →{" "}
                    {formatDate(b.end_date)}
                    {perspective !== "traveler" && ` · ${b.traveler.display_name}`}
                    {perspective !== "host" && ` · hôte : ${b.host.display_name}`}
                  </p>
                  <p className="text-sm">
                    Total <strong>{formatTnd(b.total_amount)}</strong> · acompte{" "}
                    {formatTnd(b.deposit_amount)}
                    {b.fee_payer === "host" && perspective === "host" && (
                      <span className="text-muted-foreground">
                        {" "}
                        · frais Loka {formatTnd(b.platform_fee)}
                      </span>
                    )}
                  </p>
                  {b.status === "cancelled" && b.cancellation_reason && (
                    <p className="text-xs text-muted-foreground">Motif : {b.cancellation_reason}</p>
                  )}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap justify-end gap-2">
                {perspective === "traveler" && b.status === "awaiting_deposit" && (
                  <Button size="sm" asChild data-testid="booking-pay">
                    <Link href={`/compte/reservations/${b.public_id}`}>Payer l&apos;acompte</Link>
                  </Button>
                )}
                {b.has_contract && (
                  <Button size="sm" variant="outline" onClick={() => openContract(b)}>
                    Contrat PDF
                  </Button>
                )}
                {cancellable && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => setCancelling(b)}
                    data-testid="booking-cancel"
                  >
                    Annuler
                  </Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <Dialog open={cancelling !== null} onOpenChange={(open) => !open && setCancelling(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Annuler la réservation</DialogTitle>
            <DialogDescription>
              {perspective === "traveler"
                ? "L'acompte est remboursé si l'annulation intervient au moins 7 jours avant l'arrivée."
                : "L'acompte du voyageur sera intégralement remboursé."}
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={255}
            placeholder="Motif (optionnel)"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelling(null)}>
              Retour
            </Button>
            <Button
              variant="destructive"
              disabled={busy}
              onClick={cancel}
              data-testid="booking-cancel-confirm"
            >
              Confirmer l&apos;annulation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
