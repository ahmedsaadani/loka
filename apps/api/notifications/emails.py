"""
Emails transactionnels. Chaque fonction construit le message ; l'envoi passe par
notifications.tasks.send_email (Celery) pour ne jamais bloquer une requête.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

if TYPE_CHECKING:
    from accounts.models import User
    from bookings.models import Booking, BookingRequest
    from listings.models import Property


def _enqueue(*, to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    from core.tasks import enqueue
    from notifications.tasks import send_email

    context = {"site_url": settings.SITE_URL, **context}
    html = render_to_string(f"emails/{template}.html", context)
    text = strip_tags(html)
    enqueue(send_email, to, subject, text, html)


def send_welcome(user: User) -> None:
    _enqueue(
        to=user.email,
        subject="Bienvenue sur Loka",
        template="welcome",
        context={"user": user},
    )


def send_booking_request_received(request: BookingRequest) -> None:
    host = request.property.host
    _enqueue(
        to=host.email,
        subject=f"Nouvelle demande de réservation pour « {request.property.title} »",
        template="booking_request_received",
        context={"request": request, "host": host},
    )


def send_booking_request_reminder(request: BookingRequest) -> None:
    host = request.property.host
    _enqueue(
        to=host.email,
        subject=f"Rappel : une demande expire bientôt pour « {request.property.title} »",
        template="booking_request_reminder",
        context={"request": request, "host": host},
    )


def send_booking_request_accepted(booking: Booking) -> None:
    _enqueue(
        to=booking.traveler.email,
        subject=f"Demande acceptée : payez l'acompte pour « {booking.property.title} »",
        template="booking_request_accepted",
        context={"booking": booking},
    )


def send_booking_request_declined(request: BookingRequest) -> None:
    _enqueue(
        to=request.traveler.email,
        subject=f"Demande refusée pour « {request.property.title} »",
        template="booking_request_declined",
        context={"request": request},
    )


def send_booking_request_expired(request: BookingRequest) -> None:
    _enqueue(
        to=request.traveler.email,
        subject=f"Demande expirée pour « {request.property.title} »",
        template="booking_request_expired",
        context={"request": request},
    )


def send_deposit_paid(booking: Booking) -> None:
    for recipient in (booking.traveler, booking.host):
        _enqueue(
            to=recipient.email,
            subject=f"Réservation confirmée : « {booking.property.title} »",
            template="deposit_paid",
            context={"booking": booking, "recipient": recipient},
        )


def send_booking_cancelled(booking: Booking) -> None:
    for recipient in (booking.traveler, booking.host):
        _enqueue(
            to=recipient.email,
            subject=f"Réservation annulée : « {booking.property.title} »",
            template="booking_cancelled",
            context={"booking": booking, "recipient": recipient},
        )


def send_property_published(prop: Property) -> None:
    _enqueue(
        to=prop.host.email,
        subject=f"Votre bien « {prop.title} » est en ligne",
        template="property_published",
        context={"property": prop},
    )


def send_property_rejected(prop: Property) -> None:
    _enqueue(
        to=prop.host.email,
        subject=f"Votre bien « {prop.title} » n'a pas été validé",
        template="property_rejected",
        context={"property": prop},
    )


def send_password_reset(user: User, reset_url: str) -> None:
    _enqueue(
        to=user.email,
        subject="Réinitialisation de votre mot de passe Loka",
        template="password_reset",
        context={"user": user, "reset_url": reset_url},
    )
