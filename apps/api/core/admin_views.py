"""
Écran admin « Contenus à rédiger » : liste tous les textes encore marqués [À RÉDIGER]
(villes, quartiers, pages légales), avec un éditeur Markdown et un aperçu fidèle au front.
Réservé au staff (admin.site.admin_view) ; le rendu de l'aperçu est fait côté serveur par
`core.markdown.render_markdown`, miroir du composant Markdown du front.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views import View
from django.views.decorators.http import require_POST

from core.checks import PLACEHOLDER
from core.content import pending_entries, resolve_field
from core.markdown import render_markdown


def _parse_key(key: str) -> tuple[str, int, str]:
    try:
        kind, pk, field = key.split(":", 2)
        return kind, int(pk), field
    except ValueError as exc:
        raise LookupError("Clé invalide.") from exc


@method_decorator(staff_member_required, name="dispatch")
class ContentToWriteView(View):
    """GET : liste + éditeur de l'entrée sélectionnée (?key=). POST : enregistre le texte."""

    template_name = "admin/loka/content_to_write.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        entries = pending_entries()
        selected = None
        key = request.GET.get("key")
        if key:
            try:
                kind, pk, field = _parse_key(key)
                spec, obj = resolve_field(kind, pk, field)
            except LookupError:
                messages.error(request, "Contenu introuvable.")
                return redirect("admin-content-to-write")
            selected = {
                "key": key,
                "label": spec.label,
                "markdown": spec.markdown,
                "value": getattr(obj, field),
                "object_label": next((e.object_label for e in entries if e.key == key), str(obj)),
                "admin_url": reverse(f"admin:{spec.admin_url_name}", args=[obj.pk]),
            }
        context = {
            **admin.site.each_context(request),
            "title": "Contenus à rédiger",
            "entries": entries,
            "selected": selected,
            "placeholder": PLACEHOLDER,
            "preview_url": reverse("admin-content-preview"),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        key = request.POST.get("key", "")
        value = request.POST.get("value", "").replace("\r\n", "\n").strip()
        try:
            kind, pk, field = _parse_key(key)
            spec, obj = resolve_field(kind, pk, field)
        except LookupError:
            return HttpResponseBadRequest("Contenu introuvable.")
        if not value:
            messages.error(request, "Le texte ne peut pas être vide.")
            return redirect(f"{reverse('admin-content-to-write')}?key={key}")
        if PLACEHOLDER in value:
            messages.warning(
                request,
                f"Le marqueur {PLACEHOLDER} est toujours présent : "
                "le texte reste masqué sur le site.",
            )
        setattr(obj, field, value)
        obj.save(update_fields=[field, "updated_at"])
        _revalidate(kind, obj)
        messages.success(request, f"« {spec.label} » enregistré pour {escape(str(obj))}.")
        return redirect("admin-content-to-write")


def _revalidate(kind: str, obj: Any) -> None:
    """Purge les pages publiques concernées (sans bloquer si le front est injoignable)."""
    from core.tasks import enqueue
    from notifications.tasks import revalidate_front

    if kind == "city":
        paths, tags = [f"/location/{obj.slug}"], [f"city:{obj.slug}"]
    elif kind == "neighborhood":
        paths, tags = [f"/location/{obj.city.slug}/{obj.slug}"], [f"city:{obj.city.slug}"]
    else:
        paths, tags = [f"/{obj.key}"], []
    enqueue(revalidate_front, paths, tags)


@staff_member_required
@require_POST
def content_preview(request: HttpRequest) -> JsonResponse:
    """Aperçu HTML (fragment) du Markdown saisi, mêmes règles que le front."""
    source = request.POST.get("value", "")
    return JsonResponse({"html": render_markdown(source), "pending": PLACEHOLDER in source})
