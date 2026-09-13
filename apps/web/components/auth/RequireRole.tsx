"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { PropertyGridSkeleton } from "@/components/listing/PropertyCardSkeleton";
import { useAuth } from "@/lib/api/auth-context";
import type { Role } from "@/lib/api/types";

interface Props {
  roles: Role[];
  children: React.ReactNode;
}

/**
 * Garde côté client des espaces connectés. Anonyme → /connexion?next=… ; mauvais rôle → accueil.
 * La sécurité réelle est appliquée par l'API (permissions objet par objet).
 */
export function RequireRole({ roles, children }: Props) {
  const { status, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") router.replace(`/connexion?next=${encodeURIComponent(pathname)}`);
    else if (status === "authenticated" && user && !roles.includes(user.role)) router.replace("/");
  }, [status, user, roles, router, pathname]);

  if (status !== "authenticated" || !user || !roles.includes(user.role)) {
    return (
      <div className="container py-8" aria-busy="true">
        <PropertyGridSkeleton count={3} />
      </div>
    );
  }
  return <>{children}</>;
}
