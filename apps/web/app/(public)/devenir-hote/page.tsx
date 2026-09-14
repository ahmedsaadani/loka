import { BadgeCheck, Camera, Handshake, Wallet } from "lucide-react";
import Link from "next/link";

import { OwnerContactForm } from "@/components/marketing/OwnerContactForm";
import { Button } from "@/components/ui/button";
import { serverApi } from "@/lib/api/client";
import type { CitySummary, Paginated } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { pageMetadata } from "@/lib/seo";

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache.
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: t.becomeHost.metaTitle,
  description: t.becomeHost.metaDescription,
  path: "/devenir-hote",
});

const ICONS = [Camera, BadgeCheck, Wallet, Handshake];

export default async function BecomeHostPage() {
  const cities = await serverApi
    .get<Paginated<CitySummary>>("/geo/cities/", { page_size: 50 }, { revalidate: 3600 })
    .then((d) => d.results.map((c) => c.name))
    .catch(() => [] as string[]);

  return (
    <div className="container py-10 md:py-14">
      <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-primary">
            {t.becomeHost.kicker}
          </p>
          <h1 className="mt-2 text-3xl md:text-4xl">{t.becomeHost.title}</h1>
          <p className="mt-4 max-w-xl text-lg text-muted-foreground">{t.becomeHost.intro}</p>

          <ul className="mt-8 space-y-4">
            {t.becomeHost.benefits.map((benefit, index) => {
              const Icon = ICONS[index] ?? BadgeCheck;
              return (
                <li key={benefit.title} className="flex gap-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-verified-soft text-verified">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h2 className="font-semibold">{benefit.title}</h2>
                    <p className="text-sm text-muted-foreground">{benefit.text}</p>
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="mt-8 rounded-xl border bg-card p-5">
            <h2 className="font-semibold">{t.becomeHost.feesTitle}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t.becomeHost.feesText}</p>
          </div>

          <p className="mt-6 text-sm text-muted-foreground">
            {t.becomeHost.alreadyAccount}{" "}
            <Button variant="link" className="h-auto p-0" asChild>
              <Link href="/hote/inscription">{t.becomeHost.createAccount}</Link>
            </Button>
          </p>
        </div>

        <div className="rounded-2xl border bg-card p-6 shadow-card md:p-8" id="contact">
          <h2 className="text-xl">{t.becomeHost.formTitle}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{t.becomeHost.formText}</p>
          <div className="relative mt-6">
            <OwnerContactForm cities={cities} />
          </div>
        </div>
      </div>
    </div>
  );
}
