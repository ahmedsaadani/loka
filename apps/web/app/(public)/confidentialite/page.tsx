import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Politique de confidentialité",
  description: "Comment Loka collecte, utilise et protège vos données personnelles.",
  path: "/confidentialite",
});

export default function PrivacyPage() {
  return (
    <div className="container max-w-3xl py-10">
      <h1 className="text-3xl md:text-4xl">Politique de confidentialité</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Dernière mise à jour : septembre 2026. Document de travail à valider avant mise en
        production (loi organique n° 2004-63 sur la protection des données personnelles).
      </p>
      <div className="mt-8 space-y-6 text-foreground/90">
        <section>
          <h2 className="text-xl">Données collectées</h2>
          <p>
            Email, nom, téléphone, rôle (voyageur ou hôte), demandes et réservations. Pour les hôtes
            : adresse des biens, coordonnées bancaires masquées et pièce d&apos;identité pour la
            vérification.
          </p>
        </section>
        <section>
          <h2 className="text-xl">Utilisation</h2>
          <p>
            Mise en relation, traitement des réservations, envoi des emails transactionnels,
            vérification des biens et des identités, prévention de la fraude.
          </p>
        </section>
        <section>
          <h2 className="text-xl">Protection</h2>
          <p>
            L&apos;adresse exacte d&apos;un bien n&apos;est communiquée au voyageur qu&apos;après
            confirmation. Les pièces d&apos;identité et contrats sont stockés dans un espace privé
            accessible uniquement via des liens signés de courte durée ; chaque accès est
            journalisé.
          </p>
        </section>
        <section>
          <h2 className="text-xl">Vos droits</h2>
          <p>
            Vous pouvez demander l&apos;accès, la rectification ou la suppression de vos données via
            la page contact.
          </p>
        </section>
      </div>
    </div>
  );
}
