"use client";

import { useState } from "react";
import { toast } from "sonner";

import { ReasonDialog, errorMessage } from "@/components/admin/shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import type { ConditionGrade, PropertyStaff, VerificationLevel } from "@/lib/api/types";
import { CONDITION_LABEL } from "@/lib/utils";

interface Props {
  property: PropertyStaff;
  onDone: () => Promise<void>;
}

type DialogKind = "visit" | "review" | "publish" | "reject" | null;

const VERIFICATION_LABEL: Record<VerificationLevel, string> = {
  verified: "Vérifié par Loka",
  selection: "Sélection Loka",
};

/** Panneau d'actions staff : visite, renvoi en validation, publication, rejet. */
export function PropertyActions({ property, onDone }: Props) {
  const base = `/listings/staff/properties/${property.public_id}`;
  const [open, setOpen] = useState<DialogKind>(null);
  const [busy, setBusy] = useState(false);

  const [visitAt, setVisitAt] = useState("");
  const [visitNote, setVisitNote] = useState("");

  const [level, setLevel] = useState<VerificationLevel>(property.verification_level);
  const [grade, setGrade] = useState<ConditionGrade>(property.condition_grade);
  const [publishNotes, setPublishNotes] = useState("");

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    try {
      await action();
      toast.success(success);
      setOpen(null);
      await onDone();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const scheduleVisit = () =>
    run(
      () =>
        api.post(`${base}/schedule-visit/`, {
          visit_at: new Date(visitAt).toISOString(),
          note: visitNote,
        }),
      "Visite planifiée.",
    );

  const publish = () =>
    run(
      () =>
        api.post(`${base}/publish/`, {
          verification_level: level,
          condition_grade: grade,
          notes: publishNotes,
        }),
      "Bien publié.",
    );

  const hasReadinessErrors = Object.keys(property.readiness_errors ?? {}).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Actions</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          onClick={() => setOpen("visit")}
          data-testid="admin-schedule-visit"
        >
          Planifier une visite
        </Button>
        <Button variant="outline" onClick={() => setOpen("review")}>
          Renvoyer en validation
        </Button>
        <Button
          onClick={() => setOpen("publish")}
          data-testid="admin-publish"
          title={hasReadinessErrors ? "Des prérequis sont manquants" : undefined}
        >
          Publier
        </Button>
        <Button variant="destructive" onClick={() => setOpen("reject")} data-testid="admin-reject">
          Rejeter
        </Button>
      </CardContent>

      <Dialog open={open === "visit"} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Planifier une visite</DialogTitle>
            <DialogDescription>
              Le bien passe en « Visite à planifier » et l&apos;hôte est informé.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="visit-at">Date et heure</Label>
              <Input
                id="visit-at"
                type="datetime-local"
                value={visitAt}
                onChange={(e) => setVisitAt(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="visit-note">Note (optionnel)</Label>
              <Textarea
                id="visit-note"
                value={visitNote}
                onChange={(e) => setVisitNote(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(null)} disabled={busy}>
              Annuler
            </Button>
            <Button onClick={scheduleVisit} disabled={busy || !visitAt}>
              {busy ? "En cours…" : "Planifier"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ReasonDialog
        open={open === "review"}
        onOpenChange={(o) => !o && setOpen(null)}
        title="Renvoyer en validation"
        description="Le bien repasse dans la file « En attente de validation »."
        label="Note (optionnel)"
        required={false}
        confirmLabel="Renvoyer"
        onConfirm={(note) =>
          run(() => api.post(`${base}/back-to-review/`, { note }), "Bien renvoyé en validation.")
        }
      />

      <Dialog open={open === "publish"} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Publier le bien</DialogTitle>
            <DialogDescription>
              Le bien devient visible publiquement avec le niveau de vérification choisi.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="publish-level">Niveau de vérification</Label>
              <Select value={level} onValueChange={(v) => setLevel(v as VerificationLevel)}>
                <SelectTrigger id="publish-level">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(VERIFICATION_LABEL) as VerificationLevel[]).map((v) => (
                    <SelectItem key={v} value={v}>
                      {VERIFICATION_LABEL[v]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="publish-grade">État du bien</Label>
              <Select value={grade} onValueChange={(v) => setGrade(v as ConditionGrade)}>
                <SelectTrigger id="publish-grade">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(["basic", "good", "excellent"] as ConditionGrade[]).map((g) => (
                    <SelectItem key={g} value={g}>
                      {CONDITION_LABEL[g]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="publish-notes">Notes internes</Label>
              <Textarea
                id="publish-notes"
                value={publishNotes}
                onChange={(e) => setPublishNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(null)} disabled={busy}>
              Annuler
            </Button>
            <Button onClick={publish} disabled={busy} data-testid="admin-publish-confirm">
              {busy ? "Publication…" : "Confirmer la publication"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ReasonDialog
        open={open === "reject"}
        onOpenChange={(o) => !o && setOpen(null)}
        title="Rejeter le bien"
        description="Le motif est transmis à l'hôte, qui pourra corriger et soumettre à nouveau."
        label="Motif du rejet"
        confirmLabel="Rejeter"
        destructive
        confirmTestId="admin-reject-confirm"
        onConfirm={(reason) => run(() => api.post(`${base}/reject/`, { reason }), "Bien rejeté.")}
      />
    </Card>
  );
}
