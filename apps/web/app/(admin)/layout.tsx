import { RequireRole } from "@/components/auth/RequireRole";
import { SpaceLayout } from "@/components/layout/SpaceLayout";

export const metadata = { title: "Back-office Loka", robots: { index: false, follow: false } };

const NAV = [
  { href: "/admin", label: "Tableau de bord", exact: true },
  { href: "/admin/validation", label: "Validation des biens" },
  { href: "/admin/reservations", label: "Réservations" },
  { href: "/admin/identites", label: "Identités" },
  { href: "/admin/avis", label: "Avis" },
  { href: "/admin/leads", label: "Leads" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["staff", "admin"]}>
      <SpaceLayout title="Équipe Loka" nav={NAV}>
        {children}
      </SpaceLayout>
    </RequireRole>
  );
}
