import Link from "next/link";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";

export default function NotFound() {
  return (
    <>
      <Header />
      <main className="container flex min-h-[60vh] flex-col items-center justify-center py-16 text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">404</p>
        <h1 className="mt-2 text-3xl md:text-4xl">{t.common.notFound}</h1>
        <p className="mt-3 max-w-md text-muted-foreground">{t.common.notFoundText}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button asChild>
            <Link href="/">{t.common.backHome}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/recherche">{t.nav.search}</Link>
          </Button>
        </div>
      </main>
      <Footer />
    </>
  );
}
