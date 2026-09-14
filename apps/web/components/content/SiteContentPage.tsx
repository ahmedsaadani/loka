import { Markdown } from "@/components/content/Markdown";
import { serverApi } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";

interface SiteContent {
  key: string;
  title: string;
  body: string;
  updated_at: string;
  needs_writing: boolean;
}

interface Props {
  contentKey: string;
  fallbackTitle: string;
}

/** Page éditoriale servie depuis l'admin (SiteContent), cache API 10 min, repli si l'API est absente. */
export async function SiteContentPage({ contentKey, fallbackTitle }: Props) {
  const content = await serverApi
    .get<SiteContent>(`/content/${contentKey}/`, undefined, { revalidate: 600 })
    .catch(() => null);

  return (
    <div className="container max-w-3xl py-10">
      <h1 className="text-3xl md:text-4xl">{content?.title ?? fallbackTitle}</h1>
      {content ? (
        <>
          <p className="mt-2 text-sm text-muted-foreground">
            Dernière mise à jour : {formatDate(content.updated_at)}
          </p>
          {content.needs_writing || !content.body ? (
            // Un texte encore marqué « à rédiger » n'est jamais affiché : l'API le masque.
            <p className="mt-6 rounded-lg border border-primary/40 bg-accent p-4 text-sm">
              Cette page est en cours de rédaction. Pour toute question, écrivez-nous à{" "}
              <a className="underline" href="mailto:contact@loka.tn">
                contact@loka.tn
              </a>
              .
            </p>
          ) : (
            <div className="mt-8">
              <Markdown source={content.body} />
            </div>
          )}
        </>
      ) : (
        <p className="mt-6 text-muted-foreground">Contenu indisponible pour le moment.</p>
      )}
    </div>
  );
}
