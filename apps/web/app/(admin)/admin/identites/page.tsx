"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
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
import { StatusBadge } from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { IdentityDocument, Paginated, SignedUrl } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

function Identities() {
  const params = useSearchParams();
  const router = useRouter();
  const status = params.get("status") ?? "pending";
  const page = parsePage(params.get("page"));
  const path =
    status === "pending" ? "/auth/identity-documents/pending/" : "/auth/identity-documents/";
  const { data, loading, error, refetch } = useApi<Paginated<IdentityDocument>>(
    path,
    status === "pending" ? { page } : { status, page },
  );
  const [rejecting, setRejecting] = useState<IdentityDocument | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  function setParams(next: Record<string, string>) {
    const sp = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) sp.set(k, v);
      else sp.delete(k);
    }
    router.replace(`/admin/identites?${sp.toString()}`);
  }

  async function view(doc: IdentityDocument) {
    try {
      const signed = await api.get<SignedUrl>(
        `/auth/identity-documents/${doc.public_id}/download/`,
      );
      window.open(signed.url, "_blank", "noopener");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  }

  async function approve(doc: IdentityDocument) {
    setBusy(doc.public_id);
    try {
      await api.post(`/auth/identity-documents/${doc.public_id}/approve/`);
      toast.success(`Identité de ${doc.user_email} approuvée.`);
      await refetch();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl md:text-3xl">Vérification des identités</h1>
        <p className="text-sm text-muted-foreground">
          Chaque consultation de document est journalisée (qui, quand, adresse IP).
        </p>
      </div>
      <Tabs value={status} onValueChange={(v) => setParams({ status: v, page: "" })}>
        <TabsList>
          <TabsTrigger value="pending">En attente</TabsTrigger>
          <TabsTrigger value="approved">Approuvées</TabsTrigger>
          <TabsTrigger value="rejected">Rejetées</TabsTrigger>
        </TabsList>
      </Tabs>
      <ErrorNote error={error} />
      {loading && !data ? (
        <ListSkeleton />
      ) : !data || data.results.length === 0 ? (
        <EmptyNote>Aucun document {status === "pending" ? "en attente" : ""}.</EmptyNote>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data.results.map((doc) => (
            <li
              key={doc.public_id}
              className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm"
              data-testid="identity-row"
            >
              <div>
                <p className="font-medium">{doc.user_email}</p>
                <p className="text-muted-foreground">
                  {doc.doc_type === "cin" ? "Carte d'identité" : "Passeport"} · envoyé le{" "}
                  {formatDate(doc.created_at)}
                  {doc.reviewed_at ? ` · traité le ${formatDate(doc.reviewed_at)}` : ""}
                  {doc.rejection_reason ? ` · Motif : ${doc.rejection_reason}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge kind="identity" status={doc.status} />
                <Button size="sm" variant="outline" onClick={() => view(doc)}>
                  Voir le document
                </Button>
                {doc.status === "pending" && (
                  <>
                    <Button
                      size="sm"
                      disabled={busy === doc.public_id}
                      onClick={() => approve(doc)}
                      data-testid="identity-approve"
                    >
                      Approuver
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive"
                      onClick={() => setRejecting(doc)}
                    >
                      Rejeter
                    </Button>
                  </>
                )}
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
        open={rejecting !== null}
        onOpenChange={(open) => !open && setRejecting(null)}
        title="Rejeter le document"
        description="L'utilisateur verra ce motif et pourra envoyer un nouveau document."
        confirmLabel="Rejeter"
        destructive
        onConfirm={async (reason) => {
          if (!rejecting) return;
          try {
            await api.post(`/auth/identity-documents/${rejecting.public_id}/reject/`, { reason });
            toast.success("Document rejeté.");
            await refetch();
          } catch (err) {
            toast.error(errorMessage(err));
          }
        }}
      />
    </div>
  );
}

export default function IdentitiesPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <Identities />
    </Suspense>
  );
}
