"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiRequestError, type Query } from "./client";

interface State<T> {
  data: T | null;
  error: ApiRequestError | null;
  loading: boolean;
}

/**
 * Hook de lecture minimal : charge `path` (avec `query`), expose `refetch`.
 * Pas de cache global : les espaces connectés sont peu fréquentés et toujours à jour.
 */
export function useApi<T>(
  path: string | null,
  query?: Query,
): State<T> & { refetch: () => Promise<void> } {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: Boolean(path) });
  const queryKey = JSON.stringify(query ?? {});
  const queryRef = useRef(query);
  queryRef.current = query;

  const load = useCallback(async () => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    try {
      const data = await api.get<T>(path, queryRef.current);
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState({
        data: null,
        error:
          error instanceof ApiRequestError
            ? error
            : new ApiRequestError(0, { detail: String(error) }),
        loading: false,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, queryKey]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, refetch: load };
}
