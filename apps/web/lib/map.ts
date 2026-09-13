import type { StyleSpecification } from "maplibre-gl";

/**
 * Fond de carte.
 * - Production : tuiles vectorielles MapTiler (clé `NEXT_PUBLIC_MAPTILER_KEY`, quotas et CGU
 *   compatibles avec un usage commercial).
 * - Développement sans clé : tuiles raster OpenStreetMap (usage public limité, jamais en prod).
 */

export const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_KEY ?? "";
const IS_DEV = process.env.NODE_ENV !== "production";
// Opt-in explicite pour un build de production local (tests, Lighthouse) sans clé MapTiler.
// Ne jamais activer sur un déploiement public : les tuiles OSM interdisent cet usage.
const OSM_FALLBACK_OPT_IN = process.env.NEXT_PUBLIC_MAP_FALLBACK_OSM === "1";

export const OSM_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxzoom: 19,
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export type MapStyle = StyleSpecification | string;

/** Style à passer à MapLibre, ou `null` si aucune source n'est autorisée (prod sans clé). */
export function getMapStyle(): MapStyle | null {
  if (MAPTILER_KEY) {
    return `https://api.maptiler.com/maps/streets-v2/style.json?key=${MAPTILER_KEY}`;
  }
  if (IS_DEV || OSM_FALLBACK_OPT_IN) return OSM_STYLE;
  return null;
}

export const MAP_UNAVAILABLE_MESSAGE =
  "Carte indisponible : clé cartographique non configurée (NEXT_PUBLIC_MAPTILER_KEY).";

export const TUNISIA_CENTER: [number, number] = [10.18, 36.8];
export const DEFAULT_ZOOM = 11;
