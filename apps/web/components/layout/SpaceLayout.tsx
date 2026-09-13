"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Header } from "@/components/layout/Header";
import { MobileNav } from "@/components/layout/MobileNav";
import { cn } from "@/lib/utils";

export interface SpaceNavItem {
  href: string;
  label: string;
  exact?: boolean;
}

interface Props {
  title: string;
  nav: SpaceNavItem[];
  children: React.ReactNode;
}

/** Coque des espaces connectés : en-tête, navigation latérale (desktop) et barre basse (mobile). */
export function SpaceLayout({ title, nav, children }: Props) {
  const pathname = usePathname();
  return (
    <>
      <Header />
      <div className="container grid gap-6 py-6 pb-24 md:grid-cols-[220px_1fr] md:pb-10">
        <aside className="hidden md:block">
          <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {title}
          </p>
          <nav className="flex flex-col gap-0.5" aria-label={title}>
            {nav.map((item) => {
              const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent",
                    active ? "bg-accent text-accent-foreground" : "text-muted-foreground",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <main className="min-w-0">
          <nav
            className="scrollbar-none mb-4 flex gap-2 overflow-x-auto md:hidden"
            aria-label={title}
          >
            {nav.map((item) => {
              const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "shrink-0 rounded-full border px-3 py-1.5 text-sm",
                    active
                      ? "border-foreground bg-foreground text-background"
                      : "bg-card text-muted-foreground",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          {children}
        </main>
      </div>
      <MobileNav />
    </>
  );
}
