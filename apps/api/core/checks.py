"""
Vérifications système Loka (Phase 6 F17).

`manage.py check --deploy` et le démarrage en production signalent les contenus encore
marqués « [À RÉDIGER] » : textes SEO des villes et quartiers, pages légales.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.db import DatabaseError

PLACEHOLDER = "[À RÉDIGER]"
logger = logging.getLogger("loka.audit")


def placeholder_report() -> list[str]:
    """Liste lisible des contenus contenant encore le marqueur. Vide si tout est rédigé."""
    from django.db.models import Q

    from core.models import SiteContent
    from geo.models import City, Neighborhood

    found: list[str] = []
    text_q = (
        Q(seo_title__contains=PLACEHOLDER)
        | Q(seo_description__contains=PLACEHOLDER)
        | Q(intro_text__contains=PLACEHOLDER)
    )
    for city in City.objects.filter(text_q).order_by("name"):
        found.append(f"Ville « {city.name} » (admin > Géographie > Villes)")
    for hood in Neighborhood.objects.filter(text_q).select_related("city").order_by("name"):
        found.append(
            f"Quartier « {hood.name} » ({hood.city.name}) (admin > Géographie > Quartiers)"
        )
    for content in SiteContent.objects.filter(
        Q(title__contains=PLACEHOLDER) | Q(body__contains=PLACEHOLDER)
    ).order_by("key"):
        found.append(f"Page « {content.key} » (admin > Socle > Contenus du site)")
    return found


@register(Tags.compatibility, deploy=True)
def check_placeholder_content(app_configs: Any, **kwargs: Any) -> list[Warning]:
    """Avertit (jamais bloquant) tant que des textes provisoires subsistent."""
    if settings.ENVIRONMENT != "prod" and not kwargs.get("force"):
        return []
    try:
        found = placeholder_report()
    except DatabaseError:
        return []
    if not found:
        return []
    return [
        Warning(
            f"{len(found)} contenu(s) encore marqué(s) {PLACEHOLDER} : " + " ; ".join(found[:10]),
            hint="Rédigez les textes dans l'admin Django avant la mise en production.",
            id="loka.W001",
        )
    ]


def warn_if_placeholders_remain() -> None:
    """Appelé au démarrage en production : journalise et remonte à Sentry."""
    try:
        found = placeholder_report()
    except DatabaseError:
        return
    if not found:
        return
    message = f"{len(found)} contenu(s) encore marqué(s) {PLACEHOLDER} en production"
    logger.warning("%s : %s", message, " ; ".join(found))
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.capture_message(message, level="warning")
