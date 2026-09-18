import { RequireRole } from "@/components/auth/RequireRole";
import { SpaceLayout } from "@/components/layout/SpaceLayout";

export const metadata = { title: "Mon compte", robots: { index: false, follow: false } };

const NAV = [
  { href: "/compte", label: "Mon profil", exact: true },
  { href: "/compte/demandes", label: "Mes demandes" },
  { href: "/compte/reservations", label: "Mes réservations" },
  { href: "/compte/avis", label: "Mes avis" },
  { href: "/compte/identite", label: "Identité" },
];

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["traveler", "host", "staff", "admin"]}>
      <SpaceLayout title="Mon compte" nav={NAV}>
        {children}
      </SpaceLayout>
    </RequireRole>
  );
}
