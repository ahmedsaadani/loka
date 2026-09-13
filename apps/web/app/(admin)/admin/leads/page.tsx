"use client";

import { Plus, Upload } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { toast } from "sonner";

import {
  EmptyNote,
  ErrorNote,
  ListSkeleton,
  Pagination,
  ReasonDialog,
  errorMessage,
  parsePage,
} from "@/components/admin/shared";
import { LEAD_SOURCE_LABEL, LEAD_STATUS_LABEL, StatusBadge } from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { CitySummary, Lead, LeadStatus, Paginated, PropertyStaff } from "@/lib/api/types";
import { formatDate, formatTnd } from "@/lib/utils";

const NEXT_STATUSES: Record<LeadStatus, LeadStatus[]> = {
  new: ["contacted", "rejected"],
  contacted: ["visit_scheduled", "converted", "rejected"],
  visit_scheduled: ["converted", "rejected"],
  converted: [],
  rejected: ["new"],
};

function Leads() {
  const params = useSearchParams();
  const router = useRouter();
  const status = params.get("status") ?? "";
  const source = params.get("source") ?? "";
  const city = params.get("city") ?? "";
  const page = parsePage(params.get("page"));
  const { data, loading, error, refetch } = useApi<Paginated<Lead>>("/leads/", {
    status,
    source,
    city__icontains: city,
    page,
  });
  const cities = useApi<Paginated<CitySummary>>("/geo/cities/", { page_size: 50 });

  const [statusTarget, setStatusTarget] = useState<{ lead: Lead; to: LeadStatus } | null>(null);
  const [converting, setConverting] = useState<Lead | null>(null);
  const [creating, setCreating] = useState(false);
  const [notesTarget, setNotesTarget] = useState<Lead | null>(null);
  const importInput = useRef<HTMLInputElement>(null);

  function setParams(next: Record<string, string>) {
    const sp = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) sp.set(k, v);
      else sp.delete(k);
    }
    router.replace(`/admin/leads?${sp.toString()}`);
  }

  async function importFile(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    try {
      const result = await api.upload<{ created: number; skipped: number }>("/leads/import/", fd);
      toast.success(
        `${result.created} lead(s) importé(s), ${result.skipped} ignoré(s) (doublons).`,
      );
      await refetch();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      if (importInput.current) importInput.current.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl">Leads</h1>
          <p className="text-sm text-muted-foreground">
            Biens repérés sur les sites d&apos;annonces, à contacter et convertir.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={importInput}
            type="file"
            accept=".csv,.json,text/csv,application/json"
            className="sr-only"
            onChange={(e) => e.target.files?.[0] && void importFile(e.target.files[0])}
            data-testid="lead-import-input"
          />
          <Button variant="outline" onClick={() => importInput.current?.click()}>
            <Upload /> Importer CSV / JSON
          </Button>
          <Button onClick={() => setCreating(true)} data-testid="lead-new">
            <Plus /> Nouveau lead
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select
          value={status || "all"}
          onValueChange={(v) => setParams({ status: v === "all" ? "" : v, page: "" })}
        >
          <SelectTrigger className="w-[180px]" aria-label="Statut">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les statuts</SelectItem>
            {Object.entries(LEAD_STATUS_LABEL).map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={source || "all"}
          onValueChange={(v) => setParams({ source: v === "all" ? "" : v, page: "" })}
        >
          <SelectTrigger className="w-[160px]" aria-label="Source">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes sources</SelectItem>
            {Object.entries(LEAD_SOURCE_LABEL).map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Ville"
          defaultValue={city}
          className="w-[160px]"
          onBlur={(e) => setParams({ city: e.target.value, page: "" })}
          onKeyDown={(e) =>
            e.key === "Enter" && setParams({ city: (e.target as HTMLInputElement).value, page: "" })
          }
          aria-label="Ville"
        />
      </div>

      <ErrorNote error={error} />
      {loading && !data ? (
        <ListSkeleton />
      ) : !data || data.results.length === 0 ? (
        <EmptyNote>Aucun lead.</EmptyNote>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data.results.map((lead) => (
            <li key={lead.public_id} className="space-y-2 p-4 text-sm" data-testid="lead-row">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium">
                    {lead.title}{" "}
                    {lead.price ? (
                      <span className="text-muted-foreground">· {formatTnd(lead.price)}</span>
                    ) : null}
                  </p>
                  <p className="text-muted-foreground">
                    {LEAD_SOURCE_LABEL[lead.source]} · {lead.city || "ville inconnue"} ·{" "}
                    {lead.phone || "sans téléphone"} · {formatDate(lead.created_at)}
                    {lead.assigned_to_email ? ` · ${lead.assigned_to_email}` : ""}
                  </p>
                  {lead.source_url && (
                    <a
                      href={lead.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs underline"
                    >
                      Voir l&apos;annonce source
                    </a>
                  )}
                  {lead.notes && (
                    <p className="mt-1 whitespace-pre-line rounded bg-muted p-2 text-xs">
                      {lead.notes}
                    </p>
                  )}
                </div>
                <StatusBadge kind="lead" status={lead.status} />
              </div>
              <div className="flex flex-wrap gap-2">
                {NEXT_STATUSES[lead.status].map((to) => (
                  <Button
                    key={to}
                    size="sm"
                    variant="outline"
                    onClick={() => setStatusTarget({ lead, to })}
                  >
                    → {LEAD_STATUS_LABEL[to]}
                  </Button>
                ))}
                {lead.status !== "converted" && lead.status !== "new" && (
                  <Button size="sm" onClick={() => setConverting(lead)} data-testid="lead-convert">
                    Convertir en bien
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => setNotesTarget(lead)}>
                  Notes
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && (
        <Pagination
          page={page}
          hasPrevious={Boolean(data.previous)}
          hasNext={Boolean(data.next)}
          count={data.count}
          onChange={(p) => setParams({ page: String(p) })}
        />
      )}

      <ReasonDialog
        open={statusTarget !== null}
        onOpenChange={(open) => !open && setStatusTarget(null)}
        title={statusTarget ? `Passer en « ${LEAD_STATUS_LABEL[statusTarget.to]} »` : ""}
        label="Note (optionnel)"
        required={false}
        onConfirm={async (note) => {
          if (!statusTarget) return;
          try {
            await api.post(`/leads/${statusTarget.lead.public_id}/status/`, {
              status: statusTarget.to,
              note,
            });
            toast.success("Statut mis à jour.");
            await refetch();
          } catch (err) {
            toast.error(errorMessage(err));
          }
        }}
      />

      <ReasonDialog
        open={notesTarget !== null}
        onOpenChange={(open) => !open && setNotesTarget(null)}
        title="Ajouter une note"
        label="Note"
        onConfirm={async (note) => {
          if (!notesTarget) return;
          try {
            await api.patch(`/leads/${notesTarget.public_id}/`, {
              notes: `${notesTarget.notes}\n${note}`.trim(),
            });
            toast.success("Note ajoutée.");
            await refetch();
          } catch (err) {
            toast.error(errorMessage(err));
          }
        }}
      />

      <ConvertDialog
        lead={converting}
        cities={cities.data?.results ?? []}
        onClose={() => setConverting(null)}
        onDone={refetch}
      />
      <CreateDialog open={creating} onClose={() => setCreating(false)} onDone={refetch} />
    </div>
  );
}

function ConvertDialog({
  lead,
  cities,
  onClose,
  onDone,
}: {
  lead: Lead | null;
  cities: CitySummary[];
  onClose: () => void;
  onDone: () => Promise<void>;
}) {
  const [hostEmail, setHostEmail] = useState("");
  const [city, setCity] = useState("");
  const [busy, setBusy] = useState(false);
  async function convert() {
    if (!lead) return;
    setBusy(true);
    try {
      const prop = await api.post<PropertyStaff>(`/leads/${lead.public_id}/convert/`, {
        host_email: hostEmail,
        city,
      });
      toast.success(`Brouillon créé : ${prop.title}`);
      await onDone();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={lead !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Convertir en brouillon de bien</DialogTitle>
          <DialogDescription>
            Le bien est créé en brouillon, rattaché à un compte propriétaire existant. L&apos;hôte
            complète ensuite l&apos;annonce.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="convert-host">Email du propriétaire (compte hôte existant)</Label>
            <Input
              id="convert-host"
              type="email"
              value={hostEmail}
              onChange={(e) => setHostEmail(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="convert-city">Ville</Label>
            <Select value={city} onValueChange={setCity}>
              <SelectTrigger id="convert-city">
                <SelectValue placeholder="Choisir" />
              </SelectTrigger>
              <SelectContent>
                {cities.map((c) => (
                  <SelectItem key={c.slug} value={c.slug}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={convert} disabled={busy || !hostEmail || !city}>
            Créer le brouillon
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateDialog({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => Promise<void>;
}) {
  const [form, setForm] = useState({
    title: "",
    source: "manual",
    source_url: "",
    price: "",
    city: "",
    phone: "",
    notes: "",
  });
  const [busy, setBusy] = useState(false);
  const set =
    (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [k]: e.target.value });
  async function create() {
    setBusy(true);
    try {
      await api.post("/leads/", { ...form, price: form.price || null });
      toast.success("Lead créé.");
      setForm({
        title: "",
        source: "manual",
        source_url: "",
        price: "",
        city: "",
        phone: "",
        notes: "",
      });
      await onDone();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nouveau lead</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="lead-title">Titre</Label>
            <Input id="lead-title" value={form.title} onChange={set("title")} />
          </div>
          <div className="space-y-1">
            <Label>Source</Label>
            <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(LEAD_SOURCE_LABEL).map(([v, l]) => (
                  <SelectItem key={v} value={v}>
                    {l}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="lead-price">Prix (DT)</Label>
            <Input id="lead-price" type="number" value={form.price} onChange={set("price")} />
          </div>
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="lead-url">URL de l&apos;annonce</Label>
            <Input id="lead-url" type="url" value={form.source_url} onChange={set("source_url")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="lead-city">Ville</Label>
            <Input id="lead-city" value={form.city} onChange={set("city")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="lead-phone">Téléphone</Label>
            <Input id="lead-phone" value={form.phone} onChange={set("phone")} />
          </div>
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="lead-notes">Notes</Label>
            <Textarea id="lead-notes" value={form.notes} onChange={set("notes")} rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={create} disabled={busy || !form.title}>
            Créer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <Leads />
    </Suspense>
  );
}
