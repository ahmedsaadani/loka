"""Services métier des biens : cycle de vie, modification, photos, plans tarifaires.

Voir ADR 0003 (services) et ADR 0007 (modification d'un bien publié, identité requise).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from accounts.models import User
from core.state import transition
from core.uploads import validate_and_reencode_image
from listings.models import (
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyStatus,
)

audit_logger = logging.getLogger("loka.audit")

MIN_PHOTOS_TO_SUBMIT = 3

# Champs modifiables sans nouvelle validation (ADR 0007) : conditions tarifaires et règles.
LIVE_FIELDS = frozenset(
    {
        "house_rules",
        "charges_included",
        "monthly_charges_estimate",
        "deposit_months",
        "min_lease_months",
    }
)
# Tout autre champ décrit le bien : sa modification sur un bien publié déclenche une revue.
REVIEW_FIELDS = frozenset(
    {
        "title",
        "description",
        "property_type",
        "rooms_label",
        "bedrooms",
        "bathrooms",
        "surface_m2",
        "floor",
        "has_elevator",
        "furnished",
        "max_guests",
        "city",
        "neighborhood",
        "address_private",
        "location",
        "location_precision",
        "distance_notes",
        "amenities",
    }
)
# Statuts depuis lesquels une modification descriptive renvoie en validation.
REVIEW_TRIGGER_STATUSES = frozenset({PropertyStatus.PUBLISHED, PropertyStatus.PAUSED})
# Statuts pendant lesquels l'ancienne version publiée reste visible (si instantané présent).
SNAPSHOT_STATUSES = frozenset({PropertyStatus.PENDING_REVIEW, PropertyStatus.NEEDS_VISIT})


def revalidate_property_pages(prop: Property) -> None:
    """Régénère la fiche, la ville, le quartier et l'accueil côté front."""
    from core.tasks import enqueue
    from notifications.tasks import revalidate_front

    paths = ["/", f"/logement/{prop.slug}", f"/location/{prop.city.slug}"]
    if prop.neighborhood is not None:
        paths.append(f"/location/{prop.city.slug}/{prop.neighborhood.slug}")
    enqueue(revalidate_front, paths, [f"property:{prop.slug}", f"city:{prop.city.slug}"])


class PropertyNotReady(ValidationError):
    """Le bien ne remplit pas les conditions pour être soumis / publié."""


def host_identity_verified(prop: Property) -> bool:
    """Drapeau posé uniquement par accounts.services.approve_identity_document."""
    return bool(prop.host.is_identity_verified)


def readiness_errors(prop: Property) -> dict[str, str]:
    errors: dict[str, str] = {}
    if len(prop.title.strip()) < 10:
        errors["title"] = "Le titre doit faire au moins 10 caractères."
    if len(prop.description.strip()) < 80:
        errors["description"] = "La description doit faire au moins 80 caractères."
    if not prop.address_private.strip():
        errors["address_private"] = "L'adresse exacte est requise pour la visite."
    if prop.location is None:
        errors["location"] = "Placez le bien sur la carte."
    if prop.photos.count() < MIN_PHOTOS_TO_SUBMIT:
        errors["photos"] = f"Ajoutez au moins {MIN_PHOTOS_TO_SUBMIT} photos."
    if not prop.pricing_plans.filter(is_active=True).exists():
        errors["pricing_plans"] = "Ajoutez au moins un plan tarifaire."
    if not host_identity_verified(prop):
        errors["identity"] = (
            "Votre pièce d'identité doit être vérifiée par Loka avant la publication. "
            "Envoyez-la depuis Mon compte > Identité."
        )
    return errors


# ----------------------------------------------------------------- instantané publié


def build_published_snapshot(prop: Property) -> dict[str, Any]:
    """Représentation publique figée (carte + fiche) servie pendant une revue."""
    from listings.serializers import PropertyCardSerializer, PropertyDetailSerializer

    context = {"force_live": True}
    fresh = Property.objects.for_public_any_status().get(pk=prop.pk)
    data = {
        "card": PropertyCardSerializer(fresh, context=context).data,
        "detail": PropertyDetailSerializer(fresh, context=context).data,
        "captured_at": timezone.now().isoformat(),
    }
    return json.loads(json.dumps(data, default=str))


