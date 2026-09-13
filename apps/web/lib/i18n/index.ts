import { fr, type Dictionary } from "./fr";

export type Locale = "fr" | "ar" | "en";

export const DEFAULT_LOCALE: Locale = "fr";
export const LOCALES: Locale[] = ["fr", "ar", "en"];
export const RTL_LOCALES: Locale[] = ["ar"];

const dictionaries: Record<Locale, Dictionary> = {
  fr,
  // AR / EN : contenu FR en attendant les traductions (structure identique).
  ar: fr,
  en: fr,
};

export function getDictionary(locale: Locale = DEFAULT_LOCALE): Dictionary {
  return dictionaries[locale];
}

export function isRtl(locale: Locale): boolean {
  return RTL_LOCALES.includes(locale);
}

/** Raccourci pour les composants : `const t = useT();` (client) ou `getDictionary()` (serveur). */
export const t = fr;
