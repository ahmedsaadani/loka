import { Mail, MapPin, Phone } from "lucide-react";

import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Contact",
  description: "Contacter l'équipe Loka : questions, partenariats, propriétaires.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <div className="container max-w-3xl py-10">
      <h1 className="text-3xl md:text-4xl">Contact</h1>
      <p className="mt-3 text-muted-foreground">
        Une question sur un logement, une réservation ou pour proposer votre bien ? Notre équipe
        répond sous 24 h ouvrées.
      </p>
      <ul className="mt-8 grid gap-4 sm:grid-cols-3">
        <li className="rounded-xl border bg-card p-5">
          <Mail className="h-5 w-5 text-primary" />
          <p className="mt-2 font-semibold">Email</p>
          <a
            href="mailto:contact@loka.tn"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            contact@loka.tn
          </a>
        </li>
        <li className="rounded-xl border bg-card p-5">
          <Phone className="h-5 w-5 text-primary" />
          <p className="mt-2 font-semibold">Téléphone / WhatsApp</p>
          <p className="text-sm text-muted-foreground">+216 XX XXX XXX (à compléter)</p>
        </li>
        <li className="rounded-xl border bg-card p-5">
          <MapPin className="h-5 w-5 text-primary" />
          <p className="mt-2 font-semibold">Adresse</p>
          <p className="text-sm text-muted-foreground">Tunis, Tunisie (à compléter)</p>
        </li>
      </ul>
    </div>
  );
}