def ensure_snapshot(prop: Property) -> None:
    """Garantit qu'un bien publié ou en pause a un instantané de sa version en ligne."""
    if prop.status in REVIEW_TRIGGER_STATUSES and prop.published_snapshot is None:
        prop.published_snapshot = build_published_snapshot(prop)
        prop.save(update_fields=["published_snapshot", "updated_at"])


def _clear_snapshot(prop: Property) -> None:
    if prop.published_snapshot is not None:
        prop.published_snapshot = None
        prop.save(update_fields=["published_snapshot", "updated_at"])


# ----------------------------------------------------------------- transitions hôte


@transaction.atomic
def submit_for_review(prop: Property, *, by: User) -> Property:
    errors = readiness_errors(prop)
    if errors:
        raise PropertyNotReady(errors)
    transition(prop, PropertyStatus.PENDING_REVIEW, actor=by)
    return prop


@transaction.atomic
def withdraw_to_draft(prop: Property, *, by: User) -> Property:
    """L'hôte (ou le staff) remet le bien en brouillon : il disparaît du site."""
    was_visible = prop.is_serving_snapshot
    transition(prop, PropertyStatus.DRAFT, actor=by)
    _clear_snapshot(prop)
    if was_visible:
        revalidate_property_pages(prop)
    return prop


@transaction.atomic
def pause(prop: Property, *, by: User, note: str = "") -> Property:
    transition(prop, PropertyStatus.PAUSED, actor=by, note=note)
    revalidate_property_pages(prop)
    return prop


@transaction.atomic
def resume(prop: Property, *, by: User) -> Property:
    transition(prop, PropertyStatus.PUBLISHED, actor=by)
    revalidate_property_pages(prop)
    return prop


def _send_to_review_after_change(prop: Property, *, by: User, changed: list[str]) -> None:
    """Un bien publié ou en pause vient d'être modifié sur un champ descriptif."""
    from notifications import emails

    transition(
        prop,
        PropertyStatus.PENDING_REVIEW,
        actor=by,
        note=f"Modification à valider : {', '.join(sorted(changed))}",
    )
    audit_logger.info(
        "property_changes_under_review pk=%s by=%s fields=%s", prop.pk, by.pk, changed
    )
    emails.send_property_changes_under_review(prop, changed)


