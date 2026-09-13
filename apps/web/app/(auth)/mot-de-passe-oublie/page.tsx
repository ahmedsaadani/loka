"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import { t } from "@/lib/i18n";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/auth/password/reset/", { email });
    } catch {
      // Réponse identique quel que soit le compte : on n'affiche pas d'erreur.
    } finally {
      setSent(true);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <h1 className="text-2xl">Mot de passe oublié</h1>
      {sent ? (
        <p className="text-sm text-muted-foreground" role="status">
          Si un compte existe pour <strong>{email}</strong>, un email avec un lien de
          réinitialisation vient de partir. Le lien est valable une heure.
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Indiquez votre email, nous vous envoyons un lien pour choisir un nouveau mot de passe.
          </p>
          <div className="space-y-1">
            <Label htmlFor="forgot-email">{t.auth.email}</Label>
            <Input
              id="forgot-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full" size="lg" disabled={submitting || !email}>
            Envoyer le lien
          </Button>
        </>
      )}
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/connexion" className="underline">
          {t.common.back} à la connexion
        </Link>
      </p>
    </form>
  );
}
