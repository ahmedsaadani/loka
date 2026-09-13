"use client";

import { ChevronLeft, ChevronRight, Images, X } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import type { Photo } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface Props {
  photos: Photo[];
  title: string;
}

export function Gallery({ photos, title }: Props) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const ready = photos.filter((p) => p.variants.gallery);

  const show = useCallback((i: number) => {
    setIndex(i);
    setOpen(true);
  }, []);

  const prev = useCallback(
    () => setIndex((i) => (i - 1 + ready.length) % ready.length),
    [ready.length],
  );
  const next = useCallback(() => setIndex((i) => (i + 1) % ready.length), [ready.length]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") prev();
      if (event.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, prev, next]);

  if (ready.length === 0) {
    return (
      <div className="grid aspect-[4/3] w-full place-items-center rounded-2xl bg-muted text-muted-foreground md:aspect-[21/9]">
        Photos en préparation
      </div>
    );
  }

  const [cover, ...rest] = ready;
  const current = ready[index];

  return (
    <>
      {/* Mobile : carrousel horizontal ; desktop : mosaïque 1 + 4 */}
      <div className="scrollbar-none -mx-4 flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 md:hidden">
        {ready.map((photo, i) => (
          <button
            key={photo.public_id}
            type="button"
            onClick={() => show(i)}
            className="relative aspect-[4/3] w-[88%] shrink-0 snap-center overflow-hidden rounded-xl bg-muted"
            aria-label={`Photo ${i + 1} sur ${ready.length}`}
          >
            <Image
              src={photo.variants.gallery!}
              alt={photo.alt_text || title}
              fill
              sizes="90vw"
              className="object-cover"
              priority={i === 0}
            />
          </button>
        ))}
      </div>

      <div className="relative hidden grid-cols-4 grid-rows-2 gap-2 overflow-hidden rounded-2xl md:grid md:h-[420px]">
        <button
          type="button"
          onClick={() => show(0)}
          className="relative col-span-2 row-span-2 bg-muted"
          aria-label="Agrandir la photo principale"
        >
          <Image
            src={cover!.variants.gallery!}
            alt={cover!.alt_text || title}
            fill
            sizes="50vw"
            className="object-cover"
            priority
          />
        </button>
        {rest.slice(0, 4).map((photo, i) => (
          <button
            key={photo.public_id}
            type="button"
            onClick={() => show(i + 1)}
            className="relative bg-muted"
            aria-label={`Agrandir la photo ${i + 2}`}
          >
            <Image
              src={photo.variants.gallery!}
              alt={photo.alt_text || title}
              fill
              sizes="25vw"
              className="object-cover"
            />
          </button>
        ))}
        {Array.from({ length: Math.max(0, 4 - rest.length) }, (_, i) => (
          <div key={`empty-${i}`} className="bg-muted" />
        ))}
        <Button
          variant="secondary"
          size="sm"
          className="absolute bottom-3 right-3 shadow"
          onClick={() => show(0)}
        >
          <Images /> {t.listing.seeAllPhotos} ({ready.length})
        </Button>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="h-dvh max-w-none rounded-none border-0 bg-foreground p-0 text-background sm:h-[92vh] sm:w-[94vw] sm:max-w-6xl sm:rounded-2xl [&>button]:hidden">
          <DialogTitle className="sr-only">{title} : galerie photo</DialogTitle>
          <div className="relative flex h-full flex-col">
            <div className="flex items-center justify-between px-4 py-3 text-sm">
              <span>
                {index + 1} / {ready.length}
                {current?.taken_by_team && (
                  <span className="ml-2 rounded-full bg-background/15 px-2 py-0.5 text-xs">
                    Photo équipe Loka
                  </span>
                )}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="text-background hover:bg-background/10"
                onClick={() => setOpen(false)}
                aria-label={t.common.close}
              >
                <X className="!size-6" />
              </Button>
            </div>
            <div className="relative flex-1">
              {current && (
                <Image
                  src={current.variants.gallery!}
                  alt={current.alt_text || title}
                  fill
                  sizes="100vw"
                  className="object-contain"
                />
              )}
              {ready.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={prev}
                    className={cn(
                      "absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/15 p-3 hover:bg-background/30",
                    )}
                    aria-label={t.common.previous}
                  >
                    <ChevronLeft />
                  </button>
                  <button
                    type="button"
                    onClick={next}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/15 p-3 hover:bg-background/30"
                    aria-label={t.common.next}
                  >
                    <ChevronRight />
                  </button>
                </>
              )}
            </div>
            {current?.alt_text && (
              <p className="px-4 py-3 text-center text-sm text-background/80">{current.alt_text}</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
