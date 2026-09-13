"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import { t } from "@/lib/i18n";

interface Props {
  role: "traveler" | "host";
  next: string | null;
}

export function RegisterForm({ role, next }: Props) {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    display_name: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setErrors({});
    try {
      await register({ ...form, role });
      const target =
        next && next.startsWith("/") && !next.startsWith("//")
          ? next
          : role === "host"
            ? "/hote/biens/nouveau"
            : "/";
      router.push(target);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        const fieldErrors: Record<string, string> = {};
        for (const key of Object.keys(form)) {
          const message = err.fieldError(key);
          if (message) fieldErrors[key] = message;
        }
        const nonField = err.fieldError("non_field_errors");
        setErrors(
          Object.keys(fieldErrors).length ? fieldErrors : { form: nonField ?? err.message },
        );
      } else {
        setErrors({ form: t.common.error });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <h1 className="text-2xl">
        {role === "host" ? "Créer un compte propriétaire" : t.auth.registerTitle}
      </h1>
      {role === "host" && (
        <p className="text-sm text-muted-foreground">
          Décrivez votre bien, nous le visitons, le photographions et le publions.
        </p>
      )}
      <div className="grid grid-cols-2 gap-3">
        <Field
          id="first_name"
          label={t.auth.firstName}
          value={form.first_name}
          onChange={set("first_name")}
          error={errors.first_name}
          autoComplete="given-name"
        />
        <Field
          id="last_name"
          label={t.auth.lastName}
          value={form.last_name}
          onChange={set("last_name")}
          error={errors.last_name}
          autoComplete="family-name"
        />
      </div>
      <Field
        id="email"
        label={t.auth.email}
        type="email"
        value={form.email}
        onChange={set("email")}
        error={errors.email}
        autoComplete="email"
        required
      />
      <Field
        id="phone"
        label={`${t.auth.phone} (${t.common.optional})`}
        type="tel"
        value={form.phone}
        onChange={set("phone")}
        error={errors.phone}
        autoComplete="tel"
      />
      {role === "host" && (
        <Field
          id="display_name"
          label="Nom affiché sur vos annonces"
          value={form.display_name}
          onChange={set("display_name")}
          error={errors.display_name}
        />
      )}
      <Field
        id="password"
        label={`${t.auth.password} (10 caractères minimum)`}
        type="password"
        value={form.password}
        onChange={set("password")}
        error={errors.password}
        autoComplete="new-password"
        required
      />
      {errors.form && (
        <p className="text-sm text-destructive" role="alert">
          {errors.form}
        </p>
      )}
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={submitting}
        data-testid="register-submit"
      >
        {t.auth.submitRegister}
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        En créant un compte vous acceptez les{" "}
        <Link href="/cgu" className="underline">
          conditions d&apos;utilisation
        </Link>
        .
      </p>
      <p className="text-center text-sm text-muted-foreground">
        {t.auth.haveAccount}{" "}
        <Link href="/connexion" className="font-medium text-foreground underline">
          {t.auth.loginTitle}
        </Link>
      </p>
    </form>
  );
}

function Field({
  id,
  label,
  error,
  ...props
}: { id: string; label: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        name={id}
        aria-invalid={Boolean(error)}
        data-testid={`register-${id}`}
        {...props}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
