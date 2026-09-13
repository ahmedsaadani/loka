"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { CalendarEditor } from "@/components/host/CalendarEditor";
import { PhotoUploader } from "@/components/host/PhotoUploader";
import { PricingEditor } from "@/components/host/PricingEditor";
import { PropertyStatusBadge } from "@/components/host/PropertyStatusBadge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type {
  Amenity,
  CitySummary,
  LatLng,
  NeighborhoodSummary,
  Paginated,
  PropertyHost,
  PropertyType,
  PropertyWrite,
} from "@/lib/api/types";
import { cn, PROPERTY_TYPE_LABEL } from "@/lib/utils";

const LocationPicker = dynamic(
  () => import("@/components/host/LocationPicker").then((m) => m.LocationPicker),
  { ssr: false, loading: () => <div className="h-72 w-full animate-pulse rounded-lg bg-muted" /> },
);

const STEPS = [
  { key: "infos", label: "Informations" },
  { key: "location", label: "Localisation" },
  { key: "photos", label: "Photos" },
  { key: "pricing", label: "Tarifs" },
  { key: "calendar", label: "Calendrier" },
  { key: "publish", label: "Publication" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

const READINESS_LABEL: Record<string, string> = {
  title: "Titre",
  description: "Description",
  address_private: "Adresse exacte",
  location: "Position sur la carte",
  photos: "Photos",
  pricing_plans: "Tarifs",
};

interface InfoForm {
  title: string;
  description: string;
  property_type: PropertyType;
  rooms_label: string;
  bedrooms: number;
  bathrooms: number;
  surface_m2: string;
  floor: string;
  has_elevator: boolean;
  furnished: boolean;
  max_guests: number;
  charges_included: boolean;
  monthly_charges_estimate: string;
  deposit_months: number;
  min_lease_months: number;
  distance_notes: string;
  amenities: string[];
  house_rules: { smoking: boolean; pets: boolean; parties: boolean };
}

function toForm(p: PropertyHost): InfoForm {
  return {
    title: p.title,
    description: p.description,
    property_type: p.property_type,
    rooms_label: p.rooms_label,
    bedrooms: p.bedrooms,
    bathrooms: p.bathrooms,
    surface_m2: p.surface_m2?.toString() ?? "",
    floor: p.floor?.toString() ?? "",
    has_elevator: p.has_elevator,
    furnished: p.furnished,
    max_guests: p.max_guests,
    charges_included: p.charges_included,
    monthly_charges_estimate: p.monthly_charges_estimate ?? "",
    deposit_months: p.deposit_months,
    min_lease_months: p.min_lease_months,
    distance_notes: Object.entries(p.distance_notes)
      .map(([k, v]) => `${k}: ${v}`)
      .join("\n"),
    amenities: p.amenities.map((a) => a.code),
    house_rules: {
      smoking: Boolean(p.house_rules.smoking),
      pets: Boolean(p.house_rules.pets),
      parties: Boolean(p.house_rules.parties),
    },
  };
}

function parseDistances(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const [key, ...rest] = line.split(":");
    if (key && rest.length) out[key.trim()] = rest.join(":").trim();
  }
  return out;
}

function toPayload(f: InfoForm): PropertyWrite {
  return {
    title: f.title,
    description: f.description,
    property_type: f.property_type,
    rooms_label: f.rooms_label,
    bedrooms: f.bedrooms,
    bathrooms: f.bathrooms,
    surface_m2: f.surface_m2 ? Number(f.surface_m2) : null,
    floor: f.floor === "" ? null : Number(f.floor),
    has_elevator: f.has_elevator,
    furnished: f.furnished,
    max_guests: f.max_guests,
    charges_included: f.charges_included,
    monthly_charges_estimate: f.monthly_charges_estimate ? f.monthly_charges_estimate : null,
    deposit_months: f.deposit_months,
    min_lease_months: f.min_lease_months,
    distance_notes: parseDistances(f.distance_notes),
    amenities: f.amenities,
    house_rules: f.house_rules,
  };
}

export function PropertyWizard({ publicId }: { publicId: string }) {
  const router = useRouter();
  const base = `/listings/host/properties/${publicId}`;
  const { data: property, loading, error, refetch } = useApi<PropertyHost>(`${base}/`);
  const amenities = useApi<Amenity[]>("/listings/amenities/");
  const cities = useApi<Paginated<CitySummary>>("/geo/cities/", { page_size: 50 });
  const [step, setStep] = useState<StepKey>("infos");
  const [form, setForm] = useState<InfoForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (property && !form) setForm(toForm(property));
  }, [property, form]);

  const editable = property?.status === "draft" || property?.status === "rejected";

  async function save(payload: PropertyWrite, successMessage = "Enregistré."): Promise<boolean> {
    setSaving(true);
    setFieldErrors({});
    try {
      await api.patch<PropertyHost>(`${base}/`, payload);
      await refetch();
      toast.success(successMessage);
      return true;
    } catch (err) {
      if (err instanceof ApiRequestError) {
        const errors: Record<string, string> = {};
        for (const key of Object.keys(payload)) {
          const message = err.fieldError(key);
          if (message) errors[key] = message;
        }
        setFieldErrors(errors);
        toast.error(err.message);
      } else toast.error("Une erreur est survenue.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function transition(action: "submit" | "withdraw" | "pause" | "resume") {
    setSaving(true);
    try {
      await api.post(`${base}/${action}/`);
      await refetch();
      toast.success(
        {
          submit: "Annonce soumise à validation.",
          withdraw: "Annonce repassée en brouillon.",
          pause: "Annonce mise en pause.",
          resume: "Annonce réactivée.",
        }[action],
      );
      if (action === "submit") setStep("publish");
    } catch (err) {
      if (err instanceof ApiRequestError && err.errors) {
        toast.error(
          `Complétez : ${Object.keys(err.errors)
            .map((k) => READINESS_LABEL[k] ?? k)
            .join(", ")}`,
        );
      } else toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm("Supprimer ce brouillon ?")) return;
    try {
      await api.delete(`${base}/`);
      toast.success("Brouillon supprimé.");
      router.push("/hote/biens");
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    }
  }

  if (loading && !property) return <Skeleton className="h-96 w-full" />;
  if (error || !property || !form) {
    return (
      <div className="rounded-xl border p-6">
        <p>Bien introuvable.</p>
        <Button variant="outline" className="mt-3" asChild>
          <Link href="/hote/biens">Retour à mes biens</Link>
        </Button>
      </div>
    );
  }

  const readiness = Object.entries(property.readiness_errors);
  const currentIndex = STEPS.findIndex((s) => s.key === step);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href="/hote/biens" className="text-sm text-muted-foreground hover:underline">
            ← Mes biens
          </Link>
          <h1 className="mt-1 truncate text-2xl md:text-3xl">{property.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <PropertyStatusBadge status={property.status} />
            {property.status === "published" && (
              <Link
                href={`/logement/${property.slug}`}
                className="text-sm underline"
                target="_blank"
                rel="noopener"
              >
                Voir l&apos;annonce publique
              </Link>
            )}
            {property.status === "rejected" && property.rejection_reason && (
              <span className="text-sm text-destructive">Motif : {property.rejection_reason}</span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {property.status === "pending_review" && (
            <Button variant="outline" onClick={() => transition("withdraw")} disabled={saving}>
              Retirer (brouillon)
            </Button>
          )}
          {property.status === "published" && (
            <Button variant="outline" onClick={() => transition("pause")} disabled={saving}>
              Mettre en pause
            </Button>
          )}
          {property.status === "paused" && (
            <>
              <Button onClick={() => transition("resume")} disabled={saving}>
                Réactiver
              </Button>
              <Button variant="outline" onClick={() => transition("withdraw")} disabled={saving}>
                Modifier (brouillon)
              </Button>
            </>
          )}
          {property.status === "draft" && (
            <Button variant="ghost" className="text-destructive" onClick={remove} disabled={saving}>
              Supprimer
            </Button>
          )}
        </div>
      </div>

      {!editable && (
        <p className="rounded-lg border bg-muted/60 p-3 text-sm text-muted-foreground">
          Cette annonce n&apos;est pas modifiable dans son état actuel. Toute modification passe par
          un retour en brouillon puis une nouvelle validation par Loka.
        </p>
      )}

      <nav className="scrollbar-none flex gap-1 overflow-x-auto" aria-label="Étapes">
        {STEPS.map((s, i) => (
          <button
            key={s.key}
            type="button"
            onClick={() => setStep(s.key)}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1.5 text-sm",
              step === s.key
                ? "border-foreground bg-foreground text-background"
                : "bg-card text-muted-foreground",
            )}
            aria-current={step === s.key ? "step" : undefined}
            data-testid={`wizard-step-${s.key}`}
          >
            {i + 1}. {s.label}
          </button>
        ))}
      </nav>

      {step === "infos" && (
        <InfoStep
          form={form}
          setForm={setForm}
          amenities={amenities.data ?? []}
          errors={fieldErrors}
          disabled={!editable || saving}
          onSave={() => save(toPayload(form))}
        />
      )}

      {step === "location" && (
        <LocationStep
          property={property}
          cities={cities.data?.results ?? []}
          disabled={!editable || saving}
          onSave={(payload) => save(payload)}
          errors={fieldErrors}
        />
      )}

      {step === "photos" && (
        <PhotoUploader
          basePath={base}
          photos={property.photos}
          onChange={refetch}
          disabled={saving}
        />
      )}

      {step === "pricing" && (
        <PricingEditor basePath={base} plans={property.pricing_plans} onChange={refetch} />
      )}

      {step === "calendar" && (
        <CalendarEditor propertyId={property.public_id} slug={property.slug} />
      )}

      {step === "publish" && (
        <section className="space-y-4 rounded-xl border bg-card p-5">
          <h2 className="text-lg">Soumettre à validation</h2>
          {readiness.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-verified">
              <CheckCircle2 className="h-4 w-4" /> L&apos;annonce est complète.
            </p>
          ) : (
            <ul className="space-y-1 text-sm">
              {readiness.map(([key, message]) => (
                <li key={key} className="flex items-start gap-2 text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    <strong>{READINESS_LABEL[key] ?? key}</strong> : {message}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="text-sm text-muted-foreground">
            Après soumission, l&apos;équipe Loka vous contacte pour planifier la visite, prend les
            photos et évalue l&apos;état du bien. L&apos;annonce est publiée après validation.
          </p>
          {(property.status === "draft" || property.status === "rejected") && (
            <Button
              onClick={() => transition("submit")}
              disabled={saving || readiness.length > 0}
              data-testid="wizard-submit"
            >
              Soumettre à validation
            </Button>
          )}
          {property.status === "pending_review" && (
            <p className="text-sm font-medium">Annonce en attente de validation.</p>
          )}
          {property.status === "needs_visit" && (
            <p className="text-sm font-medium">
              Visite planifiée
              {property.visit_scheduled_at
                ? ` le ${new Date(property.visit_scheduled_at).toLocaleString("fr-FR")}`
                : ""}
              .
            </p>
          )}
        </section>
      )}

      <div className="flex justify-between">
        <Button
          variant="outline"
          disabled={currentIndex === 0}
          onClick={() => setStep(STEPS[currentIndex - 1]!.key)}
        >
          Précédent
        </Button>
        <Button
          variant="outline"
          disabled={currentIndex === STEPS.length - 1}
          onClick={() => setStep(STEPS[currentIndex + 1]!.key)}
          data-testid="wizard-next"
        >
          Suivant
        </Button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- étapes

function InfoStep({
  form,
  setForm,
  amenities,
  errors,
  disabled,
  onSave,
}: {
  form: InfoForm;
  setForm: (f: InfoForm) => void;
  amenities: Amenity[];
  errors: Record<string, string>;
  disabled: boolean;
  onSave: () => Promise<boolean>;
}) {
  const set = <K extends keyof InfoForm>(key: K, value: InfoForm[K]) =>
    setForm({ ...form, [key]: value });
  return (
    <form
      className="space-y-5 rounded-xl border bg-card p-5"
      onSubmit={(e) => {
        e.preventDefault();
        void onSave();
      }}
    >
      <Field label="Titre" error={errors.title}>
        <Input
          value={form.title}
          onChange={(e) => set("title", e.target.value)}
          maxLength={140}
          disabled={disabled}
          data-testid="wizard-title"
        />
      </Field>
      <Field label="Description (80 caractères minimum)" error={errors.description}>
        <Textarea
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
          rows={6}
          disabled={disabled}
          data-testid="wizard-description"
        />
        <p className="text-xs text-muted-foreground">{form.description.length} caractères</p>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Type de bien">
          <Select
            value={form.property_type}
            onValueChange={(v) => set("property_type", v as PropertyType)}
            disabled={disabled}
          >
            <SelectTrigger>
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
        </Field>
        <Field label="Pièces (S+1, S+2…)">
          <Input
            value={form.rooms_label}
            onChange={(e) => set("rooms_label", e.target.value)}
            maxLength={8}
            placeholder="S+2"
            disabled={disabled}
          />
        </Field>
        <Field label="Chambres" error={errors.bedrooms}>
          <Input
            type="number"
            min={0}
            max={20}
            value={form.bedrooms}
            onChange={(e) => set("bedrooms", Number(e.target.value))}
            disabled={disabled}
          />
        </Field>
        <Field label="Salles de bain" error={errors.bathrooms}>
          <Input
            type="number"
            min={1}
            max={10}
            value={form.bathrooms}
            onChange={(e) => set("bathrooms", Number(e.target.value))}
            disabled={disabled}
          />
        </Field>
        <Field label="Surface (m²)" error={errors.surface_m2}>
          <Input
            type="number"
            min={5}
            max={2000}
            value={form.surface_m2}
            onChange={(e) => set("surface_m2", e.target.value)}
            disabled={disabled}
          />
        </Field>
        <Field label="Étage (vide si maison)" error={errors.floor}>
          <Input
            type="number"
            min={-1}
            max={50}
            value={form.floor}
            onChange={(e) => set("floor", e.target.value)}
            disabled={disabled}
          />
        </Field>
        <Field label="Voyageurs max." error={errors.max_guests}>
          <Input
            type="number"
            min={1}
            max={20}
            value={form.max_guests}
            onChange={(e) => set("max_guests", Number(e.target.value))}
            disabled={disabled}
          />
        </Field>
      </div>
      <div className="flex flex-wrap gap-4">
        <Check
          label="Ascenseur"
          checked={form.has_elevator}
          onChange={(v) => set("has_elevator", v)}
          disabled={disabled}
        />
        <Check
          label="Meublé"
          checked={form.furnished}
          onChange={(v) => set("furnished", v)}
          disabled={disabled}
        />
        <Check
          label="Charges incluses"
          checked={form.charges_included}
          onChange={(v) => set("charges_included", v)}
          disabled={disabled}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {!form.charges_included && (
          <Field label="Charges estimées (DT / mois)">
            <Input
              type="number"
              min={0}
              value={form.monthly_charges_estimate}
              onChange={(e) => set("monthly_charges_estimate", e.target.value)}
              disabled={disabled}
            />
          </Field>
        )}
        <Field label="Caution (mois de loyer)">
          <Input
            type="number"
            min={0}
            max={3}
            value={form.deposit_months}
            onChange={(e) => set("deposit_months", Number(e.target.value))}
            disabled={disabled}
          />
        </Field>
        <Field label="Durée minimale (mois)">
          <Input
            type="number"
            min={1}
            max={12}
            value={form.min_lease_months}
            onChange={(e) => set("min_lease_months", Number(e.target.value))}
            disabled={disabled}
          />
        </Field>
      </div>
      <Field label="À proximité (une ligne par lieu, « Lieu : distance »)">
        <Textarea
          value={form.distance_notes}
          onChange={(e) => set("distance_notes", e.target.value)}
          rows={3}
          placeholder={"ESPRIT : 8 min à pied\nMétro ligne 2 : 5 min"}
          disabled={disabled}
        />
      </Field>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Équipements</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {amenities.map((a) => (
            <Check
              key={a.code}
              label={a.name}
              checked={form.amenities.includes(a.code)}
              onChange={(v) =>
                set(
                  "amenities",
                  v ? [...form.amenities, a.code] : form.amenities.filter((c) => c !== a.code),
                )
              }
              disabled={disabled}
            />
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Règles</legend>
        <div className="flex flex-wrap gap-4">
          <Check
            label="Fumeurs acceptés"
            checked={form.house_rules.smoking}
            onChange={(v) => set("house_rules", { ...form.house_rules, smoking: v })}
            disabled={disabled}
          />
          <Check
            label="Animaux acceptés"
            checked={form.house_rules.pets}
            onChange={(v) => set("house_rules", { ...form.house_rules, pets: v })}
            disabled={disabled}
          />
          <Check
            label="Fêtes autorisées"
            checked={form.house_rules.parties}
            onChange={(v) => set("house_rules", { ...form.house_rules, parties: v })}
            disabled={disabled}
          />
        </div>
      </fieldset>
      <Button type="submit" disabled={disabled} data-testid="wizard-save-infos">
        Enregistrer
      </Button>
    </form>
  );
}

function LocationStep({
  property,
  cities,
  disabled,
  errors,
  onSave,
}: {
  property: PropertyHost;
  cities: CitySummary[];
  disabled: boolean;
  errors: Record<string, string>;
  onSave: (payload: PropertyWrite) => Promise<boolean>;
}) {
  const [city, setCity] = useState(property.city.slug);
  const [neighborhood, setNeighborhood] = useState(property.neighborhood?.slug ?? "");
  const [address, setAddress] = useState(property.address_private);
  const [precision, setPrecision] = useState(property.location_precision);
  const [location, setLocation] = useState<LatLng | null>(property.location);
  const neighborhoods = useApi<Paginated<NeighborhoodSummary>>(
    city ? "/geo/neighborhoods/" : null,
    { city__slug: city, page_size: 50 },
  );
  const cityCenter = cities.find((c) => c.slug === city)?.centroid ?? null;

  return (
    <form
      className="space-y-5 rounded-xl border bg-card p-5"
      onSubmit={(e) => {
        e.preventDefault();
        void onSave({
          city,
          neighborhood: neighborhood || null,
          address_private: address,
          location,
          location_precision: precision,
        });
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Ville" error={errors.city}>
          <Select
            value={city}
            onValueChange={(v) => {
              setCity(v);
              setNeighborhood("");
            }}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {cities.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Quartier" error={errors.neighborhood}>
          <Select
            value={neighborhood || "none"}
            onValueChange={(v) => setNeighborhood(v === "none" ? "" : v)}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Choisir" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Non précisé</SelectItem>
              {(neighborhoods.data?.results ?? []).map((n) => (
                <SelectItem key={n.slug} value={n.slug}>
                  {n.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
      <Field
        label="Adresse exacte (jamais publiée, utilisée pour la visite et communiquée au voyageur après confirmation)"
        error={errors.address_private}
      >
        <Input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          maxLength={255}
          disabled={disabled}
          data-testid="wizard-address"
        />
      </Field>
      <Field label="Position sur la carte (cliquez pour placer le bien)" error={errors.location}>
        <LocationPicker
          value={location}
          onChange={setLocation}
          center={cityCenter}
          disabled={disabled}
        />
      </Field>
      <Field label="Affichage public de la position">
        <Select
          value={precision}
          onValueChange={(v) => setPrecision(v as "exact" | "approximate")}
          disabled={disabled}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="approximate">Approximative (zone de 100 m, recommandé)</SelectItem>
            <SelectItem value="exact">Exacte</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Button type="submit" disabled={disabled} data-testid="wizard-save-location">
        Enregistrer
      </Button>
    </form>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function Check({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <Checkbox
        checked={checked}
        onCheckedChange={(c) => onChange(c === true)}
        disabled={disabled}
      />
      {label}
    </label>
  );
}
