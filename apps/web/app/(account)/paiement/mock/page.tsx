"use client";

import { ShieldAlert } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiRequestError } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import { formatTnd } from "@/lib/utils";

interface SignInfo {
  provider_ref: string;
  amount: string;
  currency: string;
  signatures: { succeeded: string; failed: string };
}

/**
 * Page de paiement du prestataire MOCK (développement uniquement).
 * Simule la page de checkout : le bouton appelle le webhook signé de l'API,
 * exactement comme le ferait Konnect / ClicToPay / Flouci en production.
 */
function MockCheckout() {
  const params = useSearchParams();
  const router = useRouter();
  const ref = params.get("ref") ?? "";
  const reference = params.get("reference") ?? "";
  const { data, loading, error } = useApi<SignInfo>(ref ? `/bookings/mock/sign/${ref}/` : null);
  const [busy, setBusy] = useState(false);

  async function complete(outcome: "succeeded" | "failed") {
    if (!data) return;
    setBusy(true);
    try {
      await api.post("/bookings/webhooks/mock/", {
        provider_ref: data.provider_ref,
        outcome,
        amount: data.amount,
        currency: data.currency,
        signature: data.signatures[outcome],
      });
      toast[outcome === "succeeded" ? "success" : "error"](
        outcome === "succeeded" ? "Paiement simulé avec succès." : "Paiement simulé en échec.",
      );
      router.push(
        `/compte/reservations/${reference}?paiement=${outcome === "succeeded" ? "ok" : "annule"}`,
      );
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-dashed bg-muted p-3 text-sm text-muted-foreground">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
        Environnement de test : aucun argent réel n&apos;est débité. En production, cette étape se
        déroule chez le prestataire de paiement.
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Paiement de l&apos;acompte</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading && <p className="text-sm text-muted-foreground">Chargement…</p>}
          {error && (
            <p className="text-sm text-destructive">Paiement introuvable ou accès refusé.</p>
          )}
          {data && (
            <>
              <p className="text-3xl font-semibold">
                {formatTnd(data.amount)}{" "}
                <span className="text-base font-normal text-muted-foreground">{data.currency}</span>
              </p>
              <p className="text-xs text-muted-foreground">Référence : {data.provider_ref}</p>
              <div className="grid gap-2">
                <Button
                  size="lg"
                  onClick={() => complete("succeeded")}
                  disabled={busy}
                  data-testid="mock-pay-success"
                >
                  Simuler un paiement réussi
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => complete("failed")}
                  disabled={busy}
                  data-testid="mock-pay-failure"
                >
                  Simuler un échec
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function MockPaymentPage() {
  return (
    <Suspense>
      <MockCheckout />
    </Suspense>
  );
}
