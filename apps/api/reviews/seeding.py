"""Génération d'avis de démonstration adossés à de vraies réservations « terminées ».

Utilisé à la fois par la commande `seed` (base vierge) et par `backfill_reviews`
(base déjà peuplée). Idempotent par bien : un bien qui a déjà des avis est ignoré.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import Role, User
from bookings.models import (
    Booking,
    BookingRequest,
    BookingRequestStatus,
    BookingStatus,
)
from core.seed_reviews import COMMENTS, REVIEWER_NAMES
from listings.models import Property, RentalMode
from reviews.models import Review
from reviews.services import recompute_property_rating

# Distribution des notes selon l'état du bien (mieux noté quand mieux entretenu).
RATING_WEIGHTS: dict[str, tuple[list[int], list[int]]] = {
    "excellent": ([5, 4, 3], [8, 2, 0]),
    "good": ([5, 4, 3], [5, 4, 1]),
    "basic": ([5, 4, 3], [3, 4, 3]),
}


def ensure_reviewers() -> list[User]:
    """Voyageurs fictifs auteurs des avis de démonstration (idempotent)."""
    reviewers: list[User] = []
    for i, (first, last) in enumerate(REVIEWER_NAMES, start=1):
        user, created = User.objects.get_or_create(
            email=f"avis{i}@demo.loka.tn",
            defaults={
                "role": Role.TRAVELER,
                "first_name": first,
                "last_name": last,
                "is_identity_verified": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        reviewers.append(user)
    return reviewers


def _pricing(prop: Property) -> tuple[str, Decimal, int, int]:
    """(mode, prix unitaire, nombre d'unités, jours/unité) à partir des plans actifs."""
    plans = {p.rental_mode: p for p in prop.pricing_plans.filter(is_active=True)}
    rng = random.Random(prop.pk)  # noqa: S311  # nosec B311 - données de démo, non cryptographique
    if RentalMode.NIGHTLY in plans:
        return RentalMode.NIGHTLY, plans[RentalMode.NIGHTLY].price, rng.randint(2, 9), 1
    if RentalMode.MONTHLY in plans:
        return RentalMode.MONTHLY, plans[RentalMode.MONTHLY].price, rng.randint(1, 3), 30
    if RentalMode.YEARLY in plans:
        return RentalMode.YEARLY, plans[RentalMode.YEARLY].price, 1, 330
    return RentalMode.MONTHLY, Decimal("800.00"), 1, 30


def seed_reviews_for_property(prop: Property, rng: random.Random, reviewers: list[User]) -> int:
    """Crée des séjours terminés + avis publiés pour un bien, puis recalcule sa note.

    Renvoie le nombre d'avis créés (0 si le bien en avait déjà).
    """
    if Review.objects.filter(booking__property=prop).exists():
        return 0
    mode, unit_price, units, unit_days = _pricing(prop)
    values, weights = RATING_WEIGHTS.get(prop.condition_grade, RATING_WEIGHTS["good"])
    count = rng.randint(3, min(10, len(reviewers)))
    duration = units * unit_days
    for author in rng.sample(reviewers, count):
        end = timezone.localdate() - timedelta(days=rng.randint(5, 300))
        start = end - timedelta(days=duration)
        subtotal = unit_price * units
        fee = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
        request = BookingRequest.objects.create(
            property=prop,
            traveler=author,
            rental_mode=mode,
            start_date=start,
            end_date=end,
            guests=rng.randint(1, min(prop.max_guests, 4)),
            status=BookingRequestStatus.ACCEPTED,
            quoted_units=units,
            quoted_unit_price=unit_price,
            quoted_subtotal=subtotal,
            quoted_fee=fee,
            quoted_total=subtotal,
            quoted_deposit=unit_price,
            expires_at=timezone.now() - timedelta(days=rng.randint(5, 300)),
        )
        booking = Booking.objects.create(
            request=request,
            property=prop,
            traveler=author,
            host=prop.host,
            rental_mode=mode,
            start_date=start,
            end_date=end,
            total_amount=subtotal,
            deposit_amount=unit_price,
            platform_fee=fee,
            fee_payer="host",
            status=BookingStatus.COMPLETED,
        )
        rating = rng.choices(values, weights=weights)[0]
        Review.objects.create(
            booking=booking,
            author=author,
            rating=rating,
            comment=rng.choice(COMMENTS[rating]),
            is_published=True,
        )
    recompute_property_rating(prop)
    return count
