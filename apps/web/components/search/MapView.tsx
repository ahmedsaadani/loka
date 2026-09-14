"use client";

import maplibregl, { type GeoJSONSource, type MapGeoJSONFeature } from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { PropertyCard } from "@/lib/api/types";
import { DEFAULT_ZOOM, getMapStyle, MAP_UNAVAILABLE_MESSAGE, TUNISIA_CENTER } from "@/lib/map";
import { formatTnd } from "@/lib/utils";

import { pickPlan } from "../listing/PriceTag";

interface Props {
  properties: PropertyCard[];
  highlighted: string | null;
  preferredMode?: string;
  /** Change de valeur quand la ville ou les filtres changent : la carte se recadre alors. */
  fitKey: string;
  onMarkerClick?: (publicId: string) => void;
  onMoveEnd?: (bbox: string) => void;
  className?: string;
}

/** Regroupement : rayon en pixels et zoom au-delà duquel on ne regroupe plus. */
const SOURCE_ID = "search-properties";
const CLUSTER_RADIUS = 48;
const CLUSTER_MAX_ZOOM = 15;
/** En dessous de ce zoom, un bien isolé est un simple point ; au-dessus, l'étiquette de prix. */
export const PRICE_LABEL_MIN_ZOOM = 13;

interface PointProps {
  id: string;
  label: string;
}

type ClusterProps = { cluster: true; cluster_id: number; point_count: number };

const PILL_STYLE =
  "cursor:pointer;padding:4px 8px;border-radius:999px;font:600 12px system-ui,sans-serif;" +
  "white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.25);transition:transform .15s;border:1.5px solid;";
const DOT_STYLE =
  "cursor:pointer;width:14px;height:14px;border-radius:999px;box-shadow:0 1px 4px rgba(0,0,0,.35);" +
  "transition:transform .15s;border:2px solid #fff;";
const CLUSTER_STYLE =
  "cursor:pointer;display:grid;place-items:center;border-radius:999px;background:#b5502e;color:#fff;" +
  "font:700 13px system-ui,sans-serif;box-shadow:0 2px 10px rgba(0,0,0,.3);border:3px solid rgba(255,255,255,.85);";

function styleMarker(el: HTMLElement, active: boolean): void {
  const dot = el.dataset.kind === "dot";
  el.style.background = active ? "#26272b" : dot ? "#b5502e" : "#fff";
  el.style.color = active ? "#fff" : "#26272b";
  if (!dot) el.style.borderColor = active ? "#26272b" : "#e2ddd3";
  el.style.transform = active ? "scale(1.15)" : "scale(1)";
  el.style.zIndex = active ? "2" : "1";
}

function pointElement(label: string, showLabel: boolean, active: boolean): HTMLDivElement {
  const el = document.createElement("div");
  applyPointMode(el, label, showLabel);
  styleMarker(el, active);
  return el;
}

function applyPointMode(el: HTMLElement, label: string, showLabel: boolean): void {
  const kind = showLabel ? "pill" : "dot";
  if (el.dataset.kind === kind) return;
  el.dataset.kind = kind;
  el.style.cssText = showLabel ? PILL_STYLE : DOT_STYLE;
  el.textContent = showLabel ? label : "";
  el.setAttribute("aria-label", label);
  el.setAttribute("role", "button");
}

function clusterElement(count: number): HTMLDivElement {
  const el = document.createElement("div");
  const size = count < 10 ? 34 : count < 100 ? 40 : 48;
  el.style.cssText = `${CLUSTER_STYLE}width:${size}px;height:${size}px;`;
  el.textContent = String(count);
  el.setAttribute("role", "button");
  el.setAttribute("aria-label", `${count} logements, cliquer pour zoomer`);
  return el;
}

function toGeoJSON(
  properties: PropertyCard[],
  preferredMode?: string,
): GeoJSON.FeatureCollection<GeoJSON.Point, PointProps> {
  return {
    type: "FeatureCollection",
    features: properties
      .filter((p) => p.location)
      .map((p) => {
        const plan = pickPlan(p.pricing_plans, preferredMode);
        return {
          type: "Feature",
          geometry: { type: "Point", coordinates: [p.location!.lng, p.location!.lat] },
          properties: { id: p.public_id, label: plan ? formatTnd(plan.price) : "—" },
        };
      }),
  };
}

