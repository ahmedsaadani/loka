import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JsonLd } from "@/components/JsonLd";
import { PropertyCard } from "@/components/listing/PropertyCard";
import { Markdown } from "@/components/content/Markdown";
import { Button } from "@/components/ui/button";
import { ApiRequestError, serverApi } from "@/lib/api/client";
import type {
  CityDetail,
  CitySummary,
  Paginated,
  PropertyCard as PropertyCardData,
} from "@/lib/api/types";
import { buildCityFaq } from "@/lib/faq";
import { t } from "@/lib/i18n";
import { breadcrumbJsonLd, faqJsonLd, pageMetadata } from "@/lib/seo";
import { formatTnd } from "@/lib/utils";

interface Params {
  city: string;
}

async function loadCity(slug: string): Promise<CityDetail | null> {
  try {
    return await serverApi.get<CityDetail>(`/geo/cities/${slug}/`, undefined, {
      revalidate: 600,
      tags: [`city:${slug}`],
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return null;
    throw error;
  }
}

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { city: slug } = await params;
  const city = await loadCity(slug);
  if (!city) return { title: t.common.notFound };
  return pageMetadata({
    title: city.seo_title || `Location appartement meublé ${city.name} : logements vérifiés`,
    description:
      city.seo_description ||
      `${city.property_count} logements vérifiés à ${city.name} : studios, S+1, S+2, villas, à la nuit, au mois ou à l'année. Visités et validés par Loka.`,
    path: `/location/${city.slug}`,
  });
}

export default async function CityPage({ params }: { params: Promise<Params> }) {
  const { city: slug } = await params;
  const city = await loadCity(slug);
  if (!city) notFound();

  const [properties, allCities] = await Promise.all([
    serverApi
      .get<Paginated<PropertyCardData>>(
        "/listings/properties/",
        { city: city.slug, page_size: 12 },
        { revalidate: 300 },
      )
      .catch(() => null),
    serverApi
      .get<Paginated<CitySummary>>("/geo/cities/", { page_size: 20 }, { revalidate: 3600 })
      .catch(() => null),
  ]);
  const listings = properties?.results ?? [];
  const nearby = (allCities?.results ?? [])
    .filter((c) => c.slug !== city.slug && c.property_count > 0)
    .slice(0, 5);
  const faq = buildCityFaq(city);
  const crumbs = [
    { name: t.nav.home, path: "/" },
    { name: city.name, path: `/location/${city.slug}` },
  ];

  return (
    <div className="container py-6 md:py-10">
      <nav aria-label="Fil d'Ariane" className="mb-3 text-sm text-muted-foreground">
        <Link href="/" className="hover:text-foreground">
          {t.nav.home}
        </Link>
        <span className="mx-1">/</span>
        <span className="text-foreground">{city.name}</span>
      </nav>

      <header className="max-w-3xl">
        <h1 className="text-display-sm md:text-display-lg">
          Location appartement meublé à {city.name}
        </h1>
        <p className="mt-3 text-muted-foreground">
          {city.property_count} {t.city.properties}
          {city.avg_monthly_price
            ? ` · ${t.city.averagePrice} ${formatTnd(city.avg_monthly_price)} / mois`
            : ""}
          {city.avg_nightly_price
            ? ` · ${t.city.averageNight} ${formatTnd(city.avg_nightly_price)}`
            : ""}
        </p>
        {city.intro_text && (
          <div className="mt-4 max-w-3xl">
            <Markdown source={city.intro_text} />
          </div>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          <Button asChild>
            <Link href={`/recherche?city=${city.slug}`}>{t.city.seeListings}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/recherche?city=${city.slug}&rental_mode=nightly`}>À la nuit</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/recherche?city=${city.slug}&rental_mode=yearly`}>À l&apos;année</Link>
          </Button>
        </div>
      </header>

      {city.neighborhoods.length > 0 && (
        <section className="mt-10" aria-labelledby="quartiers">
          <h2 id="quartiers" className="text-2xl">
            {t.city.neighborhoods} de {city.name}
          </h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {city.neighborhoods.map((n) => (
              <li key={n.slug}>
                <Link
                  href={`/location/${city.slug}/${n.slug}`}
                  className="block rounded-xl border bg-card p-4 transition-shadow hover:shadow-card"
                >
                  <p className="font-semibold">{n.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {n.property_count} {t.city.properties}
                    {n.avg_monthly_price ? ` · ${formatTnd(n.avg_monthly_price)} / mois` : ""}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-10" aria-labelledby="biens">
        <div className="flex items-end justify-between gap-4">
          <h2 id="biens" className="text-2xl">
            {t.city.listingsIn} {city.name}
          </h2>
          {listings.length > 0 && (
            <Link href={`/recherche?city=${city.slug}`} className="text-sm underline">
              {t.home.seeAll}
            </Link>
          )}
        </div>
        {listings.length === 0 ? (
          <p className="mt-4 text-muted-foreground">
            Aucun bien publié à {city.name} pour le moment. Revenez bientôt ou explorez les villes
            voisines.
          </p>
        ) : (
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {listings.map((p, i) => (
              <PropertyCard key={p.public_id} property={p} priority={i === 0} />
            ))}
          </div>
        )}
      </section>

      <section className="mt-12 max-w-3xl" aria-labelledby="faq">
        <h2 id="faq" className="text-2xl">
          {t.city.faq}
        </h2>
        <dl className="mt-4 divide-y rounded-xl border bg-card">
          {faq.map((item) => (
            <div key={item.question} className="p-4">
              <dt className="font-semibold">{item.question}</dt>
              <dd className="mt-1 text-sm text-muted-foreground">{item.answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      {nearby.length > 0 && (
        <section className="mt-12" aria-labelledby="voisines">
          <h2 id="voisines" className="text-xl">
            {t.city.nearby}
          </h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {nearby.map((c) => (
              <li key={c.slug}>
                <Link
                  href={`/location/${c.slug}`}
                  className="rounded-full border bg-card px-4 py-2 text-sm hover:bg-accent"
                >
                  {c.name} ({c.property_count})
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <JsonLd data={[breadcrumbJsonLd(crumbs), faqJsonLd(faq)]} />
    </div>
  );
}
