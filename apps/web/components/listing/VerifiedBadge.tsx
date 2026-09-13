import { BadgeCheck, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { t } from "@/lib/i18n";
import { cn, formatDate } from "@/lib/utils";

interface Props {
  level: "verified" | "selection";
  verifiedAt?: string | null;
  showDate?: boolean;
  className?: string;
}

export function VerifiedBadge({ level, verifiedAt, showDate = false, className }: Props) {
  const selection = level === "selection";
  return (
    <Badge
      variant="verified"
      className={cn("gap-1.5", selection && "bg-primary/10 text-primary", className)}
    >
      {selection ? <Sparkles className="h-3.5 w-3.5" /> : <BadgeCheck className="h-3.5 w-3.5" />}
      {selection ? t.listing.selection : t.listing.verifiedBy}
      {showDate && verifiedAt && (
        <span className="font-normal opacity-80">· {formatDate(verifiedAt)}</span>
      )}
    </Badge>
  );
}
