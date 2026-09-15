"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Currency = "TND" | "EUR" | "USD";

// Taux indicatifs par rapport au dinar (référence des prix côté API). Purement pour l'affichage.
const RATES: Record<Currency, number> = { TND: 1, EUR: 0.29, USD: 0.32 };
const SYMBOLS: Record<Currency, string> = { TND: "DT", EUR: "€", USD: "$" };
export const CURRENCIES: Currency[] = ["TND", "EUR", "USD"];
const STORAGE_KEY = "loka.currency";

interface CurrencyContextValue {
  currency: Currency;
  setCurrency: (c: Currency) => void;
  /** Formate un montant exprimé en dinars vers la devise choisie. */
  format: (amountTnd: number | string) => string;
  /** Suffixe court de la devise (DT, €, $). */
  symbol: string;
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

function formatIn(currency: Currency, amountTnd: number | string): string {
  const value = Number(amountTnd) * RATES[currency];
  if (currency === "TND") {
    return `${new Intl.NumberFormat("fr-TN", { maximumFractionDigits: 0 }).format(value)} DT`;
  }
  return new Intl.NumberFormat(currency === "EUR" ? "fr-FR" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>("TND");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && (CURRENCIES as string[]).includes(saved)) setCurrencyState(saved as Currency);
    } catch {
      // localStorage indisponible : on garde le dinar par défaut.
    }
  }, []);

  const setCurrency = useCallback((c: Currency) => {
    setCurrencyState(c);
    try {
      localStorage.setItem(STORAGE_KEY, c);
    } catch {
      // ignore
    }
  }, []);

  const value = useMemo<CurrencyContextValue>(
    () => ({
      currency,
      setCurrency,
      format: (amount) => formatIn(currency, amount),
      symbol: SYMBOLS[currency],
    }),
    [currency, setCurrency],
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext);
  // Repli sûr hors provider (ex. tests unitaires) : dinar, sans état partagé.
  return (
    ctx ?? {
      currency: "TND",
      setCurrency: () => undefined,
      format: (amount) => formatIn("TND", amount),
      symbol: "DT",
    }
  );
}
