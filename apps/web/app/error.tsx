"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="container flex min-h-[60vh] flex-col items-center justify-center py-16 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-primary">Erreur</p>
      <h1 className="mt-2 text-3xl md:text-4xl">{t.common.serverError}</h1>
      <p className="mt-3 max-w-md text-muted-foreground">
        {t.common.error} {error.digest ? `Référence : ${error.digest}` : ""}
      </p>
      <div className="mt-6 flex gap-3">
        <Button onClick={reset}>{t.common.retry}</Button>
        <Button variant="outline" asChild>
          <Link href="/">{t.common.backHome}</Link>
        </Button>
      </div>
    </main>
  );
}
