import Script from "next/script";

const DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;

/**
 * Mesure d'audience Plausible (respectueux de la vie privée : sans cookie, sans données
 * personnelles, donc pas de bandeau de consentement requis). Désactivé si le domaine n'est
 * pas configuré. Chargé avec le nonce CSP via next/script.
 */
export function Analytics() {
  if (!DOMAIN) return null;
  return (
    <Script
      defer
      data-domain={DOMAIN}
      src="https://plausible.io/js/script.js"
      strategy="afterInteractive"
    />
  );
}
