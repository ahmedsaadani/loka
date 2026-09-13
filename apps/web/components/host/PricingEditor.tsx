"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiRequestError } from "@/lib/api/client";
import type { PricingPlan, RentalMode } from "@/lib/api/types";
import { RENTAL_MODE_TITLE } from "@/lib/utils";

interface Props {
  basePath: string;
  plans: PricingPlan[];
  onChange: () => Promise<void> | void;
}

const MODES: Array<{ mode: RentalMode; unit: string; help: string }> = [
  {
    mode: "nightly",
    unit: "nuit",
    help: "Frais de service 10 % à la charge du voyageur, ajoutés à son total.",
  },
  {
    mode: "monthly",
    unit: "mois",
    help: "Frais de service 5 % déduits de l'acompte (1 mois de loyer).",
  },
  {
    mode: "yearly",
    unit: "mois (bail de 12 mois)",
    help: "Loyer mensuel pour un engagement d'un an. Frais 3 % déduits de l'acompte.",
  },
];

export function PricingEditor({ basePath, plans, onChange }: Props) {
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="text-lg">Tarifs</h2>
        <p className="text-sm text-muted-foreground">
          Activez un ou plusieurs modes. Les prix sont en dinars (DT), l&apos;équivalent EUR est
          indicatif.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {MODES.map((m) => (
          <PlanForm
            key={m.mode}
            basePath={basePath}
            mode={m.mode}
            unit={m.unit}
            help={m.help}
            plan={plans.find((p) => p.rental_mode === m.mode)}
            onChange={onChange}
          />
        ))}
      </div>
    </section>
  );
}

function PlanForm({
  basePath,
  mode,
  unit,
  help,
  plan,
  onChange,
}: {
  basePath: string;
  mode: RentalMode;
  unit: string;
  help: string;
  plan?: PricingPlan;
  onChange: () => Promise<void> | void;
}) {
  const [enabled, setEnabled] = useState(Boolean(plan?.is_active));
  const [price, setPrice] = useState(plan?.price ?? "");
  const [min, setMin] = useState(String(plan?.min_duration ?? 1));
  const [max, setMax] = useState(plan?.max_duration?.toString() ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (!enabled) {
        if (plan) await api.delete(`${basePath}/pricing/${mode}/`);
      } else {
        await api.post(`${basePath}/pricing/`, {
          rental_mode: mode,
          price,
          min_duration: Number(min) || 1,
          max_duration: max ? Number(max) : null,
          is_active: true,
        });
      }
      await onChange();
      toast.success(`Tarif ${(RENTAL_MODE_TITLE[mode] ?? mode).toLowerCase()} enregistré.`);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? (err.fieldError("price") ?? err.fieldError("max_duration") ?? err.message)
          : "Une erreur est survenue.",
      );
    } finally {
      setSaving(false);
    }
  }

  const id = `plan-${mode}`;
  return (
    <div className="space-y-3 rounded-lg border p-4" data-testid={`plan-${mode}`}>
      <label className="flex items-center gap-2 font-medium">
        <Checkbox
          checked={enabled}
          onCheckedChange={(c) => setEnabled(c === true)}
          data-testid={`plan-${mode}-toggle`}
        />
        {RENTAL_MODE_TITLE[mode]}
      </label>
      <p className="text-xs text-muted-foreground">{help}</p>
      <div className="space-y-1">
        <Label htmlFor={`${id}-price`}>Prix (DT / {unit})</Label>
        <Input
          id={`${id}-price`}
          type="number"
          min={1}
          step="1"
          inputMode="numeric"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          disabled={!enabled}
          data-testid={`plan-${mode}-price`}
        />
      </div>
      {mode !== "yearly" && (
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor={`${id}-min`}>Min. ({mode === "nightly" ? "nuits" : "mois"})</Label>
            <Input
              id={`${id}-min`}
              type="number"
              min={1}
              value={min}
              onChange={(e) => setMin(e.target.value)}
              disabled={!enabled}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${id}-max`}>Max. (vide = aucun)</Label>
            <Input
              id={`${id}-max`}
              type="number"
              min={1}
              value={max}
              onChange={(e) => setMax(e.target.value)}
              disabled={!enabled}
            />
          </div>
        </div>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
      <Button
        type="button"
        size="sm"
        onClick={save}
        disabled={saving || (enabled && !price)}
        data-testid={`plan-${mode}-save`}
      >
        Enregistrer
      </Button>
    </div>
  );
}
