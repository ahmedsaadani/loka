"""Balises pour les gabarits de l'admin Django (bandeau « Contenus à rédiger »)."""

from __future__ import annotations

from django import template
from django.db import DatabaseError

register = template.Library()


@register.simple_tag
def pending_content_count() -> int:
    from core.content import pending_entries

    try:
        return len(pending_entries())
    except DatabaseError:
        return 0
