"use client";

import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { LatLng } from "@/lib/api/types";
import { OSM_STYLE } from "@/lib/map";

interface Props {
  location: LatLng;
  approximate: boolean;
  className?: string;
}

/** Carte d'une fiche : cercle approximatif (~300 m) ou marqueur exact. */
export function PropertyMap({ location, approximate, className }: Props) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: OSM_STYLE,
      center: [location.lng, location.lat],
      zoom: approximate ? 14 : 15.5,
      attributionControl: { compact: true },
      cooperativeGestures: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      if (approximate) {
        map.addSource("zone", {
          type: "geojson",
          data: {
            type: "Feature",
            geometry: { type: "Point", coordinates: [location.lng, location.lat] },
            properties: {},
          },
        });
        map.addLayer({
          id: "zone-fill",
          type: "circle",
          source: "zone",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 18, 14, 60, 16, 220],
            "circle-color": "#b8552e",
            "circle-opacity": 0.18,
            "circle-stroke-color": "#b8552e",
            "circle-stroke-width": 2,
            "circle-stroke-opacity": 0.6,
          },
        });
      } else {
        new maplibregl.Marker({ color: "#b8552e" })
          .setLngLat([location.lng, location.lat])
          .addTo(map);
      }
    });
    return () => map.remove();
  }, [location.lat, location.lng, approximate]);

  return (
    <div
      ref={container}
      className={className}
      role="img"
      aria-label="Carte de localisation du logement"
    />
  );
}
