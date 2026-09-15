import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Loka — Logements vérifiés en Tunisie",
    short_name: "Loka",
    description:
      "Location d'appartements, studios et villas vérifiés en Tunisie, à la nuit, au mois ou à l'année.",
    start_url: "/",
    display: "standalone",
    background_color: "#f9f7f3",
    theme_color: "#b5502e",
    lang: "fr",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
