import type { CityDetail, CitySummary, NeighborhoodDetail } from "./api/types";
import { formatTnd } from "./utils";

export interface FaqItem {
  question: string;
  answer: string;
}

export function buildCityFaq(
  city: CitySummary & { neighborhoods?: CityDetail["neighborhoods"] },
): FaqItem[] {
  const faq: FaqItem[] = [
    {
      question: `Combien coûte un appartement meublé à ${city.name} ?`,
      answer: city.avg_monthly_price
        ? `Le loyer mensuel moyen des biens vérifiés par Loka à ${city.name} est d'environ ${formatTnd(city.avg_monthly_price)} par mois, charges variables selon le bien.`
        : `Les loyers dépendent du quartier et de la surface. Consultez les biens vérifiés à ${city.name} pour les prix actuels.`,
    },
    {
      question: `Peut-on louer à la nuit ou pour quelques mois à ${city.name} ?`,
      answer: `Oui. Chaque bien Loka indique ses modes de location : nuitée, mensuel (1 à 11 mois) ou annuel, avec un tarif propre à chaque durée.`,
    },
    {
      question: `Les annonces à ${city.name} sont-elles vérifiées ?`,
      answer: `Toutes. L'équipe Loka visite chaque logement, prend les photos et évalue l'état du bien avant publication. Aucune annonce non vérifiée n'est en ligne.`,
    },
  ];
  if (city.neighborhoods && city.neighborhoods.length > 0) {
    faq.push({
      question: `Quels sont les quartiers les plus demandés à ${city.name} ?`,
      answer: city.neighborhoods
        .slice(0, 4)
        .map((n) => n.name)
        .join(", "),
    });
  }
  return faq;
}

export function buildNeighborhoodFaq(neighborhood: NeighborhoodDetail): FaqItem[] {
  const cityName = neighborhood.city.name;
  return [
    {
      question: `Quel est le loyer moyen à ${neighborhood.name} (${cityName}) ?`,
      answer: neighborhood.avg_monthly_price
        ? `Environ ${formatTnd(neighborhood.avg_monthly_price)} par mois pour les logements vérifiés par Loka à ${neighborhood.name}.`
        : `Les prix varient selon la surface et l'état du bien. Les logements vérifiés à ${neighborhood.name} affichent leur tarif par nuit, par mois ou à l'année.`,
    },
    {
      question: `Comment réserver un logement à ${neighborhood.name} ?`,
      answer: `Envoyez une demande depuis la fiche du bien avec un devis instantané. L'hôte répond sous 48 h, puis vous confirmez en payant un acompte sécurisé. L'adresse exacte est communiquée à la confirmation.`,
    },
    {
      question: `Les logements à ${neighborhood.name} sont-ils visités par Loka ?`,
      answer: `Oui, chaque bien publié a été visité, photographié et évalué sur place par l'équipe Loka.`,
    },
  ];
}
