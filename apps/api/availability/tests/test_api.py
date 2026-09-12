from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse

from availability.factories import AvailabilityBlockFactory, ExternalCalendarFactory
from availability.models import AvailabilityBlock, BlockKind
from bookings.factories import BookingFactory
from listings.factories import PropertyFactory

pytestmark = pytest.mark.django_db

TODAY = date.today()


def blocks_url(prop):
    return reverse("v1:host-blocks", kwargs={"property_public_id": prop.public_id})


def calendars_url(prop):
    return reverse("v1:host-calendars", kwargs={"property_public_id": prop.public_id})


class TestPermissions:
    def test_unauthenticated(self, api, host):
        assert api.get(blocks_url(PropertyFactory(host=host))).status_code == 401

    def test_traveler_forbidden(self, as_user, traveler, host):
        assert as_user(traveler).get(blocks_url(PropertyFactory(host=host))).status_code == 403

    def test_other_host_404(self, as_user, host, other_host):
        prop = PropertyFactory(host=other_host)
        client = as_user(host)
        assert client.get(blocks_url(prop)).status_code == 404
        assert (
            client.post(
                blocks_url(prop), {"start": TODAY, "end": TODAY + timedelta(days=2)}
            ).status_code
            == 404
        )
        assert client.get(calendars_url(prop)).status_code == 404


class TestBlocks:
    def test_list_and_create(self, as_user, host):
        prop = PropertyFactory(host=host)
        client = as_user(host)
        response = client.post(
            blocks_url(prop),
            {
                "start": (TODAY + timedelta(days=3)).isoformat(),
                "end": (TODAY + timedelta(days=6)).isoformat(),
                "note": "famille",
            },
        )
        assert response.status_code == 201
        assert response.json()["kind"] == "blocked_by_host"
        listing = client.get(blocks_url(prop)).json()
        assert len(listing) == 1
        assert listing[0]["note"] == "famille"

    def test_create_invalid_range(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(
            blocks_url(prop), {"start": TODAY.isoformat(), "end": TODAY.isoformat()}
        )
        assert response.status_code == 400

    def test_create_over_booking_conflict(self, as_user, host):
        booking = BookingFactory(request__property__host=host)
        AvailabilityBlock.objects.create(
            property=booking.property,
            start=booking.start_date,
            end=booking.end_date,
            kind=BlockKind.BOOKED,
            booking=booking,
        )
        response = as_user(host).post(
            blocks_url(booking.property),
            {"start": booking.start_date.isoformat(), "end": booking.end_date.isoformat()},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "booked"

    def test_delete_block(self, as_user, host):
        prop = PropertyFactory(host=host)
        block = AvailabilityBlockFactory(property=prop)
        url = reverse(
            "v1:host-block-detail",
            kwargs={"property_public_id": prop.public_id, "block_id": block.pk},
        )
        assert as_user(host).delete(url).status_code == 204

    def test_delete_booked_block_conflict(self, as_user, host):
        booking = BookingFactory(request__property__host=host)
        block = AvailabilityBlock.objects.create(
            property=booking.property,
            start=booking.start_date,
            end=booking.end_date,
            kind=BlockKind.BOOKED,
            booking=booking,
        )
        url = reverse(
            "v1:host-block-detail",
            kwargs={"property_public_id": booking.property.public_id, "block_id": block.pk},
        )
        assert as_user(host).delete(url).status_code == 409


class TestCalendars:
    def test_add_calendar_triggers_sync(self, as_user, host):
        prop = PropertyFactory(host=host)
        with patch("availability.views.sync_external_calendar.delay") as delay:
            response = as_user(host).post(
                calendars_url(prop),
                {"ical_url": "https://airbnb.com/calendar/ical/1.ics", "source": "airbnb"},
            )
        assert response.status_code == 201
        delay.assert_called_once()
        assert len(as_user(host).get(calendars_url(prop)).json()) == 1

    def test_http_url_rejected(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(
            calendars_url(prop), {"ical_url": "http://insecure/cal.ics", "source": "other"}
        )
        assert response.status_code == 400

    def test_delete_calendar_removes_blocks(self, as_user, host):
        prop = PropertyFactory(host=host)
        calendar = ExternalCalendarFactory(property=prop)
        AvailabilityBlockFactory(
            property=prop, kind=BlockKind.EXTERNAL_ICAL, external_calendar=calendar
        )
        url = reverse(
            "v1:host-calendar-detail",
            kwargs={"property_public_id": prop.public_id, "calendar_id": calendar.pk},
        )
        assert as_user(host).delete(url).status_code == 204
        assert AvailabilityBlock.objects.count() == 0
