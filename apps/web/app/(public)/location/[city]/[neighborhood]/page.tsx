import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JsonLd } from "@/components/JsonLd";
import { PropertyCard } from "@/components/listing/PropertyCard";
import { Button } from "@/components/ui/button";
import { ApiRequestError, serverApi } from "@/lib/api/client";
import type {
  CityDetail,
  NeighborhoodDetail,
  Paginated,
  PropertyCard as PropertyCardData,
} from "@/lib/api/types";
import { buildNeighborhoodFaq } from "@/lib/faq";
import { t } from "@/lib/i18n";
import { breadcrumbJsonLd, faqJsonLd, pageMetadata } from "@/lib/seo";
import { formatTnd } from "@/lib/utils";

interface Params {
  city: string;
  neighborhood: string;
}

async function loadNeighborhood(city: string, slug: string): Promise<NeighborhoodDetail | null> {
  try {
    return await serverApi.get<NeighborhoodDetail>(
      `/geo/cities/${city}/neighborhoods/${slug}/`,
      undefined,
      { revalidate: 600 },
    );
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return null;
    throw error;
  }
}

// CSP par nonce (ADR 0009) : rendu à la demande ; les appels API restent en cache (revalidate).
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { city, neighborhood: slug } = await params;
  const neighborhood = await loadNeighborhood(city, slug);
  if (!neighborhood) return { title: t.common.notFound };
  return pageMetadata({
    title:
      neighborhood.seo_title ||
      `Location ${neighborhood.name}, ${neighborhood.city.name} : appartements vérifiés`,
    description:
      neighborhood.seo_description ||
      `${neighborhood.property_count} logements vérifiés à ${neighborhood.name} (${neighborhood.city.name}), à la nuit, au mois ou à l'année. Visités et validés par Loka.`,
    path: `/location/${city}/${slug}`,
  });
}

export default async function NeighborhoodPage({ params }: { params: Promise<Params> }) {
  const { city: citySlug, neighborhood: slug } = await params;
  const neighborhood = await loadNeighborhood(citySlug, slug);
  if (!neighborhood) notFound();

  const [properties, cityDetail] = await Promise.all([
    serverApi
      .get<Paginated<PropertyCardData>>(
        "/listings/properties/",
        { neighborhood: slug, city: citySlug, page_size: 12 },
        { revalidate: 300 },
      )
      .catch(() => null),
    serverApi
      .get<CityDetail>(`/geo/cities/${citySlug}/`, undefined, { revalidate: 600 })
      .catch(() => null),
  ]);
  const listings = properties?.results ?? [];
  const siblings = (cityDetail?.neighborhoods ?? []).filter((n) => n.slug !== slug).slice(0, 6);
  const faq = buildNeighborhoodFaq(neighborhood);
  const crumbs = [
    { name: t.nav.home, path: "/" },
    { name: neighborhood.city.name, path: `/location/${citySlug}` },
    { name: neighborhood.name, path: `/location/${citySlug}/${slug}` },
  ];

  return (
    <div className="container py-6 md:py-10">
      <nav aria-label="Fil d'Ariane" className="mb-3 text-sm text-muted-foreground">
        <Link href="/" className="hover:text-foreground">
          {t.nav.home}
        </Link>
        <span className="mx-1">/</span>
        <Link href={`/location/${citySlug}`} className="hover:text-foreground">
          {neighborhood.city.name}
        </Link>
        <span className="mx-1">/</span>
        <span className="text-foreground">{neighborhood.name}</span>
      </nav>

      <header className="max-w-3xl">
        <h1 className="text-display-sm md:text-display-lg">
          Location à {neighborhood.name}, {neighborhood.city.name}
        </h1>
        <p className="mt-3 text-muted-foreground">
          {neighborhood.property_count} {t.city.properties}
          {neighborhood.avg_monthly_price
            ? ` · ${t.city.averagePrice} ${formatTnd(neighborhood.avg_monthly_price)} / mois`
            : ""}
        </p>
        {neighborhood.intro_text && (
          <p className="mt-4 leading-relaxed">{neighborhood.intro_text}</p>
        )}
        <Button className="mt-5" asChild>
          <Link href={`/recherche?city=${citySlug}&neighborhood=${slug}`}>
            {t.city.seeListings}
          </Link>
        </Button>
      </header>

      <section className="mt-10" aria-labelledby="biens">
        <h2 id="biens" className="text-2xl">
          {t.city.listingsIn} {neighborhood.name}
        </h2>
        {listings.length === 0 ? (
          <div className="mt-4 rounded-xl border bg-card p-6">
            <p>Aucun bien vérifié à {neighborhood.name} pour le moment.</p>
            <Button variant="outline" className="mt-3" asChild>
              <Link href={`/location/${citySlug}`}>
                Voir tous les logements à {neighborhood.city.name}
              </Link>
            </Button>
          </div>
        ) : (
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
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

      {siblings.length > 0 && (
        <section className="mt-12" aria-labelledby="autres">
          <h2 id="autres" className="text-xl">
            Autres quartiers de {neighborhood.city.name}
          </h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {siblings.map((n) => (
              <li key={n.slug}>
                <Link
                  href={`/location/${citySlug}/${n.slug}`}
                  className="rounded-full border bg-card px-4 py-2 text-sm hover:bg-accent"
                >
                  {n.name} ({n.property_count})
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
