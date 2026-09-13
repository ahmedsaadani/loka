import pytest
from django.urls import reverse

from bookings.factories import BookingFactory, BookingRequestFactory
from leads.factories import LeadFactory
from listings.factories import PropertyFactory, make_published_property
from listings.models import Property

pytestmark = pytest.mark.django_db

URL = reverse("v1:staff-stats")


class TestStaffStats:
    def test_requires_staff(self, api, as_user, traveler, host):
        assert api.get(URL).status_code == 401
        assert as_user(traveler).get(URL).status_code == 403
        assert as_user(host).get(URL).status_code == 403

    def test_counts(self, as_user, staff):
        make_published_property()
        PropertyFactory(status="pending_review")
        BookingRequestFactory(status="accepted")
        BookingRequestFactory(status="accepted")
        BookingRequestFactory(status="declined")
        BookingRequestFactory(status="pending")
        BookingFactory(status="confirmed")
        LeadFactory()
        body = as_user(staff).get(URL).json()
        # Les factories de réservation créent aussi des biens publiés.
        assert body["properties_published"] == Property.objects.filter(status="published").count()
        assert body["properties_published"] >= 1
        assert body["pending_review"] == 1
        # BookingFactory crée aussi une demande acceptée : 3 acceptées, 1 refusée.
        assert body["requests"]["accepted"] == 3
        assert body["acceptance_rate"] == pytest.approx(3 / 4, abs=0.001)
        assert body["bookings_confirmed"] == 1
        assert body["leads_new"] == 1
        assert body["hosts"] >= 1

    def test_acceptance_rate_none_without_answers(self, as_user, staff):
        assert as_user(staff).get(URL).json()["acceptance_rate"] is None
