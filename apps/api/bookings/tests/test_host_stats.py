from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from bookings.factories import BookingFactory
from bookings.models import BookingStatus
from listings.factories import make_published_property

pytestmark = pytest.mark.django_db

URL = reverse("v1:host-stats")


class TestHostStats:
    def test_requires_host_role(self, as_user, traveler):
        assert as_user(traveler).get(URL).status_code == 403

    def test_aggregates_only_own_data(self, as_user, host, other_host):
        prop = make_published_property(host=host, rating=Decimal("4.5"), review_count=8)
        BookingFactory(
            request__property=prop,
            property=prop,
            host=host,
            status=BookingStatus.COMPLETED,
            total_amount=Decimal("1000.00"),
        )
        # Bien et réservation d'un autre hôte : ne doivent pas compter.
        other = make_published_property(host=other_host)
        BookingFactory(
            request__property=other,
            property=other,
            host=other_host,
            status=BookingStatus.COMPLETED,
            total_amount=Decimal("5000.00"),
        )

        res = as_user(host).get(URL)
        assert res.status_code == 200, res.data
        assert res.data["properties_published"] == 1
        assert res.data["bookings_completed"] == 1
        assert Decimal(res.data["revenue_completed"]) == Decimal("1000.00")
        assert res.data["average_rating"] == 4.5
        assert res.data["reviews_total"] == 8
