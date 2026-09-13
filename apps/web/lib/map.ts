import type { StyleSpecification } from "maplibre-gl";

/** Style MapLibre minimal : tuiles raster OpenStreetMap, aucune dépendance payante. */
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

export const TUNISIA_CENTER: [number, number] = [10.18, 36.8];
export const DEFAULT_ZOOM = 11;
