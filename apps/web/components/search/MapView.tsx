"use client";

import maplibregl from "maplibre-gl";
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

function styleMarker(el: HTMLElement, active: boolean): void {
  el.style.background = active ? "#26272b" : "#fff";
  el.style.color = active ? "#fff" : "#26272b";
  el.style.borderColor = active ? "#26272b" : "#e2ddd3";
  el.style.transform = active ? "scale(1.12)" : "scale(1)";
  el.style.zIndex = active ? "2" : "1";
}

function markerElement(label: string, active: boolean): HTMLDivElement {
  const el = document.createElement("div");
  el.textContent = label;
  el.style.cssText =
    "cursor:pointer;padding:4px 8px;border-radius:999px;font:600 12px system-ui,sans-serif;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.25);transition:transform .15s;border:1.5px solid;";
  styleMarker(el, active);
  return el;
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
  const markers = useRef<Map<string, maplibregl.Marker>>(new Map());
  const moveHandler = useRef(onMoveEnd);
  const clickHandler = useRef(onMarkerClick);
  const suppressMove = useRef(false);
  moveHandler.current = onMoveEnd;
  clickHandler.current = onMarkerClick;

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
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Marqueurs
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markers.current.forEach((m) => m.remove());
    markers.current.clear();
    for (const property of properties) {
      if (!property.location) continue;
      const plan = pickPlan(property.pricing_plans, preferredMode);
      const el = markerElement(
        plan ? formatTnd(plan.price) : "—",
        property.public_id === highlighted,
      );
      el.addEventListener("click", () => clickHandler.current?.(property.public_id));
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([property.location.lng, property.location.lat])
        .addTo(map);
      markers.current.set(property.public_id, marker);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [properties, preferredMode]);

  // Surbrillance
  useEffect(() => {
    markers.current.forEach((marker, id) => styleMarker(marker.getElement(), id === highlighted));
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
