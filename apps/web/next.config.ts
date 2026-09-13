import type { NextConfig } from "next";

const publicApi = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
const s3Public = process.env.NEXT_PUBLIC_S3_PUBLIC_URL ?? "http://localhost:9000";
// CSP : une source avec chemin ne matche que ce chemin exact, on autorise donc l'origine entière.
const apiOrigin = new URL(publicApi).origin;

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
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              `img-src 'self' data: blob: ${s3Public} https://*.amazonaws.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org`,
              "font-src 'self' data:",
              `connect-src 'self' ${apiOrigin} https://tile.openstreetmap.org https://*.tile.openstreetmap.org`,
              "worker-src 'self' blob:",
              "frame-ancestors 'none'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
