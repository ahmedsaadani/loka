"use client";

import { MapPin, Phone } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { BookingList } from "@/components/booking/BookingList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiRequestError } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { Booking, Payment } from "@/lib/api/types";
import { formatDate, formatTnd } from "@/lib/utils";

function BookingDetail() {
  const { id } = useParams<{ id: string }>();
  const paymentResult = useSearchParams().get("paiement");
  const { data: booking, loading, error, refetch } = useApi<Booking>(`/bookings/bookings/${id}/`);
  const [paying, setPaying] = useState(false);

  async function payDeposit() {
    setPaying(true);
    try {
      const payment = await api.post<Payment>(`/bookings/bookings/${id}/pay-deposit/`);
      window.location.assign(payment.checkout_url);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
      setPaying(false);
    }
  }

  if (loading && !booking) return <Skeleton className="h-64 w-full" />;
  if (error || !booking) {
    return (
      <div className="rounded-xl border p-6">
        <p>Réservation introuvable.</p>
        <Button variant="outline" className="mt-3" asChild>
          <Link href="/compte/reservations">Retour</Link>
        </Button>
      </div>
    );
  }

  const succeeded = booking.payments.find((p) => p.kind === "deposit" && p.status === "succeeded");
  const refund = booking.payments.find((p) => p.kind === "refund");

  return (
    <div className="space-y-6">
      <Link href="/compte/reservations" className="text-sm text-muted-foreground hover:underline">
        ← Mes réservations
      </Link>
      {paymentResult === "ok" && booking.status === "awaiting_deposit" && (
        <p className="rounded-lg border bg-accent p-3 text-sm">
          Paiement en cours de confirmation… Actualisez dans quelques secondes.
        </p>
      )}
      {paymentResult === "annule" && (
        <p className="rounded-lg border bg-muted p-3 text-sm">
          Paiement annulé. Vous pouvez réessayer.
        </p>
      )}

      <BookingList bookings={[booking]} loading={false} perspective="traveler" onChange={refetch} />

      {booking.status === "awaiting_deposit" && (
        <Card>
          <CardHeader>
            <CardTitle>Confirmer la réservation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm">
              Réglez l&apos;acompte de <strong>{formatTnd(booking.deposit_amount)}</strong> pour
              confirmer. Le solde (
              {formatTnd(String(Number(booking.total_amount) - Number(booking.deposit_amount)))}) se
              règle directement avec l&apos;hôte.
            </p>
            <Button size="lg" onClick={payDeposit} disabled={paying} data-testid="pay-deposit">
              Payer l&apos;acompte
            </Button>
          </CardContent>
        </Card>
      )}

      {booking.address_private && (
        <Card>
          <CardHeader>
            <CardTitle>Accès au logement</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary" /> {booking.address_private},{" "}
              {booking.property.city}
            </p>
            {booking.host_phone && (
              <p className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-primary" /> {booking.host.display_name} ·{" "}
                <a href={`tel:${booking.host_phone}`} className="underline">
                  {booking.host_phone}
                </a>
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Paiements</CardTitle>
        </CardHeader>
        <CardContent>
          {booking.payments.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun paiement pour le moment.</p>
          ) : (
            <ul className="divide-y text-sm">
              {booking.payments.map((p) => (
                <li key={p.public_id} className="flex justify-between py-2">
                  <span>
                    {{ deposit: "Acompte", balance: "Solde", refund: "Remboursement" }[p.kind]} ·{" "}
                    {formatDate(p.created_at)}
                  </span>
                  <span className={p.status === "failed" ? "text-destructive" : ""}>
                    {formatTnd(p.amount)} ·{" "}
                    {
                      {
                        initiated: "en cours",
                        succeeded: "réussi",
                        failed: "échoué",
                        refunded: "remboursé",
                      }[p.status]
                    }
                  </span>
                </li>
              ))}
            </ul>
          )}
          {succeeded && refund && (
            <p className="mt-2 text-xs text-muted-foreground">
              Acompte remboursé le {formatDate(refund.created_at)}.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function BookingDetailPage() {
  return (
    <Suspense>
      <BookingDetail />
    </Suspense>
  );
}
