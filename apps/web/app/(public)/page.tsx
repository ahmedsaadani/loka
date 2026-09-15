import { BadgeCheck, CalendarClock, Camera, MapPin, ShieldCheck, Star } from "lucide-react";
import Image from "next/image";
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
    "Studios, S+1, S+2, villas et colocations à Ariana, Tunis, Sousse et Hammamet. Chaque logement est visité, photographié et validé par l'équipe Loka avant publication.",
  path: "/",
});

const HERO = "/demo-photos/villa_piscine-07-a0mhcnwhgOE_gallery.webp";

// Image d'illustration par ville (photos de démonstration). Repli sur une façade générique.
const CITY_IMAGE: Record<string, string> = {
  ariana: "/demo-photos/facade-03-adHR6lRLp2c_gallery.webp",
  tunis: "/demo-photos/facade-01-v4Di0A7aj3I_gallery.webp",
  sousse: "/demo-photos/balcon_vue-03-N1DlQkl2V2c_gallery.webp",
  hammamet: "/demo-photos/villa_piscine-09-QWs-xsZ0wBs_gallery.webp",
};
const CITY_FALLBACK = "/demo-photos/facade-02-_UYe-zupvzA_gallery.webp";

const CATEGORIES = [
  {
    label: "Villas avec piscine",
    caption: "Pour les vacances en famille",
    href: "/recherche?property_type=villa",
    image: "/demo-photos/villa_piscine-01-OwWbUOIbhDY_gallery.webp",
  },
  {
    label: "Bord de mer",
    caption: "Hammamet, Sousse, La Marsa",
    href: "/recherche?city=hammamet",
    image: "/demo-photos/balcon_vue-01-ZGMeWNJJlAs_gallery.webp",
  },
  {
    label: "Studios & colocations",
    caption: "Près des facs et d'ESPRIT",
    href: "/recherche?property_type=studio",
    image: "/demo-photos/studio-03-5aJpyxXaCyA_gallery.webp",
  },
  {
    label: "Location au mois",
    caption: "S'installer sans agence",
    href: "/recherche?rental_mode=monthly",
    image: "/demo-photos/salon-04-gQwmhH2PRqY_gallery.webp",
  },
];

const TRUST = [
  { icon: MapPin, text: "Visité sur place" },
  { icon: Camera, text: "Photos réelles de l'équipe" },
  { icon: ShieldCheck, text: "Identité du propriétaire vérifiée" },
  { icon: CalendarClock, text: "À la nuit, au mois ou à l'année" },
];

const STEP_ICONS = [ShieldCheck, CalendarClock, BadgeCheck];

async function loadHome(): Promise<{ cities: CitySummary[]; latest: PropertyCardData[] }> {
  try {
    const [cities, latest] = await Promise.all([
      serverApi.get<Paginated<CitySummary>>("/geo/cities/", { page_size: 12 }),
      serverApi.get<Paginated<PropertyCardData>>("/listings/properties/", { page_size: 8 }),
    ]);
    return { cities: cities.results, latest: latest.results };
  } catch {
    return { cities: [], latest: [] };
  }
}

