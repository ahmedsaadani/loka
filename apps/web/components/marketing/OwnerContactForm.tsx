"use client";

import { CheckCircle2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import { t } from "@/lib/i18n";

const PROPERTY_TYPES = [
  { value: "apartment", label: "Appartement (S+1, S+2…)" },
  { value: "studio", label: "Studio" },
  { value: "villa", label: "Villa" },
  { value: "room_in_shared_flat", label: "Chambre en colocation" },
  { value: "other", label: "Autre" },
];

interface FormState {
  name: string;
  phone: string;
  city: string;
  property_type: string;
  message: string;
  website: string; // champ piège (honeypot), jamais affiché
}

const EMPTY: FormState = {
  name: "",
  phone: "",
  city: "",
  property_type: "apartment",
  message: "",
  website: "",
};

/** Formulaire public « Devenir hôte » : crée un lead pour l'équipe (POST /leads/owner-contact/). */
export function OwnerContactForm({ cities }: { cities: string[] }) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const set = (field: keyof FormState) => (value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrors({});
    try {
      await api.post<{ detail: string }>("/leads/owner-contact/", form);
      setDone(true);
    } catch (error) {
      if (error instanceof ApiRequestError) {
        const next: Record<string, string> = {};
        for (const field of ["name", "phone", "city", "property_type", "message"]) {
          const message = error.fieldError(field);
          if (message) next[field] = message;
        }
        setErrors(Object.keys(next).length ? next : { form: error.message });
      } else {
        setErrors({ form: t.common.error });
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div
        className="rounded-xl border border-verified/40 bg-verified-soft p-6"
        role="status"
        data-testid="owner-contact-success"
      >
        <CheckCircle2 className="h-6 w-6 text-verified" aria-hidden="true" />
        <h3 className="mt-3 text-lg font-semibold">{t.becomeHost.successTitle}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{t.becomeHost.successText}</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4" data-testid="owner-contact-form" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t.becomeHost.name} error={errors.name} htmlFor="oc-name">
          <Input
            id="oc-name"
            name="name"
            autoComplete="name"
            required
            maxLength={120}
            value={form.name}
            onChange={(e) => set("name")(e.target.value)}
          />
        </Field>
        <Field label={t.becomeHost.phone} error={errors.phone} htmlFor="oc-phone">
          <Input
            id="oc-phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            placeholder="+216 20 000 000"
            required
            maxLength={32}
            value={form.phone}
            onChange={(e) => set("phone")(e.target.value)}
          />
        </Field>
        <Field label={t.becomeHost.city} error={errors.city} htmlFor="oc-city">
          <Input
            id="oc-city"
            name="city"
            list="oc-cities"
            autoComplete="address-level2"
            required
            maxLength={80}
            value={form.city}
            onChange={(e) => set("city")(e.target.value)}
          />
          <datalist id="oc-cities">
            {cities.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Field>
        <Field label={t.becomeHost.propertyType} error={errors.property_type} htmlFor="oc-type">
          <Select value={form.property_type} onValueChange={set("property_type")}>
            <SelectTrigger id="oc-type" aria-label={t.becomeHost.propertyType}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROPERTY_TYPES.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
      <Field label={t.becomeHost.message} error={errors.message} htmlFor="oc-message">
        <Textarea
          id="oc-message"
          name="message"
          rows={4}
          maxLength={1500}
          placeholder={t.becomeHost.messagePlaceholder}
          value={form.message}
          onChange={(e) => set("message")(e.target.value)}
        />
      </Field>
      {/* Champ piège : invisible pour les personnes, rempli par les robots. */}
      <div
        className="absolute -left-[9999px] top-auto h-px w-px overflow-hidden"
        aria-hidden="true"
      >
        <label htmlFor="oc-website">Site web</label>
        <input
          id="oc-website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={form.website}
          onChange={(e) => set("website")(e.target.value)}
        />
      </div>
      {errors.form && (
        <p className="text-sm text-destructive" role="alert">
          {errors.form}
        </p>
      )}
      <Button type="submit" size="lg" disabled={submitting} className="w-full sm:w-auto">
        {submitting ? t.common.loading : t.becomeHost.submit}
      </Button>
      <p className="text-xs text-muted-foreground">{t.becomeHost.privacy}</p>
    </form>
  );
}

function Field({
  label,
  error,
  htmlFor,
  children,
}: {
  label: string;
  error?: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
