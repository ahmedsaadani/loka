"use client";

import { Check, Share2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

/** Partage la fiche : API de partage native si disponible, sinon copie du lien. */
export function ShareButton({ title }: { title: string }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = typeof window !== "undefined" ? window.location.href : "";
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    if (nav?.share) {
      try {
        await nav.share({ title: `${title} · Loka`, url });
        return;
      } catch {
        // partage annulé : on ne fait rien
        return;
      }
    }
    try {
      await nav?.clipboard?.writeText(url);
      setCopied(true);
      toast.success("Lien copié");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Impossible de copier le lien");
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={share} className="gap-2">
      {copied ? <Check className="h-4 w-4" /> : <Share2 className="h-4 w-4" />}
      Partager
    </Button>
  );
}