export function MapView({
  properties,
  highlighted,
  preferredMode,
  fitKey,
  onMarkerClick,
  onMoveEnd,
  className,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  /** Marqueurs affichés, clé `p:<public_id>` (bien) ou `c:<cluster_id>` (groupe). */
  const markers = useRef<Map<string, maplibregl.Marker>>(new Map());
  const moveHandler = useRef(onMoveEnd);
  const clickHandler = useRef(onMarkerClick);
  const highlightedRef = useRef(highlighted);
  const suppressMove = useRef(false);
  moveHandler.current = onMoveEnd;
  clickHandler.current = onMarkerClick;
  highlightedRef.current = highlighted;

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const style = getMapStyle();
    if (!style) {
      container.current.textContent = MAP_UNAVAILABLE_MESSAGE;
      return;
    }
    const map = new maplibregl.Map({
      container: container.current,
      style,
      center: TUNISIA_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    const syncMarkers = () => {
      if (!map.getSource(SOURCE_ID) || !map.isSourceLoaded(SOURCE_ID)) return;
      const showLabels = map.getZoom() >= PRICE_LABEL_MIN_ZOOM;
      const seen = new Set<string>();
      for (const feature of map.querySourceFeatures(SOURCE_ID) as MapGeoJSONFeature[]) {
        if (feature.geometry.type !== "Point") continue;
        const [lng, lat] = feature.geometry.coordinates as [number, number];
        const props = feature.properties as PointProps | ClusterProps;
        if ("cluster" in props && props.cluster) {
          const key = `c:${props.cluster_id}`;
          seen.add(key);
          if (markers.current.has(key)) continue;
          const el = clusterElement(props.point_count);
          const clusterId = props.cluster_id;
          el.addEventListener("click", () => {
            const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
            source
              ?.getClusterExpansionZoom(clusterId)
              .then((zoom) => map.easeTo({ center: [lng, lat], zoom: zoom + 0.5, duration: 350 }))
              .catch(() => undefined);
          });
          markers.current.set(
            key,
            new maplibregl.Marker({ element: el }).setLngLat([lng, lat]).addTo(map),
          );
          continue;
        }
        const point = props as PointProps;
        const key = `p:${point.id}`;
        seen.add(key);
        const existing = markers.current.get(key);
        const active = point.id === highlightedRef.current;
        if (existing) {
          applyPointMode(existing.getElement(), point.label, showLabels);
          styleMarker(existing.getElement(), active);
          continue;
        }
        const el = pointElement(point.label, showLabels, active);
        el.addEventListener("click", () => clickHandler.current?.(point.id));
        markers.current.set(
          key,
          new maplibregl.Marker({ element: el }).setLngLat([lng, lat]).addTo(map),
        );
      }
      for (const [key, marker] of markers.current) {
        if (!seen.has(key)) {
          marker.remove();
          markers.current.delete(key);
        }
      }
    };

    map.on("load", () => {
      map.addSource(SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        cluster: true,
        clusterRadius: CLUSTER_RADIUS,
        clusterMaxZoom: CLUSTER_MAX_ZOOM,
      });
      // Couche invisible : nécessaire pour que MapLibre charge et regroupe la source.
      map.addLayer({
        id: `${SOURCE_ID}-anchor`,
        type: "circle",
        source: SOURCE_ID,
        paint: { "circle-opacity": 0, "circle-radius": 0 },
      });
      map.on("sourcedata", (event) => {
        if (event.sourceId === SOURCE_ID && event.isSourceLoaded) syncMarkers();
      });
      map.on("move", syncMarkers);
      map.on("moveend", syncMarkers);
      syncMarkers();
    });
    map.on("moveend", () => {
      if (suppressMove.current) {
        suppressMove.current = false;
        return;
      }
      if (!moveHandler.current) return;
      const b = map.getBounds();
      moveHandler.current(
        [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((v) => v.toFixed(5)).join(","),
      );
    });
    mapRef.current = map;
    const markerStore = markers.current;
    return () => {
      markerStore.forEach((m) => m.remove());
      markerStore.clear();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Données : la source GeoJSON regroupe elle-même les points proches.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const data = toGeoJSON(properties, preferredMode);
    const apply = () => {
      const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
      if (source) source.setData(data);
    };
    if (map.getSource(SOURCE_ID)) apply();
    else map.once("load", apply);
  }, [properties, preferredMode]);

  // Surbrillance (liste → carte)
  useEffect(() => {
    markers.current.forEach((marker, key) => {
      if (key.startsWith("p:")) styleMarker(marker.getElement(), key === `p:${highlighted}`);
    });
  }, [highlighted]);

  // Recadrage quand la recherche change (pas quand l'utilisateur déplace la carte)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const bounds = new maplibregl.LngLatBounds();
    let any = false;
    for (const p of properties) {
      if (p.location) {
        bounds.extend([p.location.lng, p.location.lat]);
        any = true;
      }
    }
    if (!any) return;
    suppressMove.current = true;
    map.fitBounds(bounds, { padding: 48, maxZoom: 15, duration: 300 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);

  return (
    <div ref={container} className={className} role="region" aria-label="Carte des résultats" />
  );
}
