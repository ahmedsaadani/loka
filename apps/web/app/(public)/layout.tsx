import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { JsonLd } from "@/components/JsonLd";
import { organizationJsonLd } from "@/lib/seo";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main id="contenu" className="min-h-[60vh]">
        {children}
      </main>
      <Footer />
      <JsonLd data={organizationJsonLd()} />
    </>
  );
}
