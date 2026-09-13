"use client";

import { RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { AvailabilityCalendar } from "@/components/listing/AvailabilityCalendar";
import { Badge } from "@/components/ui/badge";
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
import type { AvailabilityBlock, ExternalCalendar } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

const KIND_LABEL: Record<AvailabilityBlock["kind"], string> = {
  booked: "Réservation",
  blocked_by_host: "Bloqué par vous",
  external_ical: "Calendrier externe",
  maintenance: "Maintenance",
};

export function CalendarEditor({ propertyId, slug }: { propertyId: string; slug: string }) {
  const base = `/availability/host/properties/${propertyId}`;
  const blocks = useApi<AvailabilityBlock[]>(`${base}/blocks/`);
  const calendars = useApi<ExternalCalendar[]>(`${base}/calendars/`);
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const [note, setNote] = useState("");
  const [icalUrl, setIcalUrl] = useState("");
  const [source, setSource] = useState<ExternalCalendar["source"]>("airbnb");
  const [busy, setBusy] = useState(false);
  const [calendarKey, setCalendarKey] = useState(0);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    try {
      await action();
      await Promise.all([blocks.refetch(), calendars.refetch()]);
      setCalendarKey((k) => k + 1);
      toast.success(success);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-4 rounded-xl border bg-card p-5">
        <div>
          <h2 className="text-lg">Bloquer des dates</h2>
          <p className="text-sm text-muted-foreground">
            Sélectionnez une période dans le calendrier pour la rendre indisponible (travaux, usage
            personnel…).
          </p>
        </div>
        <AvailabilityCalendar
          key={calendarKey}
          slug={slug}
          selection={range ?? undefined}
          onSelect={setRange}
        />
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_2fr_auto] sm:items-end">
          <div className="space-y-1">
            <Label>Début</Label>
            <Input
              type="date"
              value={range?.start ?? ""}
              onChange={(e) => setRange({ start: e.target.value, end: range?.end ?? "" })}
            />
          </div>
          <div className="space-y-1">
            <Label>Fin (exclue)</Label>
            <Input
              type="date"
              value={range?.end ?? ""}
              onChange={(e) => setRange({ start: range?.start ?? "", end: e.target.value })}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="block-note">Note ({"optionnel"})</Label>
            <Input
              id="block-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={160}
            />
          </div>
          <Button
            disabled={busy || !range?.start || !range?.end}
            onClick={() =>
              run(async () => {
                await api.post(`${base}/blocks/`, { start: range!.start, end: range!.end, note });
                setRange(null);
                setNote("");
              }, "Dates bloquées.")
            }
            data-testid="block-dates"
          >
            Bloquer
          </Button>
        </div>
        <ul className="divide-y text-sm">
          {(blocks.data ?? []).map((b) => (
            <li key={b.id} className="flex items-center justify-between gap-3 py-2">
              <span>
                {formatDate(b.start)} → {formatDate(b.end)}{" "}
                <Badge variant={b.kind === "booked" ? "verified" : "muted"}>
                  {KIND_LABEL[b.kind]}
                </Badge>
                {b.note && <span className="text-muted-foreground"> · {b.note}</span>}
              </span>
              {b.kind === "blocked_by_host" && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  aria-label="Débloquer"
                  disabled={busy}
                  onClick={() =>
                    run(() => api.delete(`${base}/blocks/${b.id}/`), "Période débloquée.")
                  }
                >
                  <Trash2 />
                </Button>
              )}
            </li>
          ))}
          {blocks.data && blocks.data.length === 0 && (
            <li className="py-2 text-muted-foreground">Aucune indisponibilité à venir.</li>
          )}
        </ul>
      </section>

      <section className="space-y-4 rounded-xl border bg-card p-5">
        <div>
          <h2 className="text-lg">Calendriers externes (iCal)</h2>
          <p className="text-sm text-muted-foreground">
            Importez vos réservations Airbnb ou Booking pour éviter les doublons. Synchronisation
            automatique toutes les heures.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-[1fr_3fr_auto] sm:items-end">
          <div className="space-y-1">
            <Label>Source</Label>
            <Select
              value={source}
              onValueChange={(v) => setSource(v as ExternalCalendar["source"])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="airbnb">Airbnb</SelectItem>
                <SelectItem value="booking">Booking.com</SelectItem>
                <SelectItem value="other">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="ical-url">URL iCal (https)</Label>
            <Input
              id="ical-url"
              type="url"
              placeholder="https://…/calendar.ics"
              value={icalUrl}
              onChange={(e) => setIcalUrl(e.target.value)}
            />
          </div>
          <Button
            disabled={busy || !icalUrl.startsWith("https://")}
            onClick={() =>
              run(async () => {
                await api.post(`${base}/calendars/`, { ical_url: icalUrl, source });
                setIcalUrl("");
              }, "Calendrier ajouté, synchronisation lancée.")
            }
          >
            Ajouter
          </Button>
        </div>
        <ul className="divide-y text-sm">
          {(calendars.data ?? []).map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 py-2">
              <span className="min-w-0">
                <span className="font-medium capitalize">{c.source}</span>{" "}
                <span className="truncate text-muted-foreground">{c.ical_url}</span>
                <br />
                <span className="text-xs text-muted-foreground">
                  {c.last_synced_at
                    ? `Synchronisé le ${formatDate(c.last_synced_at)}`
                    : "Jamais synchronisé"}
                  {c.last_error ? ` · Erreur : ${c.last_error}` : ""}
                </span>
              </span>
              <span className="flex gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  aria-label="Resynchroniser"
                  disabled={busy}
                  onClick={() =>
                    run(() => api.post(`${base}/calendars/${c.id}/`), "Synchronisation lancée.")
                  }
                >
                  <RefreshCw />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  aria-label="Supprimer"
                  disabled={busy}
                  onClick={() =>
                    run(() => api.delete(`${base}/calendars/${c.id}/`), "Calendrier supprimé.")
                  }
                >
                  <Trash2 />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
