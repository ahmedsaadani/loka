"use client";

import dynamic from "next/dynamic";

/** MapLibre (~200 kB) n'est chargé qu'au rendu client, hors du bundle initial de la fiche. */
export const PropertyMapLazy = dynamic(
  () => import("@/components/listing/PropertyMap").then((m) => m.PropertyMap),
  { ssr: false, loading: () => <div className="h-72 w-full animate-pulse rounded-xl bg-muted" /> },
);