@transaction.atomic
def update_property(prop: Property, *, by: User, data: dict[str, Any]) -> Property:
    """
    Applique une modification de l'hôte (données brutes du client, validées ici).
    Sur un bien publié ou en pause, un champ de REVIEW_FIELDS renvoie le bien en validation
    en conservant l'ancienne version visible (instantané). Les champs LIVE_FIELDS
    s'appliquent immédiatement.
    """
    from listings.serializers import PropertyWriteSerializer

    ensure_snapshot(prop)
    before = _snapshot_fields(prop, data.keys())
    serializer = PropertyWriteSerializer(prop, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    prop.refresh_from_db()
    after = _snapshot_fields(prop, data.keys())
    changed = [key for key in data if before.get(key) != after.get(key)]
    review_changes = [key for key in changed if key in REVIEW_FIELDS]

    if prop.status in REVIEW_TRIGGER_STATUSES and review_changes:
        _send_to_review_after_change(prop, by=by, changed=review_changes)
    elif prop.status == PropertyStatus.PUBLISHED and changed:
        revalidate_property_pages(prop)
    return prop


def _snapshot_fields(prop: Property, keys: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key in keys:
        if key == "amenities":
            values[key] = sorted(prop.amenities.values_list("code", flat=True))
        elif key == "location":
            values[key] = (prop.location.x, prop.location.y) if prop.location else None
        elif key in {"city", "neighborhood"}:
            values[key] = getattr(prop, f"{key}_id")
        else:
            values[key] = getattr(prop, key, None)
    return values


# ----------------------------------------------------------------- transitions équipe


@transaction.atomic
def schedule_visit(prop: Property, *, by: User, visit_at: Any, note: str = "") -> Property:
    transition(
        prop,
        PropertyStatus.NEEDS_VISIT,
        actor=by,
        note=note,
        extra_fields={"visit_scheduled_at": visit_at},
    )
    return prop


@transaction.atomic
def back_to_review(prop: Property, *, by: User, note: str = "") -> Property:
    transition(prop, PropertyStatus.PENDING_REVIEW, actor=by, note=note)
    return prop


@transaction.atomic
def publish(
    prop: Property,
    *,
    by: User,
    verification_level: str,
    condition_grade: str,
    notes: str = "",
) -> Property:
    """Publication par l'équipe après visite : fige la vérification et l'instantané public."""
    errors = readiness_errors(prop)
    if errors:
        raise PropertyNotReady(errors)
    now = timezone.now()
    transition(
        prop,
        PropertyStatus.PUBLISHED,
        actor=by,
        note=notes,
        extra_fields={
            "verification_level": verification_level,
            "condition_grade": condition_grade,
            "verified_at": now,
            "verified_by": by,
            "verification_notes": notes,
            "rejection_reason": "",
            "published_at": prop.published_at or now,
        },
    )
    prop.published_snapshot = build_published_snapshot(prop)
    prop.save(update_fields=["published_snapshot", "updated_at"])
    audit_logger.info("property_published pk=%s by=%s level=%s", prop.pk, by.pk, verification_level)
    revalidate_property_pages(prop)
    return prop


@transaction.atomic
def reject(prop: Property, *, by: User, reason: str) -> Property:
    was_visible = prop.is_serving_snapshot
    transition(
        prop,
        PropertyStatus.REJECTED,
        actor=by,
        note=reason,
        extra_fields={"rejection_reason": reason},
    )
    _clear_snapshot(prop)
    if was_visible:
        revalidate_property_pages(prop)
    return prop


# ----------------------------------------------------------------- photos


@transaction.atomic
def add_photo(
    prop: Property,
    *,
    upload: UploadedFile,
    alt_text: str = "",
    taken_by_team: bool = False,
    by: User | None = None,
) -> PropertyPhoto:
    if by is not None and not taken_by_team:
        ensure_snapshot(prop)
    content = validate_and_reencode_image(upload)
    with Image.open(content) as img:
        width, height = img.size
    content.seek(0)
    order = (prop.photos.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    photo = PropertyPhoto(
        property=prop,
        order=order,
        alt_text=alt_text or prop.title,
        taken_by_team=taken_by_team,
        width=width,
        height=height,
        is_cover=not prop.photos.exists(),
    )
    photo.original.save("photo.jpg", content, save=False)
    photo.save()
    from core.tasks import enqueue
    from notifications.tasks import generate_photo_variants

    enqueue(generate_photo_variants, photo.pk)
    photo.refresh_from_db(fields=["variants"])
    if by is not None and not taken_by_team and prop.status in REVIEW_TRIGGER_STATUSES:
        _send_to_review_after_change(prop, by=by, changed=["photos"])
    return photo


@transaction.atomic
def reorder_photos(prop: Property, ordered_public_ids: list[str]) -> None:
    photos = {str(p.public_id): p for p in prop.photos.all()}
    if set(photos) != set(ordered_public_ids):
        raise ValidationError(
            {"photos": "La liste doit contenir exactement toutes les photos du bien."}
        )
    for index, public_id in enumerate(ordered_public_ids, start=1):
        photo = photos[public_id]
        photo.order = index
        photo.is_cover = index == 1
    PropertyPhoto.objects.bulk_update(photos.values(), ["order", "is_cover"])
    if prop.status == PropertyStatus.PUBLISHED:
        revalidate_property_pages(prop)


@transaction.atomic
def delete_photo(photo: PropertyPhoto, *, by: User | None = None) -> None:
    prop = photo.property
    if by is not None and not by.is_loka_staff:
        ensure_snapshot(prop)
    was_cover = photo.is_cover
    photo.original.delete(save=False)
    photo.delete()
    if was_cover:
        first = prop.photos.order_by("order").first()
        if first:
            first.is_cover = True
            first.save(update_fields=["is_cover"])
    if by is not None and not by.is_loka_staff and prop.status in REVIEW_TRIGGER_STATUSES:
        _send_to_review_after_change(prop, by=by, changed=["photos"])


# ----------------------------------------------------------------- plans tarifaires


@transaction.atomic
def upsert_pricing_plan(
    prop: Property,
    *,
    rental_mode: str,
    price: Any,
    min_duration: int = 1,
    max_duration: int | None = None,
    is_active: bool = True,
) -> PricingPlan:
    if max_duration is not None and max_duration < min_duration:
        raise ValidationError({"max_duration": "Le maximum doit être supérieur au minimum."})
    plan, _ = PricingPlan.objects.update_or_create(
        property=prop,
        rental_mode=rental_mode,
        defaults={
            "price": price,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "is_active": is_active,
        },
    )
    if prop.status == PropertyStatus.PUBLISHED:
        revalidate_property_pages(prop)
    return plan
