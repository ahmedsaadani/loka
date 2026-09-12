from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone

from availability.models import AvailabilityBlock, BlockKind
from bookings import services
from bookings.factories import BookingFactory, BookingRequestFactory
from bookings.models import (
    Booking,
    BookingRequest,
    BookingRequestStatus,
    BookingStatus,
    PaymentKind,
    PaymentStatus,
)
from bookings.payments.base import PaymentResult
from bookings.payments.mock import MockPaymentProvider
from bookings.tasks import (
    advance_booking_statuses,
    expire_pending_requests,
    remind_hosts_of_pending_requests,
)
from core.exceptions import ConflictError, DomainError
from core.state import InvalidTransition
from listings.factories import PropertyFactory, make_published_property

pytestmark = pytest.mark.django_db

TODAY = date.today()
RS = BookingRequestStatus
BS = BookingStatus


def month_later(d: date) -> date:
    month = d.month % 12 + 1
    year = d.year + (1 if month == 1 else 0)
    day = min(d.day, 28)
    return date(year, month, day)


@pytest.fixture
def published():
    return make_published_property()


def create_request(prop, traveler, mode="monthly", start=None, end=None, guests=2):
    start = start or (TODAY + timedelta(days=15)).replace(day=10)
    if start < TODAY:
        start = month_later(start)
    end = end or (month_later(start) if mode != "nightly" else start + timedelta(days=3))
    return services.create_booking_request(
        prop=prop, traveler=traveler, rental_mode=mode, start=start, end=end, guests=guests
    )


class TestCreateRequest:
    def test_monthly_request_snapshot_and_email(self, published, traveler):
        request = create_request(published, traveler)
        assert request.status == RS.PENDING
        assert request.quoted_units == 1
        assert request.quoted_total == Decimal("850.00")
        assert request.quoted_fee == Decimal("42.50")
        assert request.quoted_deposit == Decimal("850.00")
        assert request.expires_at > timezone.now() + timedelta(hours=47)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [published.host.email]

    def test_nightly_request(self, published, traveler):
        request = create_request(published, traveler, mode="nightly")
        assert request.quoted_units == 3
        assert request.quoted_total == Decimal("396.00")
        assert request.quoted_deposit == Decimal("118.80")

    def test_unpublished_refused(self, traveler):
        with pytest.raises(DomainError) as exc:
            create_request(PropertyFactory(), traveler)
        assert exc.value.get_codes() == "not_published"

    def test_own_property_refused(self, published):
        with pytest.raises(DomainError):
            create_request(published, published.host)

    def test_too_many_guests(self, published, traveler):
        with pytest.raises(ValidationError):
            create_request(published, traveler, guests=99)

    def test_no_plan_for_mode(self, published, traveler):
        with pytest.raises(DomainError) as exc:
            create_request(published, traveler, mode="yearly")
        assert exc.value.get_codes() == "no_plan"

    def test_unavailable_dates(self, published, traveler):
        start = (TODAY + timedelta(days=15)).replace(day=10)
        if start < TODAY:
            start = month_later(start)
        AvailabilityBlock.objects.create(
            property=published,
            start=start,
            end=start + timedelta(days=2),
            kind=BlockKind.BLOCKED_BY_HOST,
        )
        with pytest.raises(ConflictError):
            create_request(published, traveler, start=start)

    def test_duplicate_pending_request(self, published, traveler):
        create_request(published, traveler)
        with pytest.raises(ConflictError) as exc:
            create_request(published, traveler)
        assert exc.value.get_codes() == "duplicate"

    def test_past_dates(self, published, traveler):
        with pytest.raises(ValidationError):
            create_request(
                published, traveler, start=TODAY - timedelta(days=1), end=TODAY + timedelta(days=2)
            )


