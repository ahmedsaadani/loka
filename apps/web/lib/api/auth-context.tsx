"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, ApiRequestError, refreshAccessToken, setAccessToken } from "./client";
import type { AuthResponse, Role, User } from "./types";

interface AuthContextValue {
  user: User | null;
  status: "loading" | "anonymous" | "authenticated";
  login: (email: string, password: string) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  loginWithGoogle: (credential: string) => Promise<User>;
  loginWithFacebook: (accessToken: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  role: "traveler" | "host";
  display_name?: string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");

  const loadUser = useCallback(async () => {
    try {
      const me = await api.get<User>("/auth/me/");
      setUser(me);
      setStatus("authenticated");
    } catch {
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    // Marqueur d'hydratation (utilisé par les tests Playwright pour attendre l'interactivité).
    document.documentElement.dataset.hydrated = "1";
    let cancelled = false;
    (async () => {
      const token = await refreshAccessToken();
      if (cancelled) return;
      if (token) await loadUser();
      else setStatus("anonymous");
    })();
    return () => {
      cancelled = true;
    };
  }, [loadUser]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<AuthResponse>("/auth/login/", { email, password });
    setAccessToken(data.access);
    setUser(data.user);
    setStatus("authenticated");
    return data.user;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const data = await api.post<AuthResponse>("/auth/register/", payload);
    setAccessToken(data.access);
    setUser(data.user);
    setStatus("authenticated");
    return data.user;
  }, []);

  const loginWithGoogle = useCallback(async (credential: string) => {
    const data = await api.post<AuthResponse>("/auth/google/", { credential });
    setAccessToken(data.access);
    setUser(data.user);
    setStatus("authenticated");
    return data.user;
  }, []);

  const loginWithFacebook = useCallback(async (accessToken: string) => {
    const data = await api.post<AuthResponse>("/auth/facebook/", { access_token: accessToken });
    setAccessToken(data.access);
    setUser(data.user);
    setStatus("authenticated");
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } catch (error) {
      if (!(error instanceof ApiRequestError)) throw error;
    }
    setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const hasRole = useCallback(
    (...roles: Role[]) => (user ? roles.includes(user.role) : false),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
      register,
      loginWithGoogle,
      loginWithFacebook,
      logout,
      refreshUser: loadUser,
      hasRole,
    }),
    [user, status, login, register, loginWithGoogle, loginWithFacebook, logout, loadUser, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return ctx;
}
