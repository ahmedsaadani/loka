import type { captureRequestError } from "@sentry/nextjs";

/**
 * Sentry côté serveur et edge. Désactivé si NEXT_PUBLIC_SENTRY_DSN est vide.
 * Chargé par Next.js au démarrage (instrumentation hook).
 */
export async function register(): Promise<void> {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.init({
    dsn,
    environment: process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: process.env.SENTRY_RELEASE ?? process.env.IMAGE_TAG,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.1"),
    sendDefaultPii: false,
  });
}

export const onRequestError = async (
  ...args: Parameters<typeof captureRequestError>
): Promise<void> => {
  if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(...args);
};