export default async function HomePage() {
  const { cities, latest } = await loadHome();
  const featured = cities.filter((c) => c.is_featured || c.property_count > 0).slice(0, 8);
  const totalListings = cities.reduce((sum, c) => sum + (c.property_count ?? 0), 0);

  return (
    <>
      {/* Hero photographique */}
      <section className="relative isolate overflow-hidden">
        <Image
          src={HERO}
          alt="Villa avec piscine et vue sur la mer en Tunisie"
          fill
          priority
          sizes="100vw"
          className="-z-10 object-cover"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-black/55 via-black/35 to-black/55" />
        <div className="container flex min-h-[520px] flex-col justify-center py-14 md:py-20">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-sm font-medium text-white backdrop-blur">
              <ShieldCheck className="h-4 w-4" /> Chaque logement vérifié par notre équipe
            </span>
            <h1 className="mt-4 text-3xl font-semibold leading-tight text-white drop-shadow-sm md:text-5xl">
              {t.home.heroTitle}
            </h1>
            <p className="mt-4 max-w-xl text-base text-white/90 md:text-lg">
              {t.home.heroSubtitle}
            </p>
          </div>
          <div className="mt-8 rounded-2xl bg-background/95 p-3 shadow-float backdrop-blur md:p-4">
            <SearchBar cities={cities} />
          </div>
          <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/90">
            {TRUST.map((item) => (
              <li key={item.text} className="inline-flex items-center gap-2">
                <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" /> {item.text}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Bande de repères */}
      <section className="border-b bg-card" aria-label="Loka en chiffres">
        <div className="container grid grid-cols-2 gap-6 py-6 md:grid-cols-4">
          <Stat value={`${totalListings || "—"}`} label="logements vérifiés" />
          <Stat value={`${cities.length || 4}`} label="villes couvertes" />
          <Stat value="100 %" label="visités et photographiés" />
          <Stat value="Nuit · Mois · An" label="durées flexibles" />
        </div>
      </section>

      {/* Catégories visuelles */}
      <section className="container py-12 md:py-16" aria-labelledby="categories-titre">
        <h2 id="categories-titre" className="text-2xl md:text-3xl">
          Explorer par envie
        </h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.label}
              href={cat.href}
              className="group relative aspect-[4/5] overflow-hidden rounded-2xl shadow-card transition-shadow hover:shadow-float"
            >
              <Image
                src={cat.image}
                alt={cat.label}
                fill
                sizes="(min-width:1024px) 25vw, (min-width:640px) 50vw, 100vw"
                className="object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-4 text-white">
                <p className="text-lg font-semibold">{cat.label}</p>
                <p className="text-sm text-white/85">{cat.caption}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Villes populaires — cartes avec image */}
      <section
        id="villes"
        className="border-y bg-card py-12 md:py-16"
        aria-labelledby="villes-titre"
      >
        <div className="container">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 id="villes-titre" className="text-2xl md:text-3xl">
                {t.home.popularCities}
              </h2>
              <p className="mt-1 text-muted-foreground">
                Des logements vérifiés dans les villes les plus demandées de Tunisie.
              </p>
            </div>
          </div>
          {featured.length === 0 ? (
            <p className="text-muted-foreground">Les premières villes arrivent bientôt.</p>
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {featured.map((city) => (
                <li key={city.slug}>
                  <Link
                    href={`/location/${city.slug}`}
                    className="group relative flex aspect-[3/2] items-end overflow-hidden rounded-2xl shadow-card transition-shadow hover:shadow-float"
                  >
                    <Image
                      src={CITY_IMAGE[city.slug] ?? CITY_FALLBACK}
                      alt={`Location à ${city.name}`}
                      fill
                      sizes="(min-width:1024px) 25vw, (min-width:640px) 50vw, 100vw"
                      className="object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent" />
                    <div className="relative p-4 text-white">
                      <p className="text-xl font-semibold">{city.name}</p>
                      <p className="text-sm text-white/85">
                        {city.property_count} {t.city.properties}
                        {city.avg_monthly_price
                          ? ` · dès ${formatTnd(city.avg_monthly_price)} / mois`
                          : ""}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* Derniers biens vérifiés */}
      <section className="container py-12 md:py-16" aria-labelledby="verifies-titre">
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
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
      </section>

      {/* Comment ça marche */}
      <section
        id="comment-ca-marche"
        className="border-t bg-card py-12 md:py-16"
        aria-labelledby="comment-titre"
      >
        <div className="container">
          <h2 id="comment-titre" className="text-2xl md:text-3xl">
            {t.home.howTitle}
          </h2>
          <ol className="mt-6 grid gap-6 md:grid-cols-3">
            {t.home.steps.map((step, index) => {
              const Icon = STEP_ICONS[index] ?? ShieldCheck;
              return (
                <li key={step.title} className="rounded-2xl border bg-background p-6 shadow-card">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-verified-soft text-verified">
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
        </div>
      </section>

      {/* Bandeau propriétaires */}
      <section className="container py-12 md:py-16">
        <div className="relative overflow-hidden rounded-3xl bg-foreground px-6 py-10 text-background md:px-12 md:py-14">
          <Star
            className="absolute -right-6 -top-6 h-40 w-40 text-background/5"
            aria-hidden="true"
          />
          <div className="relative flex flex-col items-start gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl md:text-3xl">{t.home.hostCtaTitle}</h2>
              <p className="mt-2 max-w-xl text-background/80">{t.home.hostCtaText}</p>
            </div>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/devenir-hote">{t.home.hostCta}</Link>
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center md:text-left">
      <p className="text-2xl font-semibold md:text-3xl">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
