import { BadgeCheck, CalendarClock, Camera, KeyRound, ShieldCheck, Wallet } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";
import { pageMetadata } from "@/lib/seo";

// CSP par nonce (ADR 0009) : rendu à la demande.
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: t.howItWorks.metaTitle,
  description: t.howItWorks.metaDescription,
  path: "/comment-ca-marche",
});

const TRAVELER_ICONS = [ShieldCheck, CalendarClock, Wallet, KeyRound];
const HOST_ICONS = [Camera, BadgeCheck, Wallet];

export default function HowItWorksPage() {
  return (
    <div className="container max-w-5xl py-10 md:py-14">
      <h1 className="text-3xl md:text-4xl">{t.howItWorks.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted-foreground">{t.howItWorks.intro}</p>

      <section className="mt-12" aria-labelledby="voyageurs">
        <h2 id="voyageurs" className="text-2xl">
          {t.howItWorks.travelerTitle}
        </h2>
        <ol className="mt-6 grid gap-5 sm:grid-cols-2">
          {t.howItWorks.travelerSteps.map((step, index) => {
            const Icon = TRAVELER_ICONS[index] ?? ShieldCheck;
            return (
              <li key={step.title} className="rounded-xl border bg-card p-5 shadow-card">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-verified-soft text-verified">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">
                  {index + 1}. {step.title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{step.text}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="mt-12" aria-labelledby="verification">
        <h2 id="verification" className="text-2xl">
          {t.howItWorks.verificationTitle}
        </h2>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2">
          {t.howItWorks.verificationPoints.map((point) => (
            <li key={point} className="flex items-start gap-3 rounded-lg border bg-card px-4 py-3">
              <BadgeCheck className="mt-0.5 h-5 w-5 shrink-0 text-verified" aria-hidden="true" />
              <span className="text-sm">{point}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12" aria-labelledby="proprietaires">
        <h2 id="proprietaires" className="text-2xl">
          {t.howItWorks.hostTitle}
        </h2>
        <ol className="mt-6 grid gap-5 md:grid-cols-3">
          {t.howItWorks.hostSteps.map((step, index) => {
            const Icon = HOST_ICONS[index] ?? Camera;
            return (
              <li key={step.title} className="rounded-xl border bg-card p-5 shadow-card">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-primary">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">
                  {index + 1}. {step.title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{step.text}</p>
              </li>
            );
          })}
        </ol>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button size="lg" asChild>
            <Link href="/devenir-hote">{t.howItWorks.hostCta}</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/recherche">{t.howItWorks.searchCta}</Link>
          </Button>
        </div>
      </section>

      <section className="mt-12" aria-labelledby="faq">
        <h2 id="faq" className="text-2xl">
          {t.howItWorks.faqTitle}
        </h2>
        <dl className="mt-6 divide-y rounded-xl border bg-card">
          {t.howItWorks.faq.map((item) => (
            <div key={item.q} className="px-5 py-4">
              <dt className="font-medium">{item.q}</dt>
              <dd className="mt-1 text-sm text-muted-foreground">{item.a}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
