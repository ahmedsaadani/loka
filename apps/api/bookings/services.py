"""Cycle de vie des demandes, réservations et paiements. Voir ADR 0003 et ADR 0005."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from availability import services as availability_services
from bookings.models import (
    Booking,
    BookingRequest,
    BookingRequestStatus,
    BookingStatus,
    Payment,
    PaymentKind,
    PaymentStatus,
)
from bookings.payments.base import PaymentResult, get_payment_provider
from bookings.pricing import PlanData, PricingError, Quote, compute_quote
from core.exceptions import ConflictError, DomainError
from core.state import InvalidTransition, can_transition, transition
from listings.models import PricingPlan, Property, PropertyStatus
from notifications import emails

audit_logger = logging.getLogger("loka.audit")


def _json_safe(value: Any) -> Any:
    """Décimaux et dates -> chaînes, pour stockage dans un JSONField."""
    return json.loads(json.dumps(value, default=str))


# ----------------------------------------------------------------- devis


def get_active_plan(prop: Property, rental_mode: str) -> PricingPlan:
    try:
        return prop.pricing_plans.get(rental_mode=rental_mode, is_active=True)
    except PricingPlan.DoesNotExist as exc:
        raise DomainError(
            "Ce mode de location n'est pas proposé pour ce bien.", code="no_plan"
        ) from exc


def quote_for(prop: Property, rental_mode: str, start: date, end: date) -> Quote:
    plan = get_active_plan(prop, rental_mode)
    try:
        return compute_quote(
            PlanData(
                rental_mode=plan.rental_mode,
                price=plan.price,
                min_duration=plan.min_duration,
                max_duration=plan.max_duration,
            ),
            start,
            end,
            deposit_months=prop.deposit_months,
        )
    except PricingError as exc:
        raise DomainError(str(exc), code=exc.code) from exc


# ----------------------------------------------------------------- demandes


@transaction.atomic
def create_booking_request(
    *,
    prop: Property,
    traveler: User,
    rental_mode: str,
    start: date,
    end: date,
    guests: int,
    message: str = "",
) -> BookingRequest:
    if prop.status != PropertyStatus.PUBLISHED:
        raise DomainError("Ce bien n'est pas disponible à la réservation.", code="not_published")
    if prop.host_id == traveler.pk:
        raise DomainError("Vous ne pouvez pas réserver votre propre bien.", code="own_property")
    if guests < 1 or guests > prop.max_guests:
        raise ValidationError(
            {"guests": f"Ce bien accueille au maximum {prop.max_guests} personnes."}
        )
    availability_services.assert_available(prop, start, end)
    if BookingRequest.objects.filter(
        property=prop,
        traveler=traveler,
        status=BookingRequestStatus.PENDING,
        start_date__lt=end,
        end_date__gt=start,
    ).exists():
        raise ConflictError(
            "Vous avez déjà une demande en attente sur ces dates.", code="duplicate"
        )

    quote = quote_for(prop, rental_mode, start, end)
    request = BookingRequest.objects.create(
        property=prop,
        traveler=traveler,
        rental_mode=rental_mode,
        start_date=start,
        end_date=end,
        guests=guests,
        message=message,
        quoted_units=quote.units,
        quoted_unit_price=quote.unit_price,
        quoted_subtotal=quote.subtotal,
        quoted_fee=quote.fee,
        quoted_total=quote.total,
        quoted_deposit=quote.deposit,
        expires_at=timezone.now() + timedelta(hours=settings.BOOKING_REQUEST_TTL_HOURS),
    )
    emails.send_booking_request_received(request)
    audit_logger.info(
        "booking_request_created pk=%s property=%s traveler=%s", request.pk, prop.pk, traveler.pk
    )
    return request


def accept_request(request: BookingRequest, *, by: User) -> Booking:
    """L'hôte accepte : crée la réservation en attente d'acompte et bloque les dates."""
    if not can_transition(request, BookingRequestStatus.ACCEPTED):
        raise InvalidTransition(request, BookingRequestStatus.ACCEPTED)
    if request.expires_at <= timezone.now():
        # Hors transaction : l'expiration doit rester enregistrée malgré l'erreur renvoyée.
        expire_request(request)
        raise ConflictError("Cette demande a expiré.", code="expired")
    return _accept_request(request, by=by)


@transaction.atomic
def _accept_request(request: BookingRequest, *, by: User) -> Booking:
    prop = request.property
    quote = quote_for(prop, request.rental_mode, request.start_date, request.end_date)
    booking = Booking.objects.create(
        request=request,
        property=prop,
        traveler=request.traveler,
        host=prop.host,
        rental_mode=request.rental_mode,
        start_date=request.start_date,
        end_date=request.end_date,
        total_amount=request.quoted_total,
        deposit_amount=request.quoted_deposit,
        platform_fee=request.quoted_fee,
        fee_payer=quote.fee_payer,
    )
    availability_services.book_period(booking)
    transition(request, BookingRequestStatus.ACCEPTED, actor=by)
    _decline_conflicting_requests(booking, by=by)
    emails.send_booking_request_accepted(booking)
    return booking


def _decline_conflicting_requests(booking: Booking, *, by: User) -> None:
    others = BookingRequest.objects.filter(
        property=booking.property,
        status=BookingRequestStatus.PENDING,
        start_date__lt=booking.end_date,
        end_date__gt=booking.start_date,
    ).exclude(pk=booking.request_id)
    for other in others:
        transition(
            other,
            BookingRequestStatus.DECLINED,
            actor=by,
            note="Dates réservées par une autre demande",
            extra_fields={"decline_reason": "Ces dates viennent d'être réservées."},
        )
        emails.send_booking_request_declined(other)


@transaction.atomic
def decline_request(request: BookingRequest, *, by: User, reason: str = "") -> BookingRequest:
    transition(
        request,
        BookingRequestStatus.DECLINED,
        actor=by,
        note=reason,
        extra_fields={"decline_reason": reason},
    )
    emails.send_booking_request_declined(request)
    return request


@transaction.atomic
def cancel_request(request: BookingRequest, *, by: User) -> BookingRequest:
    """Le voyageur retire sa demande tant qu'elle est en attente."""
    transition(request, BookingRequestStatus.CANCELLED, actor=by)
    return request


