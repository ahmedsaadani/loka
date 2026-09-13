import type { NextConfig } from "next";

const publicApi = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
const s3Public = process.env.NEXT_PUBLIC_S3_PUBLIC_URL ?? "http://localhost:9000";

function hostOf(url: string): { protocol: "http" | "https"; hostname: string; port: string } {
  const parsed = new URL(url);
  return {
    protocol: parsed.protocol.replace(":", "") as "http" | "https",
    hostname: parsed.hostname,
    port: parsed.port,
  };
}

const nextConfig: NextConfig = {
  output: "standalone",
  // NEXT_DIST_DIR permet un build de prod local (tests, Lighthouse) sans écraser le .next du dev.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    // En dev Docker, MinIO n'est pas joignable par l'optimiseur (localhost du conteneur) :
    // les variantes WebP sont déjà redimensionnées côté API, on les sert telles quelles.
    unoptimized: hostOf(s3Public).hostname === "localhost",
    formats: ["image/webp"],
    remotePatterns: [
      { ...hostOf(s3Public), pathname: "/**" },
      { ...hostOf(publicApi), pathname: "/**" },
      { protocol: "https", hostname: "**.amazonaws.com", pathname: "/**" },
    ],
    deviceSizes: [360, 640, 768, 1024, 1280, 1536],
  },
  // La Content-Security-Policy (nonce par requête) est posée par middleware.ts.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
        ],
      },
      {
        source: "/_next/static/(.*)",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default nextConfig;
