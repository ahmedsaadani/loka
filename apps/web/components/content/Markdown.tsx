import type { ReactNode } from "react";

/**
 * Rendu Markdown minimal et sûr (pas de HTML brut) pour les contenus édités dans l'admin :
 * titres (#, ##, ###), paragraphes, listes (-), gras (**texte**), liens [texte](https://…).
 */

function inline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    if (match[1] !== undefined) {
      nodes.push(<strong key={`${keyPrefix}-b${i}`}>{match[1]}</strong>);
    } else if (match[2] !== undefined && match[3] !== undefined) {
      nodes.push(
        <a key={`${keyPrefix}-a${i}`} href={match[3]} className="underline" rel="noopener">
          {match[2]}
        </a>,
      );
    }
    last = match.index + match[0].length;
    i += 1;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function Markdown({ source }: { source: string }) {
  const blocks: ReactNode[] = [];
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      const key = `p${blocks.length}`;
      blocks.push(
        <p key={key} className="leading-relaxed">
          {inline(paragraph.join(" "), key)}
        </p>,
      );
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      const key = `l${blocks.length}`;
      blocks.push(
        <ul key={key} className="list-disc space-y-1 pl-6">
          {list.map((item, i) => (
            <li key={`${key}-${i}`}>{inline(item, `${key}-${i}`)}</li>
          ))}
        </ul>,
      );
      list = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1]!.length;
      const key = `h${blocks.length}`;
      const text = inline(heading[2]!, key);
      if (level === 1)
        blocks.push(
          <h2 key={key} className="mt-8 text-2xl">
            {text}
          </h2>,
        );
      else if (level === 2)
        blocks.push(
          <h2 key={key} className="mt-8 text-xl">
            {text}
          </h2>,
        );
      else
        blocks.push(
          <h3 key={key} className="mt-6 text-lg">
            {text}
          </h3>,
        );
      continue;
    }
    if (/^-\s+/.test(line)) {
      flushParagraph();
      list.push(line.replace(/^-\s+/, ""));
      continue;
    }
    if (line === "") {
      flushParagraph();
      flushList();
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  return <div className="space-y-4 text-foreground/90">{blocks}</div>;
}
