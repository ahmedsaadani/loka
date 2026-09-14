from __future__ import annotations

import csv
import io
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from core.state import transition
from leads.models import Lead, LeadSource, LeadStatus
from listings.models import Property, PropertyStatus, PropertyType

IMPORT_FIELDS = ("source", "source_url", "title", "price", "city", "phone")


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source", "") or LeadSource.MANUAL).strip().lower()
    if source not in LeadSource.values:
        source = LeadSource.MANUAL
    price_raw = row.get("price")
    price: Decimal | None = None
    if price_raw not in (None, ""):
        try:
            price = Decimal(str(price_raw).replace(" ", "").replace(",", "."))
        except InvalidOperation:
            price = None
    title = str(row.get("title", "") or "").strip()[:200]
    if not title:
        raise ValidationError("Chaque ligne doit avoir un titre.")
    known = {k: row[k] for k in IMPORT_FIELDS if k in row}
    extra = {k: v for k, v in row.items() if k not in known}
    return {
        "source": source,
        "source_url": str(row.get("source_url", "") or "").strip()[:500],
        "title": title,
        "price": price,
        "city": str(row.get("city", "") or "").strip()[:80],
        "phone": str(row.get("phone", "") or "").strip()[:32],
        "raw_data": extra,
    }


def parse_import_payload(content: bytes, content_type: str) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    if "json" in content_type:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValidationError("Le JSON doit être une liste d'objets.")
        return [_clean_row(row) for row in data if isinstance(row, dict)]
    reader = csv.DictReader(io.StringIO(text))
    return [_clean_row(row) for row in reader]


@transaction.atomic
def import_leads(rows: list[dict[str, Any]], *, by: User) -> tuple[int, int]:
    """Retourne (créés, ignorés). Les doublons sur source_url sont ignorés."""
    created = skipped = 0
    for row in rows:
        url = row["source_url"]
        if url and Lead.objects.filter(source_url=url).exists():
            skipped += 1
            continue
        Lead.objects.create(assigned_to=None, **row)
        created += 1
    return created, skipped


@transaction.atomic
def change_status(lead: Lead, to_status: str, *, by: User, note: str = "") -> Lead:
    transition(lead, to_status, actor=by, note=note)
    if note:
        lead.notes = f"{lead.notes}\n{note}".strip()
        lead.save(update_fields=["notes", "updated_at"])
    return lead


@transaction.atomic
def convert_to_property(lead: Lead, *, host: User, city: Any, by: User) -> Property:
    """Crée un brouillon de bien pré-rempli depuis le lead, rattaché à l'hôte indiqué."""
    if lead.status == LeadStatus.CONVERTED:
        raise ValidationError("Lead déjà converti.")
    prop = Property.objects.create(
        host=host,
        title=lead.title[:140],
        description=lead.raw_data.get("description", "") if isinstance(lead.raw_data, dict) else "",
        property_type=PropertyType.APARTMENT,
        city=city,
        status=PropertyStatus.DRAFT,
        verification_notes=f"Converti depuis le lead {lead.public_id} ({lead.source}).",
    )
    lead.converted_property = prop
    lead.save(update_fields=["converted_property", "updated_at"])
    transition(lead, LeadStatus.CONVERTED, actor=by)
    return prop


PROPERTY_TYPE_LABELS = {
    "studio": "Studio",
    "apartment": "Appartement",
    "villa": "Villa",
    "room_in_shared_flat": "Chambre en colocation",
    "other": "Bien",
}


def create_owner_contact(data: dict[str, Any]) -> Lead:
    """Lead source « manual » depuis le formulaire propriétaire ; notifie le staff."""
    from notifications.emails import send_owner_contact_to_staff

    label = PROPERTY_TYPE_LABELS.get(data["property_type"], "Bien")
    lead = Lead.objects.create(
        source=LeadSource.MANUAL,
        title=f"{label} à {data['city']} — {data['name']}"[:200],
        city=data["city"],
        phone=data["phone"],
        raw_data={
            "channel": "owner_contact_form",
            "name": data["name"],
            "property_type": data["property_type"],
            "message": data.get("message", ""),
        },
        notes=data.get("message", ""),
    )
    send_owner_contact_to_staff(lead)
    return lead
