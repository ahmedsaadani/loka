import { BadgeCheck, CalendarClock, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { PropertyCard } from "@/components/listing/PropertyCard";
import { SearchBar } from "@/components/search/SearchBar";
import { Button } from "@/components/ui/button";
import { serverApi } from "@/lib/api/client";
import type { CitySummary, Paginated, PropertyCard as PropertyCardData } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { pageMetadata } from "@/lib/seo";
import { formatTnd } from "@/lib/utils";

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Loka · Location d'appartements vérifiés en Tunisie, à la nuit, au mois ou à l'année",
  description:
    "Studios, S+1, S+2, villas et colocations à Ariana, Tunis et Sousse. Chaque logement est visité, photographié et validé par l'équipe Loka avant publication.",
  path: "/",
});

async function loadHome(): Promise<{ cities: CitySummary[]; latest: PropertyCardData[] }> {
  try {
    const [cities, latest] = await Promise.all([
      serverApi.get<Paginated<CitySummary>>("/geo/cities/", { page_size: 12 }),
      serverApi.get<Paginated<PropertyCardData>>("/listings/properties/", { page_size: 6 }),
    ]);
    return { cities: cities.results, latest: latest.results };
  } catch {
    return { cities: [], latest: [] };
  }
}

const STEP_ICONS = [ShieldCheck, CalendarClock, BadgeCheck];

export default async function HomePage() {
  const { cities, latest } = await loadHome();
  const featured = cities.filter((c) => c.is_featured || c.property_count > 0).slice(0, 6);

  return (
    <>
      <section className="border-b bg-gradient-to-b from-accent/60 to-background">
        <div className="container py-10 md:py-16">
          <div className="max-w-3xl">
            <h1 className="text-display-sm md:text-display-lg">{t.home.heroTitle}</h1>
            <p className="mt-4 max-w-2xl text-base text-muted-foreground md:text-lg">
              {t.home.heroSubtitle}
            </p>
          </div>
          <SearchBar cities={cities} className="mt-8" />
        </div>
      </section>

      <section id="villes" className="container py-12 md:py-16" aria-labelledby="villes-titre">
        <div className="mb-6 flex items-end justify-between gap-4">
          <h2 id="villes-titre" className="text-2xl md:text-3xl">
            {t.home.popularCities}
          </h2>
        </div>
        {featured.length === 0 ? (
          <p className="text-muted-foreground">Les premières villes arrivent bientôt.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((city) => (
              <li key={city.slug}>
                <Link
                  href={`/location/${city.slug}`}
                  className="flex items-center justify-between rounded-xl border bg-card p-5 shadow-card transition-shadow hover:shadow-float"
                >
                  <div>
                    <p className="text-lg font-semibold">{city.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {city.property_count} {t.city.properties}
                      {city.avg_monthly_price
                        ? ` · dès ${formatTnd(city.avg_monthly_price)} / mois`
                        : ""}
                    </p>
                  </div>
                  <span className="text-primary" aria-hidden="true">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="bg-card py-12 md:py-16" aria-labelledby="verifies-titre">
        <div className="container">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 id="verifies-titre" className="text-2xl md:text-3xl">
                {t.home.verifiedTitle}
              </h2>
              <p className="mt-1 text-muted-foreground">{t.home.verifiedSubtitle}</p>
            </div>
            <Button variant="outline" asChild className="hidden sm:inline-flex">
              <Link href="/recherche">{t.home.seeAll}</Link>
            </Button>
          </div>
          {latest.length === 0 ? (
            <p className="text-muted-foreground">Aucun bien publié pour le moment.</p>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {latest.map((property, index) => (
                <PropertyCard key={property.public_id} property={property} priority={index === 0} />
              ))}
            </div>
          )}
          <div className="mt-6 sm:hidden">
            <Button variant="outline" asChild className="w-full">
              <Link href="/recherche">{t.home.seeAll}</Link>
            </Button>
          </div>
        </div>
      </section>

      <section
        id="comment-ca-marche"
        className="container py-12 md:py-16"
        aria-labelledby="comment-titre"
      >
        <h2 id="comment-titre" className="text-2xl md:text-3xl">
          {t.home.howTitle}
        </h2>
        <ol className="mt-6 grid gap-6 md:grid-cols-3">
          {t.home.steps.map((step, index) => {
            const Icon = STEP_ICONS[index] ?? ShieldCheck;
            return (
              <li key={step.title} className="rounded-xl border bg-card p-5 shadow-card">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-verified-soft text-verified">
                  <Icon className="h-5 w-5" />
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

      <section className="container pb-12 md:pb-16">
        <div className="flex flex-col items-start gap-4 rounded-2xl bg-foreground px-6 py-8 text-background md:flex-row md:items-center md:justify-between md:px-10">
          <div>
            <h2 className="text-2xl">{t.home.hostCtaTitle}</h2>
            <p className="mt-1 max-w-xl text-background/80">{t.home.hostCtaText}</p>
          </div>
          <Button size="lg" variant="secondary" asChild>
            <Link href="/hote/inscription">{t.home.hostCta}</Link>
          </Button>
        </div>
      </section>
    </>
  );
}
