"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "loka.favorites";

interface FavoritesContextValue {
  favorites: string[];
  isFavorite: (publicId: string) => boolean;
  toggle: (publicId: string) => void;
  ready: boolean;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

/** Favoris locaux (cœur), conservés dans le navigateur. Aucune donnée envoyée au serveur. */
export function FavoritesProvider({ children }: { children: React.ReactNode }) {
  const [favorites, setFavorites] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setFavorites(JSON.parse(raw) as string[]);
    } catch {
      // ignore
    }
    setReady(true);
  }, []);

  const persist = useCallback((next: string[]) => {
    setFavorites(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  }, []);

  const value = useMemo<FavoritesContextValue>(
    () => ({
      favorites,
      ready,
      isFavorite: (id) => favorites.includes(id),
      toggle: (id) =>
        persist(favorites.includes(id) ? favorites.filter((f) => f !== id) : [...favorites, id]),
    }),
    [favorites, ready, persist],
  );

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  return ctx ?? { favorites: [], ready: false, isFavorite: () => false, toggle: () => undefined };
}
