from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse

from availability.factories import AvailabilityBlockFactory
from geo.factories import CityFactory, NeighborhoodFactory
from listings.factories import (
    AmenityFactory,
    PropertyFactory,
    make_published_property,
)
from listings.models import LocationPrecision

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:property-list")


def detail_url(prop, action=""):
    name = f"v1:property-{action}" if action else "v1:property-detail"
    return reverse(name, kwargs={"slug": prop.slug})


class TestList:
    def test_only_published(self, api):
        published = make_published_property()
        PropertyFactory()  # draft
        PropertyFactory(status="paused")
        body = api.get(LIST_URL).json()
        assert body["count"] == 1
        card = body["results"][0]
        assert card["slug"] == published.slug
        assert card["cover_photo"]["variants"]["card"]
        assert {p["rental_mode"] for p in card["pricing_plans"]} == {"monthly", "nightly"}
        assert "address_private" not in card
        assert "verification_notes" not in card
        assert "host" not in card

    def test_location_is_rounded_when_approximate(self, api):
        make_published_property(location=Point(10.123456, 36.654321, srid=4326))
        card = api.get(LIST_URL).json()["results"][0]
        assert card["location"] == {"lat": 36.654, "lng": 10.123}

    def test_location_exact_when_allowed(self, api):
        make_published_property(
            location=Point(10.123456, 36.654321, srid=4326),
            location_precision=LocationPrecision.EXACT,
        )
        card = api.get(LIST_URL).json()["results"][0]
        assert card["location"] == {"lat": 36.654321, "lng": 10.123456}

    def test_filters(self, api):
        city = CityFactory(slug="ariana")
        ghazela = NeighborhoodFactory(city=city, slug="ghazela")
        wifi = AmenityFactory(code="wifi")
        a = make_published_property(city=city, neighborhood=ghazela, bedrooms=2, furnished=True)
        a.amenities.add(wifi)
        b = make_published_property(city=city, bedrooms=1, furnished=False)
        b.pricing_plans.filter(rental_mode="monthly").update(price=Decimal("400"))
        make_published_property()  # autre ville

        def slugs(**params):
            return {r["slug"] for r in api.get(LIST_URL, params).json()["results"]}

        assert slugs(city="ariana") == {a.slug, b.slug}
        assert slugs(neighborhood="ghazela") == {a.slug}
        assert slugs(city="ariana", bedrooms_min=2) == {a.slug}
        assert slugs(city="ariana", furnished="false") == {b.slug}
        assert slugs(city="ariana", amenities="wifi") == {a.slug}
        assert slugs(city="ariana", rental_mode="monthly", max_price=500) == {b.slug}
        assert slugs(city="ariana", rental_mode="monthly", min_price=500) == {a.slug}
        assert slugs(city="ariana", rental_mode="yearly") == set()
        assert slugs(property_type="villa") == set()
        assert slugs(city="ariana", guests=4) == {a.slug, b.slug}

    def test_bbox_filter(self, api):
        inside = make_published_property(location=Point(10.19, 36.87, srid=4326))
        make_published_property(location=Point(10.60, 35.80, srid=4326))
        body = api.get(LIST_URL, {"bbox": "10.1,36.8,10.3,36.9"}).json()
        assert [r["slug"] for r in body["results"]] == [inside.slug]
        assert api.get(LIST_URL, {"bbox": "oops"}).json()["count"] == 0

    def test_availability_filter(self, api):
        free = make_published_property()
        busy = make_published_property()
        start = date.today() + timedelta(days=10)
        AvailabilityBlockFactory(property=busy, start=start, end=start + timedelta(days=5))
        body = api.get(
            LIST_URL, {"start": start.isoformat(), "end": (start + timedelta(days=2)).isoformat()}
        ).json()
        assert {r["slug"] for r in body["results"]} == {free.slug}

    def test_ordering_by_price(self, api):
        cheap = make_published_property()
        cheap.pricing_plans.filter(rental_mode="monthly").update(price=Decimal("500"))
        expensive = make_published_property()
        expensive.pricing_plans.filter(rental_mode="monthly").update(price=Decimal("1500"))
        asc = [r["slug"] for r in api.get(LIST_URL, {"ordering": "price"}).json()["results"]]
        desc = [r["slug"] for r in api.get(LIST_URL, {"ordering": "-price"}).json()["results"]]
        assert asc == [cheap.slug, expensive.slug]
        assert desc == [expensive.slug, cheap.slug]

    def test_pagination_capped(self, api):
        for _ in range(3):
            make_published_property()
        body = api.get(LIST_URL, {"page_size": 2}).json()
        assert len(body["results"]) == 2
        assert body["next"]


class TestDetail:
    def test_detail_fields(self, api):
        prop = make_published_property(address_private="12 rue secrète")
        body = api.get(detail_url(prop)).json()
        assert body["title"] == prop.title
        assert len(body["photos"]) == 3
        assert body["host"]["display_name"]
        assert "12 rue secrète" not in str(body)
        assert "address_private" not in body
        assert "verification_notes" not in body
        assert body["pricing_plans"][0]["price_eur"]

    def test_unpublished_is_404(self, api):
        prop = PropertyFactory()
        assert api.get(detail_url(prop)).status_code == 404

    def test_availability_calendar(self, api):
        prop = make_published_property()
        start = date.today() + timedelta(days=5)
        AvailabilityBlockFactory(property=prop, start=start, end=start + timedelta(days=3))
        AvailabilityBlockFactory(
            property=prop, start=start + timedelta(days=2), end=start + timedelta(days=6)
        )
        body = api.get(detail_url(prop, "availability")).json()
        assert body == [
            {"start": start.isoformat(), "end": (start + timedelta(days=6)).isoformat()}
        ]

    def test_quote(self, api):
        prop = make_published_property()
        start = date.today() + timedelta(days=5)
        response = api.get(
            detail_url(prop, "quote"),
            {
                "rental_mode": "nightly",
                "start": start.isoformat(),
                "end": (start + timedelta(days=3)).isoformat(),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["units"] == 3
        assert Decimal(body["subtotal"]) == Decimal("360.00")
        assert Decimal(body["fee"]) == Decimal("36.00")
        assert Decimal(body["total"]) == Decimal("396.00")
        assert body["fee_payer"] == "traveler"
        assert body["available"] is True

    def test_quote_below_min_duration(self, api):
        prop = make_published_property()
        start = date.today() + timedelta(days=5)
        response = api.get(
            detail_url(prop, "quote"),
            {
                "rental_mode": "nightly",
                "start": start.isoformat(),
                "end": (start + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 400
        assert response.json()["code"] == "below_min_duration"

    def test_quote_missing_params(self, api):
        prop = make_published_property()
        assert api.get(detail_url(prop, "quote")).status_code == 400

    def test_amenities_list(self, api):
        AmenityFactory(code="wifi", name="Wi-Fi")
        body = api.get(reverse("v1:amenity-list")).json()
        assert body[0]["code"] == "wifi"
