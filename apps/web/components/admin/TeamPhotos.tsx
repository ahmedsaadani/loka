"use client";

import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";

import { errorMessage } from "@/components/admin/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { Photo } from "@/lib/api/types";

interface Props {
  propertyId: string;
  photos: Photo[];
  onChanged: () => Promise<void>;
}

/** Grille des photos avec upload « équipe » et suppression. */
export function TeamPhotos({ propertyId, photos, onChanged }: Props) {
  const base = `/listings/staff/properties/${propertyId}/photos`;
  const [file, setFile] = useState<File | null>(null);
  const [altText, setAltText] = useState("");
  const [busy, setBusy] = useState(false);
  const [inputKey, setInputKey] = useState(0);

  const upload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("image", file);
      fd.append("alt_text", altText);
      await api.upload(`${base}/`, fd);
      toast.success("Photo ajoutée.");
      setFile(null);
      setAltText("");
      setInputKey((k) => k + 1);
      await onChanged();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (photo: Photo) => {
    if (!window.confirm("Supprimer cette photo ?")) return;
    try {
      await api.delete(`${base}/${photo.public_id}/`);
      toast.success("Photo supprimée.");
      await onChanged();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const sorted = [...photos].sort((a, b) => a.order - b.order);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Photos ({photos.length})</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucune photo pour le moment.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {sorted.map((photo) => {
              const src = photo.variants.card ?? photo.variants.thumb ?? photo.variants.gallery;
              return (
                <li key={photo.public_id} className="space-y-1">
                  <div className="relative aspect-[4/3] overflow-hidden rounded-md bg-muted">
                    {src ? (
                      <Image
                        src={src}
                        alt={photo.alt_text}
                        fill
                        sizes="(max-width: 640px) 50vw, 25vw"
                        className="object-cover"
                        unoptimized
                      />
                    ) : (
                      <span className="absolute inset-0 grid place-items-center text-xs text-muted-foreground">
                        En traitement
                      </span>
                    )}
                    <div className="absolute left-1 top-1 flex gap-1">
                      {photo.is_cover && <Badge variant="default">Couverture</Badge>}
                      {photo.taken_by_team && <Badge variant="verified">Équipe</Badge>}
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-muted-foreground" title={photo.alt_text}>
                      {photo.alt_text || "Sans description"}
                    </span>
                    <Button variant="ghost" size="sm" onClick={() => remove(photo)}>
                      Supprimer
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <form
          onSubmit={upload}
          className="grid gap-3 rounded-md border p-3 sm:grid-cols-[1fr_1fr_auto]"
        >
          <div className="space-y-1">
            <Label htmlFor="admin-photo-input">Photo prise par l&apos;équipe</Label>
            <Input
              key={inputKey}
              id="admin-photo-input"
              type="file"
              accept="image/*"
              data-testid="admin-photo-input"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="admin-photo-alt">Description</Label>
            <Input
              id="admin-photo-alt"
              value={altText}
              onChange={(e) => setAltText(e.target.value)}
              placeholder="Séjour, cuisine, chambre…"
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={busy || !file} data-testid="admin-photo-submit">
              {busy ? "Envoi…" : "Ajouter"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
