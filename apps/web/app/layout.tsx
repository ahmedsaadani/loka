import type { Metadata, Viewport } from "next";
import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/api/auth-context";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

import "@/styles/globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${SITE_NAME} · Logements vérifiés en Tunisie`, template: `%s | ${SITE_NAME}` },
  description:
    "Location d'appartements, studios et villas en Tunisie à la nuit, au mois ou à l'année. Chaque bien est visité, photographié et validé par l'équipe Loka.",
  applicationName: SITE_NAME,
  robots: { index: true, follow: true },
  openGraph: { siteName: SITE_NAME, locale: "fr_TN", type: "website" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f9f7f3",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" dir="ltr">
      <body className="min-h-dvh">
        <AuthProvider>
          {children}
          <Toaster position="top-center" richColors closeButton />
        </AuthProvider>
      </body>
    </html>
  );
}
