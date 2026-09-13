#!/usr/bin/env python
"""Constitue la banque locale de photos de démonstration (apps/api/seed/photos/).

Sources autorisées : Unsplash (licence Unsplash) et Pexels (licence Pexels) uniquement.

Trois modes, du plus simple au plus riche :

1. Sans clé (défaut) : la liste vérifiée ``sources.json`` (identifiants de photos Unsplash
   relevés à la main, avec auteur) est téléchargée depuis le CDN ``images.unsplash.com``.
2. ``UNSPLASH_ACCESS_KEY`` défini : les métadonnées (auteur, lien de la page, description)
   sont rafraîchies via l'API officielle avant téléchargement (``/photos/{id}``), et le
   téléchargement est déclaré via ``links.download_location`` comme l'exigent les
   conditions de l'API.
3. ``PEXELS_API_KEY`` défini et ``--pexels-query CATEGORIE=REQUETE`` : complète une catégorie
   avec l'API de recherche Pexels (``/v1/search``).

Chaque image est vérifiée (HTTP 200, décodage Pillow, taille minimale) et ré-encodée en
JPEG ; ``CREDITS.md`` est régénéré à chaque exécution. Le script est idempotent : un
fichier déjà présent n'est pas retéléchargé (``--force`` pour tout refaire).

Usage :
    python scripts/fetch_seed_photos.py            # télécharge ce qui manque
    python scripts/fetch_seed_photos.py --check    # vérifie la banque sans réseau
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PHOTOS_DIR = ROOT / "apps" / "api" / "seed" / "photos"
SOURCES = PHOTOS_DIR / "sources.json"
MANIFEST = PHOTOS_DIR / "manifest.json"
CREDITS = PHOTOS_DIR / "CREDITS.md"

MIN_SIDE = 800
MAX_SIDE = 1600
USER_AGENT = "loka-seed-photos/1.0 (+https://gitlab.com/loka)"

CATEGORY_LABELS = {
    "salon": "Salon / séjour",
    "chambre": "Chambre",
    "cuisine": "Cuisine",
    "salle_de_bain": "Salle de bain",
    "balcon_vue": "Balcon, terrasse, vue",
    "facade": "Façade d'immeuble",
    "villa_piscine": "Villa avec piscine",
    "villa_exterieur": "Villa, extérieur et jardin",
    "studio": "Studio",
    "chambre_etudiante": "Chambre étudiante / colocation",
}


@dataclass
class Photo:
    category: str
    file: str
    source: str  # "unsplash" | "pexels"
    page_url: str
    author: str
    author_url: str
    licence: str
    width: int
    height: int


def _get(url: str, headers: dict[str, str] | None = None, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - https only
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} for {url}")
                return resp.read()
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"échec après {retries} tentatives : {url} ({last})")


def _encode(raw: bytes) -> tuple[bytes, int, int]:
    """Décode, vérifie la taille, borne le grand côté et ré-encode en JPEG propre."""
    with Image.open(io.BytesIO(raw)) as img:
        img.load()
        img = img.convert("RGB")
        w, h = img.size
        if min(w, h) < MIN_SIDE:
            raise ValueError(f"image trop petite ({w}x{h})")
        scale = min(1.0, MAX_SIDE / max(w, h))
        if scale < 1.0:
            img = img.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=86, optimize=True, progressive=True)
        return out.getvalue(), img.size[0], img.size[1]


# ----------------------------------------------------------------------------- Unsplash
def unsplash_meta(page_id: str, key: str) -> dict[str, str]:
    data = json.loads(
        _get(
            f"https://api.unsplash.com/photos/{page_id}",
            headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
        )
    )
    # Déclaration du téléchargement, exigée par les conditions de l'API Unsplash.
    try:
        _get(data["links"]["download_location"], headers={"Authorization": f"Client-ID {key}"})
    except RuntimeError as exc:  # pragma: no cover - réseau
        print(f"  ! download_location non déclaré pour {page_id} : {exc}", file=sys.stderr)
    return {
        "author": data["user"]["name"],
        "author_url": data["user"]["links"]["html"],
        "page_url": data["links"]["html"],
        "raw": data["urls"]["raw"],
    }


def fetch_unsplash(entries: list[dict[str, str]], params: str, key: str | None, force: bool) -> list[Photo]:
    photos: list[Photo] = []
    counters: dict[str, int] = {}
    for entry in entries:
        cat = entry["category"]
        counters[cat] = counters.get(cat, 0) + 1
        file = f"{cat}-{counters[cat]:02d}-{entry['page']}.jpg"
        target = PHOTOS_DIR / file
        author = entry["author"]
        author_url = f"https://unsplash.com/@{entry['handle']}"
        page_url = f"https://unsplash.com/photos/{entry['page']}"
        url = f"https://images.unsplash.com/photo-{entry['cdn']}?{params}"
        if key:
            meta = unsplash_meta(entry["page"], key)
            author, author_url, page_url = meta["author"], meta["author_url"], meta["page_url"]
            url = f"{meta['raw']}&{params}"
        if target.exists() and not force:
            with Image.open(target) as img:
                w, h = img.size
        else:
            print(f"  + {file}")
            data, w, h = _encode(_get(url))
            target.write_bytes(data)
        photos.append(
            Photo(cat, file, "unsplash", page_url, author, author_url, "Unsplash License", w, h)
        )
    return photos


# ------------------------------------------------------------------------------- Pexels
def fetch_pexels(category: str, query: str, key: str, count: int, start: int, force: bool) -> list[Photo]:
    q = urllib.parse.urlencode({"query": query, "per_page": count, "orientation": "landscape"})
    data = json.loads(_get(f"https://api.pexels.com/v1/search?{q}", headers={"Authorization": key}))
    photos: list[Photo] = []
    for i, item in enumerate(data.get("photos", []), start=start + 1):
        file = f"{category}-{i:02d}-pexels-{item['id']}.jpg"
        target = PHOTOS_DIR / file
        if target.exists() and not force:
            with Image.open(target) as img:
                w, h = img.size
        else:
            print(f"  + {file}")
            raw, w, h = _encode(_get(item["src"]["large2x"]))
            target.write_bytes(raw)
        photos.append(
            Photo(
                category, file, "pexels", item["url"], item["photographer"],
                item["photographer_url"], "Pexels License", w, h,
            )
        )
    return photos


# ------------------------------------------------------------------------------ sorties
def write_outputs(photos: list[Photo]) -> None:
    MANIFEST.write_text(
        json.dumps([asdict(p) for p in photos], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Crédits des photos de démonstration",
        "",
        "> **Avertissement.** Ces photos servent uniquement à peupler l'environnement de démonstration",
        "> (commande `seed`). Elles ne représentent aucun bien réel et **ne doivent jamais être utilisées",
        "> pour une annonce réelle** ni présentées comme des photos prises par l'équipe Loka. Chaque",
        "> annonce réelle doit être illustrée par des photos prises sur place par l'équipe.",
        "",
        "Sources autorisées : [Unsplash](https://unsplash.com/license) et [Pexels](https://www.pexels.com/license/)",
        "uniquement. Les deux licences autorisent l'usage commercial et la modification sans attribution",
        "obligatoire ; l'attribution ci-dessous est fournie par courtoisie.",
        "",
        f"Banque générée par `scripts/fetch_seed_photos.py` ({len(photos)} photos).",
        "",
    ]
    for cat, label in CATEGORY_LABELS.items():
        rows = [p for p in photos if p.category == cat]
        if not rows:
            continue
        lines += [f"## {label} ({len(rows)})", "", "| Fichier | Auteur | Source | Licence |", "|---|---|---|---|"]
        for p in rows:
            lines.append(
                f"| `{p.file}` | [{p.author}]({p.author_url}) | [{p.source}]({p.page_url}) | {p.licence} |"
            )
        lines.append("")
    CREDITS.write_text("\n".join(lines), encoding="utf-8")


def check_bank() -> int:
    if not MANIFEST.exists():
        print("manifest.json absent : lancez le script sans --check", file=sys.stderr)
        return 1
    photos = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = 0
    for p in photos:
        path = PHOTOS_DIR / p["file"]
        try:
            with Image.open(path) as img:
                img.verify()
        except Exception as exc:  # noqa: BLE001
            print(f"  x {p['file']} : {exc}")
            bad += 1
    print(f"{len(photos) - bad}/{len(photos)} photos valides")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="retélécharge tout")
    parser.add_argument("--check", action="store_true", help="vérifie la banque locale sans réseau")
    parser.add_argument(
        "--pexels-query",
        action="append",
        default=[],
        metavar="CATEGORIE=REQUETE",
        help="complète une catégorie via l'API Pexels (PEXELS_API_KEY requis)",
    )
    parser.add_argument("--pexels-count", type=int, default=6)
    args = parser.parse_args()

    if args.check:
        return check_bank()

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY") or None
    pexels_key = os.environ.get("PEXELS_API_KEY") or None
    print(f"Unsplash : {'API' if unsplash_key else 'liste vérifiée sources.json (sans clé)'}")

    photos = fetch_unsplash(sources["photos"], sources["params"], unsplash_key, args.force)

    for spec in args.pexels_query:
        if not pexels_key:
            print("PEXELS_API_KEY absent : --pexels-query ignoré", file=sys.stderr)
            break
        category, _, query = spec.partition("=")
        if category not in CATEGORY_LABELS:
            parser.error(f"catégorie inconnue : {category}")
        start = sum(1 for p in photos if p.category == category)
        photos += fetch_pexels(category, query, pexels_key, args.pexels_count, start, args.force)

    write_outputs(photos)
    by_cat = {c: sum(1 for p in photos if p.category == c) for c in CATEGORY_LABELS}
    print(json.dumps(by_cat, ensure_ascii=False))
    print(f"{len(photos)} photos dans {PHOTOS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
