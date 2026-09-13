"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type ComponentProps } from "react";

import { Button } from "@/components/ui/button";

const PropertyMap = dynamic(
  () => import("@/components/listing/PropertyMap").then((m) => m.PropertyMap),
  { ssr: false, loading: () => <div className="h-72 w-full animate-pulse rounded-xl bg-muted" /> },
);

type Props = ComponentProps<typeof PropertyMap>;

/**
 * MapLibre (~200 kB) n'est chargé ni au rendu initial ni avant que la section soit proche de
 * l'écran : la carte se monte quand elle entre dans le viewport (ou au clic sur le bouton).
 */
export function PropertyMapLazy(props: Props) {
  const sentinel = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = sentinel.current;
    if (!node || visible || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setVisible(true);
      },
      { rootMargin: "200px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [visible]);

  if (visible) return <PropertyMap {...props} />;
  return (
    <div
      ref={sentinel}
      className={props.className ?? "h-72 w-full"}
      role="img"
      aria-label="Carte de localisation du logement, chargée à l'affichage"
    >
      <div className="grid h-full w-full place-items-center rounded-xl border bg-muted/60">
        <Button variant="outline" onClick={() => setVisible(true)}>
          Afficher la carte
        </Button>
      </div>
    </div>
  );
}
