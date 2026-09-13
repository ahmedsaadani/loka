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
import type { BookingRequest, RequestStatus } from "@/lib/api/types";
import { cn, formatDate, formatTnd, RENTAL_MODE_TITLE, REQUEST_STATUS_LABEL } from "@/lib/utils";

const VARIANT: Record<RequestStatus, BadgeProps["variant"]> = {
  pending: "default",
  accepted: "verified",
  declined: "destructive",
  expired: "muted",
  cancelled: "muted",
};

export function RequestStatusBadge({ status }: { status: RequestStatus }) {
  return <Badge variant={VARIANT[status]}>{REQUEST_STATUS_LABEL[status]}</Badge>;
}

interface Props {
  requests: BookingRequest[] | null;
  loading: boolean;
  /** "host" : accepter / refuser ; "traveler" : annuler + lien vers la réservation */
  perspective: "host" | "traveler";
  onChange: () => Promise<void> | void;
  focus?: string | null;
}

export function RequestList({ requests, loading, perspective, onChange, focus }: Props) {
  const [declining, setDeclining] = useState<BookingRequest | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function act(
    request: BookingRequest,
    action: "accept" | "decline" | "cancel",
    body?: unknown,
  ) {
    setBusy(request.public_id);
    try {
      const prefix = perspective === "host" ? "/bookings/host/requests" : "/bookings/requests";
      await api.post(`${prefix}/${request.public_id}/${action}/`, body);
      toast.success(
        {
          accept: "Demande acceptée. Le voyageur est invité à payer l'acompte.",
          decline: "Demande refusée.",
          cancel: "Demande annulée.",
        }[action],
      );
      setDeclining(null);
      setReason("");
      await onChange();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    } finally {
      setBusy(null);
    }
  }

  if (loading && !requests) return <Skeleton className="h-40 w-full" />;
  if (!requests || requests.length === 0)
    return (
      <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        Aucune demande.
      </p>
    );

  return (
    <>
      <ul className="space-y-3">
        {requests.map((r) => {
          const thumb = r.property.cover_photo?.variants.thumb;
          const expiresSoon =
            r.status === "pending" &&
            new Date(r.expires_at).getTime() - Date.now() < 12 * 3600 * 1000;
          return (
            <li
              key={r.public_id}
              className={cn(
                "rounded-xl border bg-card p-4 shadow-card",
                focus === r.public_id && "ring-2 ring-primary",
              )}
              data-testid="request-row"
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
                      href={`/logement/${r.property.slug}`}
                      className="truncate font-semibold hover:underline"
                    >
                      {r.property.title}
                    </Link>
                    <RequestStatusBadge status={r.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {RENTAL_MODE_TITLE[r.rental_mode]} · {formatDate(r.start_date)} →{" "}
                    {formatDate(r.end_date)} · {r.guests} voyageur(s)
                    {perspective === "host" &&
                      ` · ${r.traveler.display_name}${r.traveler.is_identity_verified ? " ✓" : ""}`}
                  </p>
                  <p className="text-sm">
                    Total <strong>{formatTnd(r.quoted_total)}</strong> · acompte{" "}
                    {formatTnd(r.quoted_deposit)}
                    {perspective === "host" &&
                      Number(r.quoted_fee) > 0 &&
                      r.rental_mode !== "nightly" && (
                        <span className="text-muted-foreground">
                          {" "}
                          · frais Loka {formatTnd(r.quoted_fee)} déduits de l&apos;acompte
                        </span>
                      )}
                  </p>
                  {r.message && (
                    <p className="rounded-md bg-muted p-2 text-sm italic">« {r.message} »</p>
                  )}
                  {r.status === "pending" && (
                    <p
                      className={cn(
                        "text-xs",
                        expiresSoon ? "text-destructive" : "text-muted-foreground",
                      )}
                    >
                      Expire le{" "}
                      {formatDate(r.expires_at, {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  )}
                  {r.status === "declined" && r.decline_reason && (
                    <p className="text-xs text-muted-foreground">Motif : {r.decline_reason}</p>
                  )}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap justify-end gap-2">
                {perspective === "host" && r.status === "pending" && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={busy === r.public_id}
                      onClick={() => setDeclining(r)}
                      data-testid="request-decline"
                    >
                      Refuser
                    </Button>
                    <Button
                      size="sm"
                      disabled={busy === r.public_id}
                      onClick={() => act(r, "accept")}
                      data-testid="request-accept"
                    >
                      Accepter
                    </Button>
                  </>
                )}
                {perspective === "traveler" && r.status === "pending" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy === r.public_id}
                    onClick={() => act(r, "cancel")}
                  >
                    Retirer ma demande
                  </Button>
                )}
                {r.booking_public_id && (
                  <Button size="sm" asChild data-testid="request-booking-link">
                    <Link
                      href={
                        perspective === "host"
                          ? `/hote/reservations?focus=${r.booking_public_id}`
                          : `/compte/reservations/${r.booking_public_id}`
                      }
                    >
                      {perspective === "traveler" && r.status === "accepted"
                        ? "Payer l'acompte"
                        : "Voir la réservation"}
                    </Link>
                  </Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <Dialog open={declining !== null} onOpenChange={(open) => !open && setDeclining(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Refuser la demande</DialogTitle>
            <DialogDescription>
              Le voyageur sera informé par email. Vous pouvez indiquer un motif (optionnel).
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={255}
            placeholder="Ex. dates déjà prises hors plateforme"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeclining(null)}>
              Annuler
            </Button>
            <Button
              variant="destructive"
              disabled={busy !== null}
              onClick={() => declining && act(declining, "decline", { reason })}
              data-testid="request-decline-confirm"
            >
              Refuser
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
