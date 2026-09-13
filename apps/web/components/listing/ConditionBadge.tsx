import { Badge } from "@/components/ui/badge";
import { CONDITION_LABEL, cn } from "@/lib/utils";

const DOTS: Record<string, number> = { basic: 1, good: 2, excellent: 3 };

export function ConditionBadge({ grade, className }: { grade: string; className?: string }) {
  const filled = DOTS[grade] ?? 2;
  return (
    <Badge
      variant="muted"
      className={cn("gap-1.5 font-medium", className)}
      title="État du bien évalué par l'équipe Loka"
    >
      <span className="flex items-center gap-0.5" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              i <= filled ? "bg-foreground/70" : "bg-foreground/20",
            )}
          />
        ))}
      </span>
      {CONDITION_LABEL[grade] ?? grade}
    </Badge>
  );
}
