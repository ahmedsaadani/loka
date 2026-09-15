"use client";

import { Heart, LogOut, Menu, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { CurrencySwitcher } from "@/components/layout/CurrencySwitcher";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/api/auth-context";
import { t } from "@/lib/i18n";

const PUBLIC_LINKS = [
  { href: "/recherche", label: t.nav.search },
  { href: "/#villes", label: t.nav.cities },
  { href: "/comment-ca-marche", label: t.nav.howItWorks },
];

function spaceLinks(role: string): Array<{ href: string; label: string }> {
  const links: Array<{ href: string; label: string }> = [
    { href: "/compte/reservations", label: t.nav.myBookings },
    { href: "/compte/demandes", label: t.nav.myRequests },
  ];
  if (role === "host" || role === "staff" || role === "admin")
    links.push({ href: "/hote", label: t.nav.hostSpace });
  if (role === "staff" || role === "admin") links.push({ href: "/admin", label: t.nav.adminSpace });
  return links;
}

export function Header() {
  const { user, status, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  async function handleLogout() {
    await logout();
    setOpen(false);
    router.push("/");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Logo />

        <nav className="hidden items-center gap-1 md:flex" aria-label="Navigation principale">
          {PUBLIC_LINKS.map((link) => (
            <Button key={link.href} variant="ghost" asChild>
              <Link href={link.href}>{link.label}</Link>
            </Button>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" size="icon" asChild aria-label="Mes favoris">
            <Link href="/favoris">
              <Heart className="h-5 w-5" />
            </Link>
          </Button>
          <CurrencySwitcher />
          {status === "loading" && <Skeleton className="h-10 w-28" />}
          {status === "anonymous" && (
            <>
              <Button variant="ghost" asChild>
                <Link href="/devenir-hote">{t.nav.host}</Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/connexion">{t.nav.login}</Link>
              </Button>
            </>
          )}
          {status === "authenticated" && user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <UserIcon />
                  <span className="max-w-[10rem] truncate">{user.first_name || user.email}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="truncate font-normal text-muted-foreground">
                  {user.email}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {spaceLinks(user.role).map((link) => (
                  <DropdownMenuItem key={link.href} asChild>
                    <Link href={link.href}>{link.label}</Link>
                  </DropdownMenuItem>
                ))}
                <DropdownMenuItem asChild>
                  <Link href="/compte">{t.nav.account}</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={handleLogout}>
                  <LogOut /> {t.nav.logout}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden" aria-label={t.nav.menu}>
              <Menu className="!size-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="flex flex-col">
            <SheetTitle>
              <Logo />
            </SheetTitle>
            <nav className="mt-6 flex flex-col gap-1" aria-label="Navigation mobile">
              {PUBLIC_LINKS.map((link) => (
                <Button
                  key={link.href}
                  variant="ghost"
                  className="justify-start text-base"
                  asChild
                  onClick={() => setOpen(false)}
                >
                  <Link href={link.href}>{link.label}</Link>
                </Button>
              ))}
              {status === "authenticated" && user && (
                <>
                  <div className="my-2 border-t" />
                  {spaceLinks(user.role).map((link) => (
                    <Button
                      key={link.href}
                      variant="ghost"
                      className="justify-start text-base"
                      asChild
                      onClick={() => setOpen(false)}
                    >
                      <Link href={link.href}>{link.label}</Link>
                    </Button>
                  ))}
                  <Button
                    variant="ghost"
                    className="justify-start text-base"
                    asChild
                    onClick={() => setOpen(false)}
                  >
                    <Link href="/compte">{t.nav.account}</Link>
                  </Button>
                </>
              )}
            </nav>
            <div className="mt-auto flex flex-col gap-2">
              {status === "anonymous" && (
                <>
                  <Button asChild onClick={() => setOpen(false)}>
                    <Link href="/connexion">{t.nav.login}</Link>
                  </Button>
                  <Button variant="outline" asChild onClick={() => setOpen(false)}>
                    <Link href="/devenir-hote">{t.nav.host}</Link>
                  </Button>
                </>
              )}
              {status === "authenticated" && (
                <Button variant="outline" onClick={handleLogout}>
                  <LogOut /> {t.nav.logout}
                </Button>
              )}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
