"""
Contenus éditoriaux et marqueur « [À RÉDIGER] ».

- `is_placeholder` / `public_text` : un texte encore marqué n'est jamais exposé par l'API
  publique (le front masque la section).
- `PENDING_FIELDS` + `pending_entries` : inventaire des champs à rédiger, utilisé par
  l'écran admin « Contenus à rédiger » et par les vérifications système.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import models

from core.checks import PLACEHOLDER


def is_placeholder(text: str | None) -> bool:
    return bool(text) and PLACEHOLDER in (text or "")


def public_text(text: str | None) -> str:
    """Texte tel qu'exposé au public : vide tant qu'il est marqué à rédiger."""
    if not text or is_placeholder(text):
        return ""
    return text


@dataclass(frozen=True)
class ContentField:
    model: type[models.Model]
    kind: str  # city | neighborhood | page
    field: str
    label: str
    markdown: bool
    admin_url_name: str  # <app>_<model>_change


def content_fields() -> list[ContentField]:
    from core.models import SiteContent
    from geo.models import City, Neighborhood

    return [
        ContentField(City, "city", "intro_text", "Texte d'introduction", True, "geo_city_change"),
        ContentField(City, "city", "seo_title", "Titre SEO", False, "geo_city_change"),
        ContentField(City, "city", "seo_description", "Description SEO", False, "geo_city_change"),
        ContentField(
            Neighborhood,
            "neighborhood",
            "intro_text",
            "Texte d'introduction",
            True,
            "geo_neighborhood_change",
        ),
        ContentField(
            Neighborhood, "neighborhood", "seo_title", "Titre SEO", False, "geo_neighborhood_change"
        ),
        ContentField(
            Neighborhood,
            "neighborhood",
            "seo_description",
            "Description SEO",
            False,
            "geo_neighborhood_change",
        ),
        ContentField(
            SiteContent, "page", "title", "Titre de la page", False, "core_sitecontent_change"
        ),
        ContentField(
            SiteContent, "page", "body", "Corps de la page", True, "core_sitecontent_change"
        ),
    ]


@dataclass(frozen=True)
class PendingEntry:
    kind: str
    pk: int
    field: str
    label: str
    object_label: str
    markdown: bool
    value: str
    admin_url_name: str

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.pk}:{self.field}"


def _object_label(obj: Any, kind: str) -> str:
    if kind == "city":
        return f"Ville « {obj.name} »"
    if kind == "neighborhood":
        return f"Quartier « {obj.name} » ({obj.city.name})"
    return f"Page « {obj.title or obj.key} » ({obj.key})"


def pending_entries() -> list[PendingEntry]:
    """Toutes les valeurs encore marquées à rédiger, triées par type puis par objet."""
    entries: list[PendingEntry] = []
    for spec in content_fields():
        qs = spec.model._default_manager.filter(**{f"{spec.field}__contains": PLACEHOLDER})
        if spec.kind == "neighborhood":
            qs = qs.select_related("city")
        for obj in qs:
            entries.append(
                PendingEntry(
                    kind=spec.kind,
                    pk=obj.pk,
                    field=spec.field,
                    label=spec.label,
                    object_label=_object_label(obj, spec.kind),
                    markdown=spec.markdown,
                    value=getattr(obj, spec.field),
                    admin_url_name=spec.admin_url_name,
                )
            )
    order = {"page": 0, "city": 1, "neighborhood": 2}
    entries.sort(key=lambda e: (order[e.kind], e.object_label, e.field))
    return entries


def resolve_field(kind: str, pk: int, field: str) -> tuple[ContentField, Any]:
    """Retrouve la spécification et l'objet d'une clé `kind:pk:field` ; lève LookupError."""
    for spec in content_fields():
        if spec.kind == kind and spec.field == field:
            obj = spec.model._default_manager.filter(pk=pk).first()
            if obj is None:
                raise LookupError("Objet introuvable.")
            return spec, obj
    raise LookupError("Champ inconnu.")
