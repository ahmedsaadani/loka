"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiRequestError } from "@/lib/api/client";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { useAuth } from "@/lib/api/auth-context";
import { t } from "@/lib/i18n";

function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export function LoginForm({ next }: { next: string | null }) {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email, password);
      const target = safeNext(next);
      router.push(
        target !== "/"
          ? target
          : user.role === "host"
            ? "/hote"
            : user.role === "staff" || user.role === "admin"
              ? "/admin"
              : "/",
      );
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiRequestError && err.status === 429
          ? "Trop de tentatives, réessayez dans une minute."
          : t.auth.error,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <h1 className="text-2xl">{t.auth.loginTitle}</h1>
      <div className="space-y-1">
        <Label htmlFor="login-email">{t.auth.email}</Label>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          data-testid="login-email"
        />
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <Label htmlFor="login-password">{t.auth.password}</Label>
          <Link
            href="/mot-de-passe-oublie"
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            {t.auth.forgot}
          </Link>
        </div>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          data-testid="login-password"
        />
      </div>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={submitting}
        data-testid="login-submit"
      >
        {t.auth.submitLogin}
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        {t.auth.noAccount}{" "}
        <Link
          href={`/inscription${next ? `?next=${encodeURIComponent(next)}` : ""}`}
          className="font-medium text-foreground underline"
        >
          {t.auth.registerTitle}
        </Link>
      </p>
      <div className="flex items-center gap-3 py-1 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" /> ou <span className="h-px flex-1 bg-border" />
      </div>
      <GoogleButton />
    </form>
  );
}
