"""ADR 0007 : délais de remboursement par mode et annulation par l'hôte."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from bookings import services
from bookings.factories import BookingFactory
from bookings.models import BookingStatus

pytestmark = pytest.mark.django_db

TODAY = date.today()


def confirmed(mode: str, days_ahead: int) -> object:
    return BookingFactory(
        status=BookingStatus.CONFIRMED,
        request__rental_mode=mode,
        request__start_date=TODAY + timedelta(days=days_ahead),
        request__end_date=TODAY + timedelta(days=days_ahead + 30),
    )


@pytest.mark.parametrize(
    ("mode", "days_ahead", "refunded"),
    [
        ("nightly", 7, True),
        ("nightly", 6, False),
        ("monthly", 30, True),
        ("monthly", 29, False),
        ("yearly", 30, True),
        ("yearly", 10, False),
    ],
)
def test_traveler_refund_thresholds(mode, days_ahead, refunded):
    booking = confirmed(mode, days_ahead)
    amount = services.refund_amount_for_cancellation(booking, by=booking.traveler, today=TODAY)
    assert (amount == booking.deposit_amount) is refunded
    if not refunded:
        assert amount == Decimal("0.00")


@pytest.mark.parametrize("mode", ["nightly", "monthly", "yearly"])
def test_host_and_staff_always_refund(mode, staff):
    booking = confirmed(mode, 1)
    assert (
        services.refund_amount_for_cancellation(booking, by=booking.host) == booking.deposit_amount
    )
    assert services.refund_amount_for_cancellation(booking, by=staff) == booking.deposit_amount


def test_host_cancellation_is_audited(caplog):
    booking = confirmed("monthly", 2)
    with caplog.at_level("INFO", logger="loka.audit"):
        services.cancel_booking(booking, by=booking.host, reason="Travaux imprévus")
    assert any("booking_cancelled_by_host" in record.getMessage() for record in caplog.records)
    assert booking.status == BookingStatus.CANCELLED


def test_provider_without_refund_api_leaves_manual_refund(monkeypatch):
    from unittest.mock import MagicMock

    from bookings.models import PaymentKind, PaymentStatus
    from bookings.payments import base
    from bookings.payments.base import PaymentResult
    from bookings.services import handle_payment_result, start_deposit_payment

    booking = BookingFactory(
        status=BookingStatus.AWAITING_DEPOSIT,
        request__rental_mode="nightly",
        request__start_date=TODAY + timedelta(days=30),
        request__end_date=TODAY + timedelta(days=33),
    )
    payment = start_deposit_payment(booking, by=booking.traveler)
    handle_payment_result(
        PaymentResult(provider_ref=payment.provider_ref, succeeded=True, amount=payment.amount)
    )
    booking.refresh_from_db()
    provider = MagicMock()
    provider.refund.side_effect = NotImplementedError("Remboursement manuel via le tableau de bord")
    monkeypatch.setattr(base, "get_payment_provider", lambda: provider)
    monkeypatch.setattr("bookings.services.get_payment_provider", lambda: provider)
    services.cancel_booking(booking, by=booking.traveler, reason="changement")
    refund = booking.payments.get(kind=PaymentKind.REFUND)
    assert refund.status == PaymentStatus.INITIATED
    assert refund.raw_payload["manual"] is True
    assert booking.payments.get(kind=PaymentKind.DEPOSIT).status == PaymentStatus.SUCCEEDED
