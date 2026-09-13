/**
 * Sentry côté navigateur. Désactivé si NEXT_PUBLIC_SENTRY_DSN est vide (dev par défaut).
 * Chargé par Next.js avant l'hydratation (instrumentation-client hook, Next 15.3+).
 */
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
    tracesSampleRate: 0.1,
    replaysOnErrorSampleRate: 0,
    replaysSessionSampleRate: 0,
    sendDefaultPii: false,
  });
}

export const onRouterTransitionStart = dsn ? Sentry.captureRouterTransitionStart : () => undefined;
