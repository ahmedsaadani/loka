"use client";

import { MessageSquare } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import type { Conversation } from "@/lib/api/types";

/** Ouvre une conversation avec l'hôte au sujet d'un logement (crée/relance une discussion). */
export function ContactHostButton({ slug, className }: { slug: string; className?: string }) {
  const { status } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  if (status === "anonymous") {
    return (
      <Button
        variant="outline"
        className={className}
        onClick={() => router.push(`/connexion?next=/logement/${slug}`)}
      >
        <MessageSquare className="h-4 w-4" /> Contacter l&apos;hôte
      </Button>
    );
  }

  async function submit() {
    const text = body.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    try {
      const conv = await api.post<Conversation>("/messaging/conversations/", {
        property: slug,
        body: text,
      });
      router.push(`/messages/${conv.public_id}`);
    } catch (e) {
      setError(e instanceof ApiRequestError ? e.message : "Une erreur est survenue.");
      setSending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={className}>
          <MessageSquare className="h-4 w-4" /> Contacter l&apos;hôte
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Contacter l&apos;hôte</DialogTitle>
          <DialogDescription>
            Posez votre question sur le logement, la disponibilité ou les conditions.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Bonjour, votre logement est-il disponible en août ?"
          rows={4}
          maxLength={4000}
          autoFocus
        />
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        <Button onClick={submit} disabled={sending || !body.trim()}>
          {sending ? "Envoi…" : "Envoyer le message"}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
