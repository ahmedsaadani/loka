import Link from "next/link";

import { Logo } from "@/components/layout/Logo";
import { t } from "@/lib/i18n";

const EXPLORE = [
  { href: "/location/ariana", label: "Location à Ariana" },
  { href: "/location/tunis", label: "Location à Tunis" },
  { href: "/location/sousse", label: "Location à Sousse" },
  { href: "/location/hammamet", label: "Location à Hammamet" },
  { href: "/recherche?rental_mode=monthly", label: "Location au mois" },
  { href: "/recherche?rental_mode=nightly", label: "Location à la nuit" },
];

const HOSTS = [
  { href: "/devenir-hote", label: "Proposer un bien" },
  { href: "/comment-ca-marche", label: "Comment ça marche" },
  { href: "/hote/inscription", label: "Créer un compte propriétaire" },
];

const LEGAL = [
  { href: "/cgu", label: t.footer.terms },
  { href: "/confidentialite", label: t.footer.privacy },
  { href: "/contact", label: t.footer.contact },
];

export function Footer() {
  return (
    <footer className="mt-16 border-t bg-card">
      <div className="container grid gap-10 py-12 md:grid-cols-4">
        <div className="space-y-3">
          <Logo />
          <p className="max-w-xs text-sm text-muted-foreground">{t.footer.about}</p>
        </div>
        <FooterColumn title={t.footer.explore} links={EXPLORE} />
        <FooterColumn title={t.footer.hosts} links={HOSTS} />
        <FooterColumn title={t.footer.legal} links={LEGAL} />
      </div>
      <div className="border-t">
        <div className="container flex flex-col gap-2 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>
            © {new Date().getFullYear()} Loka. {t.footer.rights}
          </span>
          <span>Tunisie · Prix en dinars (DT), équivalent EUR indicatif.</span>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: Array<{ href: string; label: string }>;
}) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      <ul className="space-y-2 text-sm">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="text-muted-foreground hover:text-foreground">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
