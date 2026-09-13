"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

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
import { api, ApiRequestError } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { CitySummary, Paginated, PropertyHost, PropertyType } from "@/lib/api/types";
import { PROPERTY_TYPE_LABEL } from "@/lib/utils";

/** Étape 0 : on crée un brouillon minimal, puis l'assistant sauvegarde à chaque étape. */
export default function NewPropertyPage() {
  const router = useRouter();
  const cities = useApi<Paginated<CitySummary>>("/geo/cities/", { page_size: 50 });
  const [title, setTitle] = useState("");
  const [type, setType] = useState<PropertyType>("apartment");
  const [city, setCity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.post<PropertyHost>("/listings/host/properties/", {
        title,
        property_type: type,
        city,
        bedrooms: type === "studio" ? 0 : 1,
        bathrooms: 1,
        max_guests: 2,
      });
      toast.success("Brouillon créé. Complétez les étapes.");
      router.push(`/hote/biens/${created.public_id}`);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? (err.fieldError("title") ?? err.fieldError("city") ?? err.message)
          : "Une erreur est survenue.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-lg space-y-5" noValidate>
      <div>
        <h1 className="text-2xl md:text-3xl">Nouveau bien</h1>
        <p className="text-muted-foreground">
          Commençons par l&apos;essentiel. Vous compléterez le reste étape par étape.
        </p>
      </div>
      <div className="space-y-1">
        <Label htmlFor="np-title">Titre de l&apos;annonce</Label>
        <Input
          id="np-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex. S+2 lumineux à Ghazela, proche ESPRIT"
          minLength={3}
          maxLength={140}
          required
          data-testid="np-title"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="np-type">Type de bien</Label>
        <Select value={type} onValueChange={(v) => setType(v as PropertyType)}>
          <SelectTrigger id="np-type" data-testid="np-type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(PROPERTY_TYPE_LABEL).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="np-city">Ville</Label>
        <Select value={city} onValueChange={setCity}>
          <SelectTrigger id="np-city" data-testid="np-city">
            <SelectValue placeholder="Choisir une ville" />
          </SelectTrigger>
          <SelectContent>
            {(cities.data?.results ?? []).map((c) => (
              <SelectItem key={c.slug} value={c.slug}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <Button
        type="submit"
        size="lg"
        className="w-full"
        disabled={submitting || !title || !city}
        data-testid="np-submit"
      >
        Créer le brouillon
      </Button>
    </form>
  );
}
