"""
Rendu Markdown minimal, miroir exact de `apps/web/components/content/Markdown.tsx`.

Sert à l'aperçu de l'écran admin « Contenus à rédiger » : ce que l'équipe voit dans l'aperçu
est ce que le front affichera. Sous-ensemble volontaire : titres (#, ##, ###), paragraphes,
listes (-), gras (**texte**), liens [texte](https://… ou mailto:…). Aucun HTML brut n'est
interprété : tout le texte est échappé.
"""

from __future__ import annotations

import re
from html import escape

_INLINE = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)")
_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_LIST_ITEM = re.compile(r"^-\s+")


def _inline(text: str) -> str:
    out: list[str] = []
    last = 0
    for match in _INLINE.finditer(text):
        out.append(escape(text[last : match.start()]))
        if match.group(1) is not None:
            out.append(f"<strong>{escape(match.group(1))}</strong>")
        else:
            href = escape(match.group(3), quote=True)
            out.append(f'<a href="{href}" rel="noopener">{escape(match.group(2))}</a>')
        last = match.end()
    out.append(escape(text[last:]))
    return "".join(out)


def render_markdown(source: str) -> str:
    """Retourne un fragment HTML sûr (texte échappé) pour le sous-ensemble supporté."""
    blocks: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if items:
            blocks.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for raw in source.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            tag = "h3" if len(heading.group(1)) == 3 else "h2"
            blocks.append(f"<{tag}>{_inline(heading.group(2))}</{tag}>")
            continue
        if _LIST_ITEM.match(line):
            flush_paragraph()
            items.append(_LIST_ITEM.sub("", line, count=1))
            continue
        if line == "":
            flush_paragraph()
            flush_list()
            continue
        flush_list()
        paragraph.append(line)
    flush_paragraph()
    flush_list()
    return "\n".join(blocks)
