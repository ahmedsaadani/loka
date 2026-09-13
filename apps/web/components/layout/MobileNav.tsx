"use client";

import { CalendarCheck, Home, LayoutDashboard, Search, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/api/auth-context";
import { cn } from "@/lib/utils";

interface Item {
  href: string;
  label: string;
  icon: typeof Home;
}

/** Navigation basse mobile pour les espaces connectés. */
export function MobileNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  if (!user) return null;

  const items: Item[] = [
    { href: "/", label: "Accueil", icon: Home },
    { href: "/recherche", label: "Recherche", icon: Search },
    { href: "/compte/reservations", label: "Réservations", icon: CalendarCheck },
  ];
  if (user.role === "host" || user.role === "staff" || user.role === "admin") {
    items.push({ href: "/hote", label: "Hôte", icon: LayoutDashboard });
  }
  if (user.role === "staff" || user.role === "admin") {
    items.push({ href: "/admin", label: "Équipe", icon: LayoutDashboard });
  }
  items.push({ href: "/compte", label: "Compte", icon: User });

  return (
    <nav
      className="safe-bottom fixed inset-x-0 bottom-0 z-40 grid border-t bg-card/95 backdrop-blur md:hidden"
      style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      aria-label="Navigation rapide"
    >
      {items.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "tap-target flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium",
              active ? "text-primary" : "text-muted-foreground",
            )}
            aria-current={active ? "page" : undefined}
          >
            <Icon className="h-5 w-5" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
