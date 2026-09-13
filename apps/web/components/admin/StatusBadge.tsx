import { Badge, type BadgeProps } from "@/components/ui/badge";
import type {
  BookingStatus,
  IdentityStatus,
  LeadStatus,
  PropertyStatus,
  RequestStatus,
} from "@/lib/api/types";
import { BOOKING_STATUS_LABEL, PROPERTY_STATUS_LABEL, REQUEST_STATUS_LABEL } from "@/lib/utils";

type Variant = NonNullable<BadgeProps["variant"]>;

export const LEAD_STATUS_LABEL: Record<LeadStatus, string> = {
  new: "Nouveau",
  contacted: "Contacté",
  visit_scheduled: "Visite planifiée",
  converted: "Converti",
  rejected: "Rejeté",
};

export const IDENTITY_STATUS_LABEL: Record<IdentityStatus, string> = {
  pending: "En attente",
  approved: "Approuvé",
  rejected: "Rejeté",
};

export const LEAD_SOURCE_LABEL: Record<string, string> = {
  tayara: "Tayara",
  mubawab: "Mubawab",
  facebook: "Facebook",
  manual: "Manuel",
};

const PROPERTY_VARIANT: Record<PropertyStatus, Variant> = {
  draft: "muted",
  pending_review: "secondary",
  needs_visit: "outline",
  published: "verified",
  paused: "muted",
  rejected: "destructive",
};

const REQUEST_VARIANT: Record<RequestStatus, Variant> = {
  pending: "secondary",
  accepted: "verified",
  declined: "destructive",
  expired: "muted",
  cancelled: "muted",
};

const BOOKING_VARIANT: Record<BookingStatus, Variant> = {
  awaiting_deposit: "secondary",
  confirmed: "verified",
  in_progress: "default",
  completed: "muted",
  cancelled: "destructive",
};

const LEAD_VARIANT: Record<LeadStatus, Variant> = {
  new: "default",
  contacted: "secondary",
  visit_scheduled: "outline",
  converted: "verified",
  rejected: "destructive",
};

const IDENTITY_VARIANT: Record<IdentityStatus, Variant> = {
  pending: "secondary",
  approved: "verified",
  rejected: "destructive",
};

type Props =
  | { kind: "property"; status: PropertyStatus }
  | { kind: "request"; status: RequestStatus }
  | { kind: "booking"; status: BookingStatus }
  | { kind: "lead"; status: LeadStatus }
  | { kind: "identity"; status: IdentityStatus };

function resolve(props: Props): { label: string; variant: Variant } {
  switch (props.kind) {
    case "property":
      return {
        label: PROPERTY_STATUS_LABEL[props.status] ?? props.status,
        variant: PROPERTY_VARIANT[props.status] ?? "muted",
      };
    case "request":
      return {
        label: REQUEST_STATUS_LABEL[props.status] ?? props.status,
        variant: REQUEST_VARIANT[props.status] ?? "muted",
      };
    case "booking":
      return {
        label: BOOKING_STATUS_LABEL[props.status] ?? props.status,
        variant: BOOKING_VARIANT[props.status] ?? "muted",
      };
    case "lead":
      return {
        label: LEAD_STATUS_LABEL[props.status] ?? props.status,
        variant: LEAD_VARIANT[props.status] ?? "muted",
      };
    case "identity":
      return {
        label: IDENTITY_STATUS_LABEL[props.status] ?? props.status,
        variant: IDENTITY_VARIANT[props.status] ?? "muted",
      };
  }
}

/** Badge de statut unifié pour le back-office (biens, demandes, réservations, leads, identités). */
export function StatusBadge(props: Props & { className?: string }) {
  const { label, variant } = resolve(props);
  return (
    <Badge variant={variant} className={props.className} data-status={props.status}>
      {label}
    </Badge>
  );
}