class TestAcceptDecline:
    def test_accept_creates_booking_and_block(self, published, traveler):
        request = create_request(published, traveler)
        mail.outbox.clear()
        booking = services.accept_request(request, by=published.host)
        request.refresh_from_db()
        assert request.status == RS.ACCEPTED
        assert booking.status == BS.AWAITING_DEPOSIT
        assert booking.host == published.host
        assert booking.fee_payer == "host"
        assert booking.deposit_amount == Decimal("850.00")
        block = AvailabilityBlock.objects.get(booking=booking)
        assert block.kind == BlockKind.BOOKED
        assert mail.outbox[-1].to == [traveler.email]

    def test_accept_declines_overlapping_requests(self, published, traveler):
        first = create_request(published, traveler)
        from accounts.factories import TravelerFactory

        second = create_request(published, TravelerFactory())
        services.accept_request(first, by=published.host)
        second.refresh_from_db()
        assert second.status == RS.DECLINED
        assert second.decline_reason

    def test_accept_expired_request(self, published, traveler):
        request = create_request(published, traveler)
        request.expires_at = timezone.now() - timedelta(minutes=1)
        request.save()
        with pytest.raises(ConflictError):
            services.accept_request(request, by=published.host)
        request.refresh_from_db()
        assert request.status == RS.EXPIRED

    def test_accept_twice_forbidden(self, published, traveler):
        request = create_request(published, traveler)
        services.accept_request(request, by=published.host)
        with pytest.raises(InvalidTransition):
            services.accept_request(request, by=published.host)

    def test_decline_and_cancel(self, published, traveler):
        request = create_request(published, traveler)
        services.decline_request(request, by=published.host, reason="Indisponible")
        assert request.status == RS.DECLINED
        assert request.decline_reason == "Indisponible"
        other = BookingRequestFactory(property=published, traveler=traveler)
        services.cancel_request(other, by=traveler)
        assert other.status == RS.CANCELLED

    @pytest.mark.parametrize("status", [RS.ACCEPTED, RS.DECLINED, RS.EXPIRED, RS.CANCELLED])
    def test_terminal_request_statuses(self, status, staff):
        request = BookingRequestFactory(status=status)
        for target in (RS.ACCEPTED, RS.DECLINED, RS.EXPIRED, RS.CANCELLED):
            with pytest.raises(InvalidTransition):
                from core.state import transition

                transition(request, target, actor=staff)


