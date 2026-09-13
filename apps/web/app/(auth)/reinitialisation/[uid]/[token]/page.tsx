"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiRequestError, setAccessToken } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import type { AuthResponse } from "@/lib/api/types";
import { t } from "@/lib/i18n";

export default function ResetPasswordPage() {
  const params = useParams<{ uid: string; token: string }>();
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const data = await api.post<AuthResponse>("/auth/password/reset/confirm/", {
        uid: params.uid,
        token: params.token,
        password,
      });
      setAccessToken(data.access);
      await refreshUser();
      toast.success("Mot de passe mis à jour.");
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? (err.fieldError("password") ?? err.fieldError("token") ?? err.message)
          : t.common.error,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <h1 className="text-2xl">Nouveau mot de passe</h1>
      <div className="space-y-1">
        <Label htmlFor="reset-password">{t.auth.password} (10 caractères minimum)</Label>
        <Input
          id="reset-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="reset-confirm">Confirmer le mot de passe</Label>
        <Input
          id="reset-confirm"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
      </div>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <Button type="submit" className="w-full" size="lg" disabled={submitting}>
        Enregistrer
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/mot-de-passe-oublie" className="underline">
          Demander un nouveau lien
        </Link>
      </p>
    </form>
  );
}
