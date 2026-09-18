from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Avg, Count

from accounts.models import User
from bookings.models import Booking, BookingStatus
from core.exceptions import ConflictError
from listings.models import Property
from reviews.models import Review

audit_logger = logging.getLogger("loka.audit")


def recompute_property_rating(prop: Property) -> None:
    """Recalcule la note moyenne et le nombre d'avis publiés d'un bien.

    Source de vérité : les lignes Review publiées. Sans avis, la note repasse à None.
    """
    agg = Review.objects.filter(booking__property=prop, is_published=True).aggregate(
        avg=Avg("rating"), n=Count("id")
    )
    count = agg["n"] or 0
    prop.review_count = count
    prop.rating = round(agg["avg"], 1) if agg["avg"] is not None else None
    prop.save(update_fields=["rating", "review_count", "updated_at"])


@transaction.atomic
def create_review(*, booking: Booking, author: User, rating: int, comment: str) -> Review:
    """Crée l'avis d'un voyageur pour un séjour terminé.

    Garde-fous : l'auteur doit être le voyageur de la réservation, le séjour doit être
    terminé, et un seul avis par réservation est autorisé.
    """
    if booking.traveler_id != author.id:
        raise ConflictError("Cette réservation ne vous appartient pas.", code="not_your_booking")
    if booking.status != BookingStatus.COMPLETED:
        raise ConflictError(
            "Vous pourrez laisser un avis une fois le séjour terminé.", code="stay_not_completed"
        )
    if Review.objects.filter(booking=booking).exists():
        raise ConflictError(
            "Vous avez déjà laissé un avis pour ce séjour.", code="already_reviewed"
        )
    review = Review.objects.create(
        booking=booking,
        author=author,
        rating=rating,
        comment=comment,
        is_published=True,
    )
    recompute_property_rating(booking.property)
    audit_logger.info("review_created booking=%s rating=%s", booking.pk, rating)
    return review
