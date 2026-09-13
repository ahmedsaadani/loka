import { NextResponse, type NextRequest } from "next/server";

/**
 * CSP par nonce (ADR 0009) : chaque réponse HTML reçoit un nonce unique. Next.js l'applique
 * automatiquement à ses propres balises <script> quand l'en-tête est présent sur la requête.
 * Aucun 'unsafe-inline' ni 'unsafe-eval' en production. En développement, Next a besoin
 * d'`eval` pour les source maps et le rafraîchissement à chaud.
 */

const publicApi = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
const s3Public = process.env.NEXT_PUBLIC_S3_PUBLIC_URL ?? "http://localhost:9000";
const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";
const isDev = process.env.NODE_ENV !== "production";

function originOf(url: string): string {
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

const apiOrigin = originOf(publicApi);
const s3Origin = originOf(s3Public);
const sentryOrigin = sentryDsn ? originOf(sentryDsn) : "";
const mapHosts =
  "https://api.maptiler.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org";

function buildCsp(nonce: string): string {
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""}`,
    // Exception documentée (ADR 0009) : next/image (`style="color:transparent"`) et Radix rendent
    // des attributs style inline côté serveur, impossibles à noncer. 'unsafe-inline' sur les
    // styles n'autorise aucune exécution de script.
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' data: blob: ${s3Origin} https://*.amazonaws.com ${mapHosts}`,
    "font-src 'self' data:",
    `connect-src 'self' ${apiOrigin} ${mapHosts}${sentryOrigin ? ` ${sentryOrigin}` : ""}`,
    "worker-src 'self' blob:",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    ...(isDev ? [] : ["upgrade-insecure-requests"]),
  ];
  return directives.join("; ");
}

export function middleware(request: NextRequest): NextResponse {
  // btoa : disponible dans le runtime edge du middleware (Buffer ne l'est pas en dev).
  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [
    // Pages HTML uniquement : pas les assets, images ni les routes API internes.
    {
      source: "/((?!api|_next/static|_next/image|icon.svg|favicon.ico|robots.txt|sitemap.xml).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
