from decimal import Decimal

import pytest
from django.urls import reverse

from geo.factories import CityFactory, NeighborhoodFactory
from listings.factories import PricingPlanFactory, PropertyFactory

pytestmark = pytest.mark.django_db


class TestCities:
    def test_list_with_counts_and_average(self, api):
        city = CityFactory(slug="ariana", name="Ariana", is_featured=True)
        neighborhood = NeighborhoodFactory(city=city, slug="ghazela")
        for price in ("800", "1000"):
            prop = PropertyFactory(published=True, city=city, neighborhood=neighborhood)
            PricingPlanFactory(property=prop, rental_mode="monthly", price=Decimal(price))
        PropertyFactory(city=city, neighborhood=neighborhood)  # brouillon : non compté
        CityFactory(slug="sfax")

        response = api.get(reverse("v1:city-list"))
        assert response.status_code == 200
        results = response.json()["results"]
        assert results[0]["slug"] == "ariana"
        assert results[0]["property_count"] == 2
        assert Decimal(results[0]["avg_monthly_price"]) == Decimal("900")
        assert results[0]["centroid"] == {"lat": 36.86, "lng": 10.18}

    def test_filter_featured(self, api):
        CityFactory(slug="a", is_featured=True)
        CityFactory(slug="b", is_featured=False)
        body = api.get(reverse("v1:city-list"), {"is_featured": "true"}).json()
        assert [c["slug"] for c in body["results"]] == ["a"]

    def test_detail_includes_neighborhoods_and_seo(self, api):
        city = CityFactory(slug="tunis", seo_title="Location Tunis", intro_text="Intro")
        NeighborhoodFactory(city=city, slug="lac-2", name="Lac 2")
        body = api.get(reverse("v1:city-detail", kwargs={"slug": "tunis"})).json()
        assert body["seo_title"] == "Location Tunis"
        assert body["intro_text"] == "Intro"
        assert body["neighborhoods"][0]["slug"] == "lac-2"
        assert body["neighborhoods"][0]["property_count"] == 0

    def test_detail_404(self, api):
        assert api.get(reverse("v1:city-detail", kwargs={"slug": "nope"})).status_code == 404


class TestNeighborhoods:
    def test_list_filtered_by_city(self, api):
        city = CityFactory(slug="ariana")
        NeighborhoodFactory(city=city, slug="ghazela")
        NeighborhoodFactory(slug="autre")
        body = api.get(reverse("v1:neighborhood-list"), {"city__slug": "ariana"}).json()
        assert [n["slug"] for n in body["results"]] == ["ghazela"]

    def test_detail(self, api):
        city = CityFactory(slug="ariana", name="Ariana")
        NeighborhoodFactory(city=city, slug="ghazela", name="Ghazela", seo_description="Desc")
        url = reverse("v1:neighborhood-detail", kwargs={"city_slug": "ariana", "slug": "ghazela"})
        body = api.get(url).json()
        assert body["name"] == "Ghazela"
        assert body["city"]["slug"] == "ariana"
        assert body["seo_description"] == "Desc"

    def test_detail_wrong_city_404(self, api):
        NeighborhoodFactory(city=CityFactory(slug="ariana"), slug="ghazela")
        url = reverse("v1:neighborhood-detail", kwargs={"city_slug": "tunis", "slug": "ghazela"})
        assert api.get(url).status_code == 404