@transaction.atomic
def expire_request(request: BookingRequest) -> BookingRequest:
    transition(request, BookingRequestStatus.EXPIRED, actor=None, note="Sans réponse de l'hôte")
    emails.send_booking_request_expired(request)
    return request


# ----------------------------------------------------------------- réservations & paiements


@transaction.atomic
def start_deposit_payment(booking: Booking, *, by: User) -> Payment:
    if booking.status != BookingStatus.AWAITING_DEPOSIT:
        raise ConflictError(
            "Cette réservation n'attend pas d'acompte.", code="not_awaiting_deposit"
        )
    existing = booking.payments.filter(
        kind=PaymentKind.DEPOSIT, status=PaymentStatus.INITIATED
    ).first()
    if existing:
        return existing
    provider = get_payment_provider()
    session = provider.create_checkout(
        amount=booking.deposit_amount,
        currency="TND",
        reference=str(booking.public_id),
        description=f"Acompte Loka - {booking.property.title}",
        success_url=f"{settings.SITE_URL}/compte/reservations/{booking.public_id}?paiement=ok",
        cancel_url=f"{settings.SITE_URL}/compte/reservations/{booking.public_id}?paiement=annule",
    )
    return Payment.objects.create(
        booking=booking,
        provider=session.provider,
        provider_ref=session.provider_ref,
        amount=booking.deposit_amount,
        kind=PaymentKind.DEPOSIT,
        checkout_url=session.checkout_url,
        raw_payload=session.raw,
    )