class TestExpiryTasks:
    def test_expire_task(self, published, traveler):
        request = create_request(published, traveler)
        BookingRequest.objects.filter(pk=request.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        fresh = BookingRequestFactory(property=published)
        mail.outbox.clear()
        assert expire_pending_requests() == 1
        request.refresh_from_db()
        fresh.refresh_from_db()
        assert request.status == RS.EXPIRED
        assert fresh.status == RS.PENDING
        assert mail.outbox[0].to == [traveler.email]

    def test_reminder_task_once(self, published, traveler):
        request = create_request(published, traveler)
        BookingRequest.objects.filter(pk=request.pk).update(
            expires_at=timezone.now() + timedelta(hours=20)
        )
        mail.outbox.clear()
        assert remind_hosts_of_pending_requests() == 1
        assert remind_hosts_of_pending_requests() == 0
        assert "Rappel" in mail.outbox[0].subject
        request.refresh_from_db()
        assert request.reminder_sent_at is not None

    def test_reminder_not_sent_too_early(self, published, traveler):
        create_request(published, traveler)  # expire dans 48 h
        assert remind_hosts_of_pending_requests() == 0


class TestPayments:
    def test_deposit_flow(self, published, traveler):
        booking = services.accept_request(create_request(published, traveler), by=published.host)
        payment = services.start_deposit_payment(booking, by=traveler)
        assert payment.kind == PaymentKind.DEPOSIT
        assert payment.status == PaymentStatus.INITIATED
        assert payment.checkout_url.startswith("http://localhost:3000/paiement/mock")
        # idempotent
        assert services.start_deposit_payment(booking, by=traveler).pk == payment.pk
        mail.outbox.clear()
        result = PaymentResult(
            provider_ref=payment.provider_ref, succeeded=True, amount=payment.amount
        )
        services.handle_payment_result(result)
        payment.refresh_from_db()
        booking.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert booking.status == BS.CONFIRMED
        assert {m.to[0] for m in mail.outbox} == {traveler.email, published.host.email}
        # webhook rejoué : rien ne change
        services.handle_payment_result(result)
        assert booking.payments.count() == 1

    def test_failed_payment_keeps_awaiting(self, published, traveler):
        booking = services.accept_request(create_request(published, traveler), by=published.host)
        payment = services.start_deposit_payment(booking, by=traveler)
        services.handle_payment_result(
            PaymentResult(provider_ref=payment.provider_ref, succeeded=False, amount=payment.amount)
        )
        booking.refresh_from_db()
        assert booking.status == BS.AWAITING_DEPOSIT
        assert booking.payments.get().status == PaymentStatus.FAILED

    def test_amount_mismatch(self, published, traveler):
        booking = services.accept_request(create_request(published, traveler), by=published.host)
        payment = services.start_deposit_payment(booking, by=traveler)
        with pytest.raises(DomainError):
            services.handle_payment_result(
                PaymentResult(
                    provider_ref=payment.provider_ref, succeeded=True, amount=Decimal("1")
                )
            )
        booking.refresh_from_db()
        assert booking.status == BS.AWAITING_DEPOSIT

    def test_pay_non_awaiting_booking(self, traveler):
        booking = BookingFactory(status=BS.CONFIRMED)
        with pytest.raises(ConflictError):
            services.start_deposit_payment(booking, by=traveler)

    def test_mock_webhook_signature(self):
        provider = MockPaymentProvider()
        payload = {
            "provider_ref": "mock_x",
            "outcome": "succeeded",
            "amount": "10.00",
            "signature": "bad",
        }
        with pytest.raises(ValueError):
            provider.parse_webhook(payload, {})
        payload["signature"] = provider.sign("mock_x", "succeeded")
        assert provider.parse_webhook(payload, {}).succeeded is True


class TestCancellation:
    def confirmed_booking(self, published, traveler, days_ahead=30):
        start = TODAY + timedelta(days=days_ahead)
        request = create_request(
            published, traveler, mode="nightly", start=start, end=start + timedelta(days=3)
        )
        booking = services.accept_request(request, by=published.host)
        payment = services.start_deposit_payment(booking, by=traveler)
        services.handle_payment_result(
            PaymentResult(provider_ref=payment.provider_ref, succeeded=True, amount=payment.amount)
        )
        booking.refresh_from_db()
        return booking

    def test_traveler_cancels_early_gets_refund(self, published, traveler):
        booking = self.confirmed_booking(published, traveler, days_ahead=30)
        services.cancel_booking(booking, by=traveler, reason="changement de plans")
        assert booking.status == BS.CANCELLED
        assert booking.cancelled_by == traveler
        refund = booking.payments.get(kind=PaymentKind.REFUND)
        assert refund.amount == booking.deposit_amount
        assert booking.payments.get(kind=PaymentKind.DEPOSIT).status == PaymentStatus.REFUNDED
        assert AvailabilityBlock.objects.filter(booking=booking).count() == 0

    def test_traveler_cancels_late_no_refund(self, published, traveler):
        booking = self.confirmed_booking(published, traveler, days_ahead=3)
        services.cancel_booking(booking, by=traveler)
        assert not booking.payments.filter(kind=PaymentKind.REFUND).exists()

    def test_host_cancels_always_refunds(self, published, traveler):
        booking = self.confirmed_booking(published, traveler, days_ahead=3)
        services.cancel_booking(booking, by=published.host, reason="dégât des eaux")
        assert booking.payments.filter(kind=PaymentKind.REFUND).exists()

    def test_cancel_awaiting_deposit_no_payment(self, published, traveler):
        booking = services.accept_request(create_request(published, traveler), by=published.host)
        services.cancel_booking(booking, by=traveler)
        assert booking.status == BS.CANCELLED
        assert booking.payments.count() == 0

    def test_cancel_completed_forbidden(self, traveler):
        booking = BookingFactory(status=BS.COMPLETED)
        with pytest.raises(InvalidTransition):
            services.cancel_booking(booking, by=traveler)


class TestBookingTransitions:
    ALLOWED = {
        (BS.AWAITING_DEPOSIT, BS.CONFIRMED),
        (BS.AWAITING_DEPOSIT, BS.CANCELLED),
        (BS.CONFIRMED, BS.IN_PROGRESS),
        (BS.CONFIRMED, BS.CANCELLED),
        (BS.IN_PROGRESS, BS.COMPLETED),
    }

    def test_table(self):
        declared = {(s, t) for s, ts in Booking.TRANSITIONS.items() for t in ts}
        assert declared == self.ALLOWED

    @pytest.mark.parametrize("source", list(BS.values))
    @pytest.mark.parametrize("target", list(BS.values))
    def test_every_pair(self, source, target):
        from core.state import transition

        booking = BookingFactory(status=source)
        if (source, target) in self.ALLOWED:
            transition(booking, target)
            assert booking.status == target
        else:
            with pytest.raises(InvalidTransition):
                transition(booking, target)

    def test_advance_task(self):
        starting = BookingFactory(
            status=BS.CONFIRMED,
            request__start_date=TODAY,
            request__end_date=TODAY + timedelta(days=3),
        )
        ending = BookingFactory(
            status=BS.IN_PROGRESS,
            request__start_date=TODAY - timedelta(days=3),
            request__end_date=TODAY,
        )
        future = BookingFactory(status=BS.CONFIRMED)
        assert advance_booking_statuses() == 2
        starting.refresh_from_db()
        ending.refresh_from_db()
        future.refresh_from_db()
        assert starting.status == BS.IN_PROGRESS
        assert ending.status == BS.COMPLETED
        assert future.status == BS.CONFIRMED
