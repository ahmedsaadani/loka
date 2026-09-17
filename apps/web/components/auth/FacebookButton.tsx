"use client";

import Script from "next/script";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";

import { ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";

const APP_ID = process.env.NEXT_PUBLIC_FACEBOOK_APP_ID;

interface FbAuthResponse {
  accessToken: string;
}
interface FbLoginResponse {
  authResponse: FbAuthResponse | null;
  status: string;
}
interface FbApi {
  init: (config: { appId: string; cookie: boolean; xfbml: boolean; version: string }) => void;
  login: (cb: (r: FbLoginResponse) => void, opts: { scope: string }) => void;
}

declare global {
  interface Window {
    FB?: FbApi;
    fbAsyncInit?: () => void;
  }
}

/** Bouton « Continuer avec Facebook » (SDK JavaScript Facebook, flux jeton d'accès). */
export function FacebookButton() {
  const { loginWithFacebook } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const initSdk = useCallback(() => {
    if (!APP_ID || !window.FB) return;
    window.FB.init({ appId: APP_ID, cookie: true, xfbml: false, version: "v21.0" });
  }, []);

  const handleClick = useCallback(() => {
    if (!window.FB) {
      setError("Facebook n'est pas encore chargé, réessayez.");
      return;
    }
    setError(null);
    setBusy(true);
    window.FB.login(
      (response) => {
        void (async () => {
          try {
            if (response.status !== "connected" || !response.authResponse) {
              return;
            }
            await loginWithFacebook(response.authResponse.accessToken);
            const next = searchParams.get("next");
            router.push(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
            router.refresh();
          } catch (e) {
            setError(e instanceof ApiRequestError ? e.message : "Connexion Facebook impossible.");
          } finally {
            setBusy(false);
          }
        })();
      },
      { scope: "public_profile,email" },
    );
  }, [loginWithFacebook, router, searchParams]);

  if (!APP_ID) return null;

  return (
    <div className="space-y-2">
      <Script
        src="https://connect.facebook.net/fr_FR/sdk.js"
        strategy="afterInteractive"
        onReady={initSdk}
      />
      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        className="mx-auto flex h-11 w-full max-w-[320px] items-center justify-center gap-2 rounded-md border border-[#1877F2] bg-[#1877F2] px-4 text-sm font-medium text-white transition hover:bg-[#166fe0] disabled:opacity-60"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M24 12c0-6.627-5.373-12-12-12S0 5.373 0 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078V12h3.047V9.356c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874V12h3.328l-.532 3.469h-2.796v8.385C19.612 22.954 24 17.99 24 12z" />
        </svg>
        Continuer avec Facebook
      </button>
      {error && (
        <p className="text-center text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
