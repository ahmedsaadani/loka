import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const tnd = new Intl.NumberFormat("fr-TN", { maximumFractionDigits: 0 });
const eur = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function formatTnd(amount: number | string): string {
  return `${tnd.format(Number(amount))} DT`;
}

export function formatEur(amount: number | string): string {
  return eur.format(Number(amount));
}

export const RENTAL_MODE_LABEL: Record<string, string> = {
  nightly: "nuit",
  monthly: "mois",
  yearly: "an",
};

export const RENTAL_MODE_TITLE: Record<string, string> = {
  nightly: "Nuit",
  monthly: "Mois",
  yearly: "Année",
};

export function formatPrice(amount: number | string, mode: string): string {
  return `${formatTnd(amount)} / ${RENTAL_MODE_LABEL[mode] ?? mode}`;
}

export const PROPERTY_TYPE_LABEL: Record<string, string> = {
  studio: "Studio",
  apartment: "Appartement",
  villa: "Villa",
  room_in_shared_flat: "Chambre en colocation",
};

export const CONDITION_LABEL: Record<string, string> = {
  basic: "Simple",
  good: "Bon état",
  excellent: "Excellent état",
};

export const PROPERTY_STATUS_LABEL: Record<string, string> = {
  draft: "Brouillon",
  pending_review: "En attente de validation",
  needs_visit: "Visite à planifier",
  published: "Publié",
  paused: "En pause",
  rejected: "Rejeté",
};

export const REQUEST_STATUS_LABEL: Record<string, string> = {
  pending: "En attente",
  accepted: "Acceptée",
  declined: "Refusée",
  expired: "Expirée",
  cancelled: "Annulée",
};

export const BOOKING_STATUS_LABEL: Record<string, string> = {
  awaiting_deposit: "Acompte en attente",
  confirmed: "Confirmée",
  in_progress: "En cours",
  completed: "Terminée",
  cancelled: "Annulée",
};

export function formatDate(value: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(
    "fr-FR",
    options ?? { day: "numeric", month: "short", year: "numeric" },
  ).format(date);
}

export function toIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addMonths(date: Date, months: number): Date {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return `${count} ${count > 1 ? (plural ?? `${singular}s`) : singular}`;
}
