import type { PricingPlan } from "@/lib/api/types";
import { formatEur, formatTnd, RENTAL_MODE_LABEL, RENTAL_MODE_TITLE } from "@/lib/utils";

const ORDER = ["nightly", "monthly", "yearly"] as const;

function durationLabel(plan: PricingPlan): string {
  const unit = plan.rental_mode === "nightly" ? "nuit" : "mois";
  if (plan.rental_mode === "yearly") return "Bail de 12 mois";
  const min = `min. ${plan.min_duration} ${unit}${plan.min_duration > 1 ? "s" : ""}`;
  return plan.max_duration
    ? `${min} · max. ${plan.max_duration} ${unit}${plan.max_duration > 1 ? "s" : ""}`
    : min;
}

export function PricingTabs({ plans }: { plans: PricingPlan[] }) {
  const active = ORDER.map((mode) =>
    plans.find((p) => p.rental_mode === mode && p.is_active),
  ).filter((p): p is PricingPlan => Boolean(p));
  if (active.length === 0) return null;
  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      {active.map((plan) => (
        <div key={plan.rental_mode} className="rounded-xl border bg-card p-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {RENTAL_MODE_TITLE[plan.rental_mode]}
          </dt>
          <dd className="mt-1">
            <span className="text-2xl font-semibold">{formatTnd(plan.price)}</span>
            <span className="text-sm text-muted-foreground">
              {" "}
              / {RENTAL_MODE_LABEL[plan.rental_mode]}
            </span>
            <p className="text-xs text-muted-foreground">
              ≈ {formatEur(plan.price_eur)} · {durationLabel(plan)}
            </p>
          </dd>
        </div>
      ))}
    </dl>
  );
}
