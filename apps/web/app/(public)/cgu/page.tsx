import { SiteContentPage } from "@/components/content/SiteContentPage";
import { pageMetadata } from "@/lib/seo";

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Conditions d'utilisation",
  description: "Conditions générales d'utilisation de la plateforme Loka.",
  path: "/cgu",
});

export default function TermsPage() {
  return <SiteContentPage contentKey="cgu" fallbackTitle="Conditions d'utilisation" />;
}
