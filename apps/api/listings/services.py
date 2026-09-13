"""Services métier des biens : cycle de vie, photos, plans tarifaires. Voir ADR 0003."""

from __future__ import annotations

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
    return errors


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
    """L'hôte (ou le staff) remet le bien en brouillon depuis pending_review, paused ou rejected."""
    transition(prop, PropertyStatus.DRAFT, actor=by)
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
    """Publication par l'équipe après visite : fige la vérification."""
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
    audit_logger.info("property_published pk=%s by=%s level=%s", prop.pk, by.pk, verification_level)
    revalidate_property_pages(prop)
    return prop


@transaction.atomic
def reject(prop: Property, *, by: User, reason: str) -> Property:
    transition(
        prop,
        PropertyStatus.REJECTED,
        actor=by,
        note=reason,
        extra_fields={"rejection_reason": reason},
    )
    return prop


# ----------------------------------------------------------------- photos


@transaction.atomic
def add_photo(
    prop: Property,
    *,
    upload: UploadedFile,
    alt_text: str = "",
    taken_by_team: bool = False,
) -> PropertyPhoto:
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


@transaction.atomic
def delete_photo(photo: PropertyPhoto) -> None:
    prop = photo.property
    was_cover = photo.is_cover
    photo.original.delete(save=False)
    photo.delete()
    if was_cover:
        first = prop.photos.order_by("order").first()
        if first:
            first.is_cover = True
            first.save(update_fields=["is_cover"])


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
