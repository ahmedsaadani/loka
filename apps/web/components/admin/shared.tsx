"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiRequestError } from "@/lib/api/client";

/** Message d'erreur uniforme pour les actions du back-office. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiRequestError ? error.message : "Une erreur est survenue.";
}

export function ErrorNote({ error }: { error: ApiRequestError | null }) {
  if (!error) return null;
  return (
    <p
      role="alert"
      className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm"
    >
      {error.message}
    </p>
  );
}

export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

export function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
      {children}
    </p>
  );
}

interface PaginationProps {
  page: number;
  hasPrevious: boolean;
  hasNext: boolean;
  count?: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, hasPrevious, hasNext, count, onChange }: PaginationProps) {
  if (!hasPrevious && !hasNext) return null;
  return (
    <nav className="flex items-center justify-between pt-2" aria-label="Pagination">
      <Button
        variant="outline"
        size="sm"
        disabled={!hasPrevious}
        onClick={() => onChange(page - 1)}
      >
        Précédent
      </Button>
      <span className="text-xs text-muted-foreground">
        Page {page}
        {count !== undefined ? ` · ${count} au total` : ""}
      </span>
      <Button variant="outline" size="sm" disabled={!hasNext} onClick={() => onChange(page + 1)}>
        Suivant
      </Button>
    </nav>
  );
}

interface ReasonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  label?: string;
  required?: boolean;
  confirmLabel?: string;
  destructive?: boolean;
  confirmTestId?: string;
  onConfirm: (text: string) => Promise<void>;
}

/** Dialogue générique « motif / note » utilisé pour rejeter, annuler, renvoyer, etc. */
export function ReasonDialog({
  open,
  onOpenChange,
  title,
  description,
  label = "Motif",
  required = true,
  confirmLabel = "Confirmer",
  destructive = false,
  confirmTestId,
  onConfirm,
}: ReasonDialogProps) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await onConfirm(text.trim());
      setText("");
      onOpenChange(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="space-y-1">
          <Label htmlFor="reason-dialog-text">{label}</Label>
          <Textarea
            id="reason-dialog-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Annuler
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={submit}
            disabled={busy || (required && !text.trim())}
            data-testid={confirmTestId}
          >
            {busy ? "En cours…" : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Lit le paramètre `page` d'une URL, borné à 1 minimum. */
export function parsePage(value: string | null): number {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : 1;
}
