import { RequireRole } from "@/components/auth/RequireRole";
import { SpaceLayout } from "@/components/layout/SpaceLayout";

export const metadata = { title: "Espace propriétaire", robots: { index: false, follow: false } };

const NAV = [
  { href: "/hote", label: "Tableau de bord", exact: true },
  { href: "/hote/biens", label: "Mes biens" },
  { href: "/hote/demandes", label: "Demandes" },
  { href: "/hote/reservations", label: "Réservations" },
  { href: "/compte", label: "Mon compte" },
];

export default function HostLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["host", "staff", "admin"]}>
      <SpaceLayout title="Espace propriétaire" nav={NAV}>
        {children}
      </SpaceLayout>
    </RequireRole>
  );
}
