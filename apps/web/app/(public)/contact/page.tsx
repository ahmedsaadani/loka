import { SiteContentPage } from "@/components/content/SiteContentPage";
import { pageMetadata } from "@/lib/seo";

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Contact",
  description: "Contacter l'équipe Loka : questions, partenariats, propriétaires.",
  path: "/contact",
});

export default function ContactPage() {
  return <SiteContentPage contentKey="contact" fallbackTitle="Contact" />;
}
