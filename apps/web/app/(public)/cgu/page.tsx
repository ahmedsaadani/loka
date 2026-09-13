import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Conditions d'utilisation",
  description: "Conditions générales d'utilisation de la plateforme Loka.",
  path: "/cgu",
});

export default function TermsPage() {
  return (
    <div className="container max-w-3xl py-10">
      <h1 className="text-3xl md:text-4xl">Conditions d&apos;utilisation</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Dernière mise à jour : septembre 2026. Document de travail à valider par un conseil
        juridique avant mise en production.
      </p>
      <div className="prose-loka mt-8 space-y-6 text-foreground/90">
        <section>
          <h2 className="text-xl">1. Objet</h2>
          <p>
            Loka est une plateforme de mise en relation entre propriétaires et locataires pour des
            hébergements situés en Tunisie. Chaque bien publié a été visité et vérifié par
            l&apos;équipe Loka. Loka n&apos;est pas partie au contrat de location conclu entre
            l&apos;hôte et le voyageur.
          </p>
        </section>
        <section>
          <h2 className="text-xl">2. Comptes</h2>
          <p>
            L&apos;inscription requiert une adresse email valide. Les hôtes s&apos;engagent à
            fournir des informations exactes sur leurs biens et à honorer les réservations
            confirmées. Les documents d&apos;identité sont conservés de façon chiffrée et ne sont
            accessibles qu&apos;à l&apos;équipe Loka, chaque accès étant journalisé.
          </p>
        </section>
        <section>
          <h2 className="text-xl">3. Réservations et acompte</h2>
          <p>
            Une demande de réservation est valable 48 heures. Après acceptation par l&apos;hôte, la
            réservation est confirmée par le paiement d&apos;un acompte. Les frais de service sont
            indiqués avant tout engagement : ils sont à la charge du voyageur pour les locations à
            la nuit et à la charge de l&apos;hôte pour les locations au mois ou à l&apos;année.
          </p>
        </section>
        <section>
          <h2 className="text-xl">4. Annulation</h2>
          <p>
            L&apos;acompte est remboursé au voyageur si l&apos;annulation intervient au moins 7
            jours avant la date d&apos;arrivée, ou si l&apos;annulation est à l&apos;initiative de
            l&apos;hôte. Passé ce délai, l&apos;acompte reste acquis à l&apos;hôte.
          </p>
        </section>
        <section>
          <h2 className="text-xl">5. Responsabilité</h2>
          <p>
            Loka vérifie l&apos;état des biens au moment de la visite. L&apos;hôte demeure
            responsable de la conformité du logement pendant la location. Tout litige est régi par
            le droit tunisien.
          </p>
        </section>
      </div>
    </div>
  );
}
