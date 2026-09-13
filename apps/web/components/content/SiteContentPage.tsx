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

/** Page éditoriale servie depuis l'admin (SiteContent). ISR 10 min, repli si l'API est absente. */
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
          {content.needs_writing && (
            <p className="mt-4 rounded-lg border border-primary/40 bg-accent p-3 text-sm">
              Texte provisoire : le contenu définitif est en cours de rédaction.
            </p>
          )}
          <div className="mt-8">
            <Markdown source={content.body} />
          </div>
        </>
      ) : (
        <p className="mt-6 text-muted-foreground">Contenu indisponible pour le moment.</p>
      )}
    </div>
  );
}
