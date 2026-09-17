"use client";

import Script from "next/script";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useRef, useState } from "react";

import { ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdApi {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } };
  }
}

/** Bouton « Continuer avec Google » (Google Identity Services, flux jeton d'identité). */
export function GoogleButton() {
  const { loginWithGoogle } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const holder = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCredential = useCallback(
    async (response: GoogleCredentialResponse) => {
      setError(null);
      try {
        await loginWithGoogle(response.credential);
        const next = searchParams.get("next");
        router.push(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiRequestError ? e.message : "Connexion Google impossible.");
      }
    },
    [loginWithGoogle, router, searchParams],
  );

  const init = useCallback(() => {
    if (!CLIENT_ID || !window.google || !holder.current) return;
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (r) => void handleCredential(r),
    });
    window.google.accounts.id.renderButton(holder.current, {
      theme: "outline",
      size: "large",
      width: 320,
      text: "continue_with",
      locale: "fr",
    });
  }, [handleCredential]);

  if (!CLIENT_ID) return null;

  return (
    <div className="space-y-2">
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={init}
      />
      <div ref={holder} className="flex justify-center" />
      {error && (
        <p className="text-center text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
