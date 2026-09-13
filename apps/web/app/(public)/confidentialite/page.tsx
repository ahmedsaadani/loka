import { SiteContentPage } from "@/components/content/SiteContentPage";
import { pageMetadata } from "@/lib/seo";

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Politique de confidentialité",
  description: "Comment Loka collecte, utilise et protège vos données personnelles.",
  path: "/confidentialite",
});

export default function PrivacyPage() {
  return (
    <SiteContentPage contentKey="confidentialite" fallbackTitle="Politique de confidentialité" />
  );
}
