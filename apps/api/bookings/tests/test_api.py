from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from bookings import services
from bookings.factories import BookingFactory, BookingRequestFactory
from bookings.models import BookingStatus
from bookings.payments.base import PaymentResult
from bookings.payments.mock import MockPaymentProvider
from core.models import SensitiveAccessLog
from listings.factories import make_published_property

pytestmark = pytest.mark.django_db

TODAY = date.today()


def next_10th():
    start = (TODAY + timedelta(days=20)).replace(day=10)
    if start <= TODAY:
        start = date(start.year + (start.month // 12), start.month % 12 + 1, 10)
    return start


def month_after(d):
    return date(d.year + (d.month // 12), d.month % 12 + 1, d.day)


@pytest.fixture
def published():
    return make_published_property(address_private="99 rue secrète")


def request_payload(prop, mode="monthly"):
    start = next_10th()
    end = month_after(start) if mode == "monthly" else start + timedelta(days=3)
    return {
        "property": prop.slug,
        "rental_mode": mode,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "guests": 2,
        "message": "Bonjour",
    }


class TestTravelerRequests:
    url = reverse("v1:request-list")

    def test_create(self, as_user, traveler, published):
        response = as_user(traveler).post(self.url, request_payload(published), format="json")
        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["status"] == "pending"
        assert body["property"]["slug"] == published.slug
        assert Decimal(body["quoted_deposit"]) == Decimal("850.00")

    def test_unauthenticated(self, api, published):
        assert api.post(self.url, request_payload(published), format="json").status_code == 401

    def test_invalid_dates(self, as_user, traveler, published):
        payload = {
            **request_payload(published),
            "end_date": request_payload(published)["start_date"],
        }
        assert as_user(traveler).post(self.url, payload, format="json").status_code == 400

    def test_unpublished_property_invalid(self, as_user, traveler):
        from listings.factories import PropertyFactory

        payload = request_payload(PropertyFactory())
        assert as_user(traveler).post(self.url, payload, format="json").status_code == 400

    def test_list_own_only(self, as_user, traveler):
        mine = BookingRequestFactory(traveler=traveler)
        BookingRequestFactory()
        body = as_user(traveler).get(self.url).json()
        assert [r["public_id"] for r in body["results"]] == [str(mine.public_id)]

    def test_cancel_own_and_not_others(self, as_user, traveler):
        mine = BookingRequestFactory(traveler=traveler)
        other = BookingRequestFactory()
        assert (
            as_user(traveler)
            .post(reverse("v1:request-cancel", kwargs={"public_id": mine.public_id}))
            .json()["status"]
            == "cancelled"
        )
        assert (
            as_user(traveler)
            .post(reverse("v1:request-cancel", kwargs={"public_id": other.public_id}))
            .status_code
            == 404
        )


class TestHostRequests:
    def test_host_sees_requests_on_own_properties(self, as_user, host, other_host):
        mine = BookingRequestFactory(property__host=host)
        BookingRequestFactory(property__host=other_host)
        body = as_user(host).get(reverse("v1:host-request-list")).json()
        assert [r["public_id"] for r in body["results"]] == [str(mine.public_id)]

    def test_traveler_forbidden(self, as_user, traveler):
        assert as_user(traveler).get(reverse("v1:host-request-list")).status_code == 403

    def test_accept_and_decline(self, as_user, host, traveler):
        published = make_published_property(host=host)
        request = services.create_booking_request(
            prop=published,
            traveler=traveler,
            rental_mode="nightly",
            start=TODAY + timedelta(days=5),
            end=TODAY + timedelta(days=8),
            guests=1,
        )
        response = as_user(host).post(
            reverse("v1:host-request-accept", kwargs={"public_id": request.public_id})
        )
        assert response.status_code == 201
        assert response.json()["status"] == "awaiting_deposit"
        # une deuxième acceptation est un conflit
        assert (
            as_user(host)
            .post(reverse("v1:host-request-accept", kwargs={"public_id": request.public_id}))
            .status_code
            == 409
        )
        other = BookingRequestFactory(property=published)
        declined = as_user(host).post(
            reverse("v1:host-request-decline", kwargs={"public_id": other.public_id}),
            {"reason": "Non"},
            format="json",
        )
        assert declined.json()["status"] == "declined"

    def test_other_host_cannot_accept(self, as_user, host, other_host):
        request = BookingRequestFactory(property__host=other_host)
        assert (
            as_user(host)
            .post(reverse("v1:host-request-accept", kwargs={"public_id": request.public_id}))
            .status_code
            == 404
        )


class TestBookings:
    def test_traveler_detail_hides_address_until_confirmed(self, as_user, traveler, published):
        booking = BookingFactory(request__property=published, request__traveler=traveler)
        url = reverse("v1:booking-detail", kwargs={"public_id": booking.public_id})
        body = as_user(traveler).get(url).json()
        assert "address_private" not in body
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        body = as_user(traveler).get(url).json()
        assert body["address_private"] == "99 rue secrète"
        assert (
            SensitiveAccessLog.objects.filter(kind="private_address", actor=traveler).count() == 1
        )

    def test_traveler_cannot_see_others(self, as_user, traveler):
        booking = BookingFactory()
        assert (
            as_user(traveler)
            .get(reverse("v1:booking-detail", kwargs={"public_id": booking.public_id}))
            .status_code
            == 404
        )

    def test_pay_deposit_and_mock_webhook(self, as_user, api, traveler, published):
        booking = BookingFactory(request__property=published, request__traveler=traveler)
        response = as_user(traveler).post(
            reverse("v1:booking-pay-deposit", kwargs={"public_id": booking.public_id})
        )
        assert response.status_code == 201
        payment = response.json()
        assert payment["checkout_url"]
        webhook = api.post(
            reverse("v1:mock-webhook"),
            {
                "provider_ref": booking.payments.get().provider_ref,
                "outcome": "succeeded",
                "amount": str(booking.deposit_amount),
                "currency": "TND",
                "signature": MockPaymentProvider.sign(
                    booking.payments.get().provider_ref, "succeeded"
                ),
            },
            format="json",
        )
        assert webhook.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CONFIRMED

    def test_webhook_bad_signature(self, api, traveler, published):
        booking = BookingFactory(request__property=published, request__traveler=traveler)
        services.start_deposit_payment(booking, by=traveler)
        webhook = api.post(
            reverse("v1:mock-webhook"),
            {
                "provider_ref": booking.payments.get().provider_ref,
                "outcome": "succeeded",
                "amount": "850.00",
                "signature": "forged",
            },
            format="json",
        )
        assert webhook.status_code == 403
        booking.refresh_from_db()
        assert booking.status == BookingStatus.AWAITING_DEPOSIT

    def test_mock_sign_endpoint_restricted(self, as_user, traveler, published):
        booking = BookingFactory(request__property=published)
        payment = services.start_deposit_payment(booking, by=booking.traveler)
        assert (
            as_user(traveler)
            .get(reverse("v1:mock-sign", kwargs={"provider_ref": payment.provider_ref}))
            .status_code
            == 403
        )
        body = (
            as_user(booking.traveler)
            .get(reverse("v1:mock-sign", kwargs={"provider_ref": payment.provider_ref}))
            .json()
        )
        assert set(body["signatures"]) == {"succeeded", "failed"}

    def test_host_cancel_and_contract(self, as_user, host, traveler):
        published = make_published_property(host=host)
        booking = BookingFactory(
            request__property=published, request__traveler=traveler, status=BookingStatus.CONFIRMED
        )
        contract_url = reverse("v1:host-booking-contract", kwargs={"public_id": booking.public_id})
        assert as_user(host).get(contract_url).status_code == 400  # pas encore de contrat
        response = as_user(host).post(
            reverse("v1:host-booking-cancel", kwargs={"public_id": booking.public_id}),
            {"reason": "x"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_staff_lists_everything(self, as_user, staff, traveler):
        BookingFactory()
        BookingFactory()
        assert as_user(staff).get(reverse("v1:staff-booking-list")).json()["count"] == 2
        assert as_user(traveler).get(reverse("v1:staff-booking-list")).status_code == 403

    def test_handle_result_via_service_matches_webhook(self, traveler, published):
        booking = BookingFactory(request__property=published, request__traveler=traveler)
        payment = services.start_deposit_payment(booking, by=traveler)
        services.handle_payment_result(
            PaymentResult(provider_ref=payment.provider_ref, succeeded=True, amount=payment.amount)
        )
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CONFIRMED