@transaction.atomic
def handle_payment_result(result: PaymentResult) -> Payment:
    """Appelé par le webhook du prestataire. Idempotent."""
    payment = (
        Payment.objects.select_for_update()
        .select_related("booking")
        .get(provider_ref=result.provider_ref)
    )
    if payment.status != PaymentStatus.INITIATED:
        return payment
    payment.raw_payload = {**payment.raw_payload, "result": _json_safe(result.raw)}
    if not result.succeeded:
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "raw_payload", "updated_at"])
        return payment
    if result.amount != payment.amount:
        payment.status = PaymentStatus.FAILED
        payment.raw_payload["error"] = "amount_mismatch"
        payment.save(update_fields=["status", "raw_payload", "updated_at"])
        raise DomainError("Montant payé différent du montant attendu.", code="amount_mismatch")
    payment.status = PaymentStatus.SUCCEEDED
    payment.save(update_fields=["status", "raw_payload", "updated_at"])
    booking = payment.booking
    if payment.kind == PaymentKind.DEPOSIT and booking.status == BookingStatus.AWAITING_DEPOSIT:
        transition(
            booking, BookingStatus.CONFIRMED, actor=None, note=f"Acompte payé ({payment.provider})"
        )
        emails.send_deposit_paid(booking)
        from bookings.tasks import generate_contract
        from core.tasks import enqueue

        enqueue(generate_contract, booking.pk)
    audit_logger.info(
        "payment_succeeded pk=%s booking=%s amount=%s", payment.pk, booking.pk, payment.amount
    )
    return payment


def refund_amount_for_cancellation(
    booking: Booking, *, by: User, today: date | None = None
) -> Decimal:
    """
    Politique prudente (ADR 0005) : l'hôte qui annule rembourse tout ; le voyageur récupère
    l'acompte s'il annule au moins BOOKING_FREE_CANCELLATION_DAYS jours avant le début.
    """
    today = today or timezone.localdate()
    if by.pk == booking.host_id or by.is_loka_staff:
        return booking.deposit_amount
    if (booking.start_date - today).days >= settings.BOOKING_FREE_CANCELLATION_DAYS:
        return booking.deposit_amount
    return Decimal("0.00")


@transaction.atomic
def cancel_booking(booking: Booking, *, by: User, reason: str = "") -> Booking:
    refund = Decimal("0.00")
    if booking.status == BookingStatus.CONFIRMED:
        refund = refund_amount_for_cancellation(booking, by=by)
    transition(
        booking,
        BookingStatus.CANCELLED,
        actor=by,
        note=reason,
        extra_fields={"cancellation_reason": reason, "cancelled_by": by},
    )
    availability_services.release_booking(booking)
    if refund > 0:
        deposit = booking.payments.filter(
            kind=PaymentKind.DEPOSIT, status=PaymentStatus.SUCCEEDED
        ).first()
        if deposit:
            result = get_payment_provider().refund(provider_ref=deposit.provider_ref, amount=refund)
            Payment.objects.create(
                booking=booking,
                provider=deposit.provider,
                provider_ref=result.provider_ref,
                amount=refund,
                kind=PaymentKind.REFUND,
                status=PaymentStatus.SUCCEEDED if result.succeeded else PaymentStatus.FAILED,
                raw_payload=result.raw,
            )
            deposit.status = PaymentStatus.REFUNDED
            deposit.save(update_fields=["status", "updated_at"])
    emails.send_booking_cancelled(booking)
    return booking


@transaction.atomic
def start_stay(booking: Booking, *, by: User | None = None) -> Booking:
    transition(booking, BookingStatus.IN_PROGRESS, actor=by)
    return booking


@transaction.atomic
def complete_stay(booking: Booking, *, by: User | None = None) -> Booking:
    transition(booking, BookingStatus.COMPLETED, actor=by)
    return booking


def build_contract_context(booking: Booking) -> dict[str, Any]:
    return {
        "booking": booking,
        "property": booking.property,
        "host": booking.host,
        "traveler": booking.traveler,
        "generated_at": timezone.now(),
    }
