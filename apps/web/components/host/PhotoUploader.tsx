"use client";

import { ArrowDown, ArrowUp, ImagePlus, Trash2 } from "lucide-react";
import Image from "next/image";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiRequestError } from "@/lib/api/client";
import type { Photo } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface Props {
  /** Ex. /listings/host/properties/{id} ou /listings/staff/properties/{id} */
  basePath: string;
  photos: Photo[];
  onChange: () => Promise<void> | void;
  disabled?: boolean;
  teamMode?: boolean;
}

const MAX_MB = 10;

export function PhotoUploader({ basePath, photos, onChange, disabled, teamMode }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(0);
  const [dragging, setDragging] = useState(false);
  const ordered = [...photos].sort((a, b) => a.order - b.order);

  async function upload(files: FileList | File[]) {
    const list = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (list.length === 0) return;
    setUploading(list.length);
    let ok = 0;
    for (const file of list) {
      if (file.size > MAX_MB * 1024 * 1024) {
        toast.error(`${file.name} dépasse ${MAX_MB} Mo.`);
        continue;
      }
      const fd = new FormData();
      fd.append("image", file);
      fd.append(
        "alt_text",
        file.name
          .replace(/\.[^.]+$/, "")
          .replace(/[-_]+/g, " ")
          .slice(0, 160),
      );
      try {
        await api.upload(`${basePath}/photos/`, fd);
        ok += 1;
      } catch (err) {
        toast.error(
          err instanceof ApiRequestError
            ? (err.fieldError("image") ?? err.message)
            : `Échec pour ${file.name}`,
        );
      }
      setUploading((n) => n - 1);
    }
    if (ok) toast.success(`${ok} photo(s) ajoutée(s).`);
    await onChange();
  }

  async function move(index: number, delta: -1 | 1) {
    const next = [...ordered];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target]!, next[index]!];
    try {
      await api.post(`${basePath}/photos/reorder/`, { order: next.map((p) => p.public_id) });
      await onChange();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    }
  }

  async function remove(photo: Photo) {
    if (!window.confirm("Supprimer cette photo ?")) return;
    try {
      await api.delete(`${basePath}/photos/${photo.public_id}/`);
      await onChange();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    }
  }

  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="text-lg">Photos</h2>
        <p className="text-sm text-muted-foreground">
          {teamMode
            ? "Photos prises par l'équipe : elles remplacent visuellement celles de l'hôte (badge « Photo équipe Loka »)."
            : "Au moins 3 photos. La première est la photo principale. Nos photos prises lors de la visite viendront compléter les vôtres."}
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) void upload(e.dataTransfer.files);
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center",
          dragging ? "border-primary bg-accent" : "border-border",
          disabled && "opacity-50",
        )}
      >
        <ImagePlus className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm">Glissez vos photos ici ou</p>
        <Button
          type="button"
          variant="outline"
          onClick={() => input.current?.click()}
          disabled={disabled || uploading > 0}
        >
          {uploading > 0 ? `Envoi (${uploading} restante(s))…` : "Choisir des fichiers"}
        </Button>
        <p className="text-xs text-muted-foreground">
          JPEG, PNG ou WebP · {MAX_MB} Mo max par photo
        </p>
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="sr-only"
          onChange={(e) => e.target.files && void upload(e.target.files)}
          data-testid="photo-input"
          disabled={disabled}
        />
      </div>

      {ordered.length > 0 && (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {ordered.map((photo, index) => (
            <li
              key={photo.public_id}
              className="relative overflow-hidden rounded-lg border bg-muted"
              data-testid="photo-item"
            >
              <div className="relative aspect-[4/3]">
                {photo.variants.card ? (
                  <Image
                    src={photo.variants.card}
                    alt={photo.alt_text}
                    fill
                    sizes="33vw"
                    className="object-cover"
                  />
                ) : (
                  <span className="grid h-full place-items-center text-xs text-muted-foreground">
                    Traitement…
                  </span>
                )}
              </div>
              <div className="absolute left-2 top-2 flex gap-1">
                {index === 0 && <Badge>Principale</Badge>}
                {photo.taken_by_team && <Badge variant="verified">Équipe Loka</Badge>}
              </div>
              {!disabled && (
                <div className="flex items-center justify-between gap-1 p-1.5">
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => move(index, -1)}
                      disabled={index === 0}
                      aria-label="Monter"
                    >
                      <ArrowUp />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => move(index, 1)}
                      disabled={index === ordered.length - 1}
                      aria-label="Descendre"
                    >
                      <ArrowDown />
                    </Button>
                  </div>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive"
                    onClick={() => remove(photo)}
                    aria-label="Supprimer"
                  >
                    <Trash2 />
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
