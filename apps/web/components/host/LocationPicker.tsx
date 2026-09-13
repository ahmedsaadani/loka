"use client";

import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { LatLng } from "@/lib/api/types";
import { getMapStyle, MAP_UNAVAILABLE_MESSAGE, TUNISIA_CENTER } from "@/lib/map";

interface Props {
  value: LatLng | null;
  onChange: (value: LatLng) => void;
  center: LatLng | null;
  disabled?: boolean;
}

/** Carte cliquable : un clic place (ou déplace) le marqueur du bien. */
export function LocationPicker({ value, onChange, center, disabled }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const initial = value ?? center;
    const style = getMapStyle();
    if (!style) {
      container.current.textContent = MAP_UNAVAILABLE_MESSAGE;
      return;
    }
    const map = new maplibregl.Map({
      container: container.current,
      style,
      center: initial ? [initial.lng, initial.lat] : TUNISIA_CENTER,
      zoom: value ? 15 : 12,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("click", (e) => {
      if (disabled) return;
      onChangeRef.current({
        lat: Number(e.lngLat.lat.toFixed(6)),
        lng: Number(e.lngLat.lng.toFixed(6)),
      });
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!value) {
      marker.current?.remove();
      marker.current = null;
      return;
    }
    if (!marker.current) {
      marker.current = new maplibregl.Marker({ color: "#b8552e", draggable: !disabled })
        .setLngLat([value.lng, value.lat])
        .addTo(map);
      marker.current.on("dragend", () => {
        const pos = marker.current?.getLngLat();
        if (pos)
          onChangeRef.current({ lat: Number(pos.lat.toFixed(6)), lng: Number(pos.lng.toFixed(6)) });
      });
    } else {
      marker.current.setLngLat([value.lng, value.lat]);
    }
  }, [value, disabled]);

  return (
    <div>
      <div
        ref={container}
        className="h-72 w-full overflow-hidden rounded-lg border"
        role="application"
        aria-label="Carte pour positionner le bien"
        data-testid="location-picker"
      />
      <p className="mt-1 text-xs text-muted-foreground">
        {value
          ? `Position : ${value.lat}, ${value.lng}`
          : "Aucune position : cliquez sur la carte."}
      </p>
    </div>
  );
}
