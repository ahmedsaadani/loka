"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import { useApi } from "@/lib/api/hooks";
import type { IdentityDocument, Paginated } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

const STATUS: Record<
  IdentityDocument["status"],
  { label: string; variant: BadgeProps["variant"] }
> = {
  pending: { label: "En cours de vérification", variant: "default" },
  approved: { label: "Approuvé", variant: "verified" },
  rejected: { label: "Rejeté", variant: "destructive" },
};

export default function IdentityPage() {
  const { user, refreshUser } = useAuth();
  const { data, loading, refetch } = useApi<Paginated<IdentityDocument>>(
    "/auth/identity-documents/",
  );
  const [docType, setDocType] = useState<"cin" | "passport">("cin");
  const [uploading, setUploading] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setUploading(true);
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await api.upload("/auth/identity-documents/", fd);
      toast.success("Document envoyé. Vérification sous 48 h ouvrées.");
      await Promise.all([refetch(), refreshUser()]);
    } catch (err) {
      toast.error(
        err instanceof ApiRequestError
          ? (err.fieldError("file") ?? err.message)
          : "Une erreur est survenue.",
      );
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
    }
  }

  const hasPending = data?.results.some((d) => d.status === "pending");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl">Vérification d&apos;identité</h1>
        <p className="text-muted-foreground">
          {user?.is_identity_verified
            ? "Votre identité est vérifiée : les hôtes le voient sur vos demandes."
            : "Une identité vérifiée rassure les hôtes et accélère l'acceptation de vos demandes. Obligatoire pour publier un bien."}
        </p>
      </div>

      {!user?.is_identity_verified && !hasPending && (
        <Card>
          <CardHeader>
            <CardTitle>Envoyer une pièce d&apos;identité</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              CIN ou passeport, en PDF ou photo (JPEG, PNG, WebP), 8 Mo max. Le document est stocké
              dans un espace privé chiffré ; seule l&apos;équipe Loka y accède et chaque
              consultation est journalisée.
            </p>
            <div className="grid gap-3 sm:grid-cols-[200px_1fr]">
              <div className="space-y-1">
                <Label>Type</Label>
                <Select value={docType} onValueChange={(v) => setDocType(v as "cin" | "passport")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cin">Carte d&apos;identité (CIN)</SelectItem>
                    <SelectItem value="passport">Passeport</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="identity-file">Fichier</Label>
                <input
                  id="identity-file"
                  ref={input}
                  type="file"
                  accept="application/pdf,image/jpeg,image/png,image/webp"
                  className="block w-full text-sm"
                  disabled={uploading}
                  onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])}
                  data-testid="identity-file"
                />
              </div>
            </div>
            {uploading && <p className="text-sm text-muted-foreground">Envoi en cours…</p>}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Historique</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Chargement…</p>
          ) : !data || data.results.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun document envoyé.</p>
          ) : (
            <ul className="divide-y text-sm">
              {data.results.map((d) => (
                <li
                  key={d.public_id}
                  className="flex flex-wrap items-center justify-between gap-2 py-2"
                >
                  <span>
                    {d.doc_type === "cin" ? "CIN" : "Passeport"} · envoyé le{" "}
                    {formatDate(d.created_at)}
                    {d.status === "rejected" && d.rejection_reason
                      ? ` · Motif : ${d.rejection_reason}`
                      : ""}
                  </span>
                  <Badge variant={STATUS[d.status].variant}>{STATUS[d.status].label}</Badge>
                </li>
              ))}
            </ul>
          )}
          {data?.results.some((d) => d.status === "rejected") &&
            !hasPending &&
            !user?.is_identity_verified && (
              <Button variant="outline" className="mt-3" onClick={() => input.current?.click()}>
                Envoyer un nouveau document
              </Button>
            )}
        </CardContent>
      </Card>
    </div>
  );
}
