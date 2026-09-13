import type { ApiError } from "./types";

/**
 * Client API minimal et typé.
 * - Côté serveur (RSC) : API_INTERNAL_URL (réseau docker), cache/revalidation Next.
 * - Côté client : NEXT_PUBLIC_API_URL, access token en mémoire, refresh automatique via cookie httpOnly.
 */

const PUBLIC_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18000/api/v1";
const INTERNAL_BASE = process.env.API_INTERNAL_URL ?? PUBLIC_BASE;

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly errors: ApiError["errors"];

  constructor(status: number, body: Partial<ApiError>) {
    super(body.detail ?? `Erreur ${status}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = body.code ?? "unknown";
    this.errors = body.errors;
  }

  fieldError(field: string): string | undefined {
    const value = this.errors?.[field];
    if (!value) return undefined;
    return Array.isArray(value) ? value.join(" ") : String(value);
  }
}

export type QueryValue = string | number | boolean | null | undefined | Array<string | number>;
export type Query = Record<string, QueryValue>;

export function buildQuery(query?: Query): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => params.append(key, String(v)));
    } else {
      params.set(key, String(value));
    }
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  query?: Query;
  body?: unknown;
  formData?: FormData;
  token?: string | null;
  next?: NextFetchRequestConfig;
  cache?: RequestCache;
  signal?: AbortSignal;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { detail: text, code: "invalid_json" };
  }
}

async function request<T>(base: string, path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const response = await fetch(`${base}${path}${buildQuery(options.query)}`, {
    method: options.method ?? "GET",
    headers,
    body,
    credentials: "include",
    next: options.next,
    cache: options.cache,
    signal: options.signal,
  });
  const data = await parseBody(response);
  if (!response.ok) {
    throw new ApiRequestError(response.status, (data ?? {}) as Partial<ApiError>);
  }
  return data as T;
}

/** Appels côté serveur (RSC, route handlers). */
export const serverApi = {
  get<T>(path: string, query?: Query, next?: NextFetchRequestConfig): Promise<T> {
    return request<T>(INTERNAL_BASE, path, { query, next: next ?? { revalidate: 300 } });
  },
};

// ---------------------------------------------------------------- client (navigateur)

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** Rafraîchit l'access token via le cookie httpOnly. Une seule requête en vol à la fois. */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const data = await request<{ access: string }>(PUBLIC_BASE, "/auth/refresh/", {
          method: "POST",
        });
        accessToken = data.access;
        return accessToken;
      } catch {
        accessToken = null;
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function clientRequest<T>(path: string, options: RequestOptions, retry = true): Promise<T> {
  try {
    return await request<T>(PUBLIC_BASE, path, { ...options, token: accessToken });
  } catch (error) {
    if (
      error instanceof ApiRequestError &&
      error.status === 401 &&
      retry &&
      !path.startsWith("/auth/")
    ) {
      const token = await refreshAccessToken();
      if (token) return clientRequest<T>(path, options, false);
    }
    throw error;
  }
}

/** Appels côté navigateur, authentifiés si un token est présent. */
export const api = {
  get<T>(path: string, query?: Query, signal?: AbortSignal): Promise<T> {
    return clientRequest<T>(path, { query, cache: "no-store", signal });
  },
  post<T>(path: string, body?: unknown, query?: Query): Promise<T> {
    return clientRequest<T>(path, { method: "POST", body, query });
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return clientRequest<T>(path, { method: "PATCH", body });
  },
  delete<T = null>(path: string): Promise<T> {
    return clientRequest<T>(path, { method: "DELETE" });
  },
  upload<T>(path: string, formData: FormData): Promise<T> {
    return clientRequest<T>(path, { method: "POST", formData });
  },
};

export const API_PUBLIC_BASE = PUBLIC_BASE;
