import type { PricingPlan, RentalMode } from "@/lib/api/types";
import { cn, formatEur, formatTnd, RENTAL_MODE_LABEL } from "@/lib/utils";

interface Props {
  plans: PricingPlan[];
  preferredMode?: RentalMode | string;
  size?: "sm" | "lg";
  showEur?: boolean;
  className?: string;
}

const ORDER: RentalMode[] = ["monthly", "nightly", "yearly"];

export function pickPlan(plans: PricingPlan[], preferred?: string): PricingPlan | undefined {
  const active = plans.filter((p) => p.is_active);
  if (preferred) {
    const match = active.find((p) => p.rental_mode === preferred);
    if (match) return match;
  }
  for (const mode of ORDER) {
    const match = active.find((p) => p.rental_mode === mode);
    if (match) return match;
  }
  return active[0];
}

export function PriceTag({ plans, preferredMode, size = "sm", showEur = false, className }: Props) {
  const plan = pickPlan(plans, preferredMode);
  if (!plan)
    return <span className={cn("text-sm text-muted-foreground", className)}>Prix sur demande</span>;
  const others = plans.filter((p) => p.is_active && p.rental_mode !== plan.rental_mode);
  return (
    <div className={cn("flex flex-col", className)}>
      <span className={cn("font-semibold", size === "lg" ? "text-2xl" : "text-base")}>
        {formatTnd(plan.price)}
        <span className="text-sm font-normal text-muted-foreground">
          {" "}
          / {RENTAL_MODE_LABEL[plan.rental_mode]}
        </span>
      </span>
      {plan.rental_mode === "yearly" && plan.monthly_equivalent && (
        <span className="text-xs text-muted-foreground">
          soit {formatTnd(plan.monthly_equivalent)} / mois
        </span>
      )}
      {showEur && (
        <span className="text-xs text-muted-foreground">≈ {formatEur(plan.price_eur)}</span>
      )}
      {others.length > 0 && size === "sm" && (
        <span className="text-xs text-muted-foreground">
          {others
            .map((p) =>
              p.rental_mode === "yearly" && p.monthly_equivalent
                ? `${formatTnd(p.price)} / an (soit ${formatTnd(p.monthly_equivalent)} / mois)`
                : `${formatTnd(p.price)} / ${RENTAL_MODE_LABEL[p.rental_mode]}`,
            )
            .join(" · ")}
        </span>
      )}
    </div>
  );
}
