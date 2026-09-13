import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { PropertyStatus } from "@/lib/api/types";
import { PROPERTY_STATUS_LABEL } from "@/lib/utils";

const VARIANT: Record<PropertyStatus, BadgeProps["variant"]> = {
  draft: "muted",
  pending_review: "secondary",
  needs_visit: "default",
  published: "verified",
  paused: "outline",
  rejected: "destructive",
};

export function PropertyStatusBadge({ status }: { status: PropertyStatus }) {
  return <Badge variant={VARIANT[status]}>{PROPERTY_STATUS_LABEL[status] ?? status}</Badge>;
}
