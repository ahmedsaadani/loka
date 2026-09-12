from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from geo.factories import CityFactory, NeighborhoodFactory
from listings.factories import (
    AmenityFactory,
    PropertyFactory,
    PropertyPhotoFactory,
    make_published_property,
)
from listings.models import Property

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:host-property-list")


def url(prop, action=""):
    name = f"v1:host-property-{action}" if action else "v1:host-property-detail"
    return reverse(name, kwargs={"public_id": prop.public_id})


def png_upload(name="photo.png"):
    buffer = BytesIO()
    Image.new("RGB", (640, 480), "#334455").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def payload():
    city = CityFactory(slug="ariana")
    neighborhood = NeighborhoodFactory(city=city, slug="ghazela")
    AmenityFactory(code="wifi")
    return {
        "title": "Studio meublé Ghazela",
        "description": "d" * 100,
        "property_type": "studio",
        "rooms_label": "",
        "bedrooms": 0,
        "bathrooms": 1,
        "surface_m2": 30,
        "max_guests": 1,
        "city": city.slug,
        "neighborhood": neighborhood.slug,
        "address_private": "3 rue des Lilas",
        "location": {"lat": 36.8975, "lng": 10.1875},
        "amenities": ["wifi"],
        "distance_notes": {"ESPRIT": "5 min"},
    }


class TestPermissions:
    def test_unauthenticated(self, api):
        assert api.get(LIST_URL).status_code == 401

    def test_traveler_forbidden(self, as_user, traveler, payload):
        assert as_user(traveler).get(LIST_URL).status_code == 403
        assert as_user(traveler).post(LIST_URL, payload, format="json").status_code == 403

    def test_host_sees_only_own(self, as_user, host, other_host):
        mine = PropertyFactory(host=host)
        theirs = PropertyFactory(host=other_host)
        body = as_user(host).get(LIST_URL).json()
        assert [p["public_id"] for p in body["results"]] == [str(mine.public_id)]
        assert as_user(host).get(url(theirs)).status_code == 404
        assert as_user(host).patch(url(theirs), {"title": "hack"}, format="json").status_code == 404
        assert as_user(host).post(url(theirs, "submit")).status_code == 404
        assert as_user(host).delete(url(theirs)).status_code == 404


class TestCrud:
    def test_create(self, as_user, host, payload):
        response = as_user(host).post(LIST_URL, payload, format="json")
        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["status"] == "draft"
        assert body["address_private"] == "3 rue des Lilas"
        assert body["location"] == {"lat": 36.8975, "lng": 10.1875}
        assert [a["code"] for a in body["amenities"]] == ["wifi"]
        assert set(body["readiness_errors"]) == {"photos", "pricing_plans"}
        prop = Property.objects.get(public_id=body["public_id"])
        assert prop.host == host
        assert prop.slug

    def test_create_invalid(self, as_user, host, payload):
        bad = {**payload, "city": "inconnue", "location": {"lat": 0, "lng": 0}, "max_guests": 0}
        response = as_user(host).post(LIST_URL, bad, format="json")
        assert response.status_code == 400
        errors = response.json()["errors"]
        assert {"city", "location", "max_guests"} <= set(errors)

    def test_neighborhood_must_match_city(self, as_user, host, payload):
        other = NeighborhoodFactory(slug="ailleurs")
        response = as_user(host).post(
            LIST_URL, {**payload, "neighborhood": other.slug}, format="json"
        )
        assert response.status_code == 400
        assert "neighborhood" in response.json()["errors"]

    def test_patch_draft(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).patch(url(prop), {"title": "Nouveau titre valide"}, format="json")
        assert response.status_code == 200
        assert response.json()["title"] == "Nouveau titre valide"

    def test_patch_published_is_conflict(self, as_user, host):
        prop = make_published_property(host=host)
        response = as_user(host).patch(url(prop), {"title": "Nouveau titre valide"}, format="json")
        assert response.status_code == 409
        assert response.json()["code"] == "not_editable"

    def test_cannot_set_status_or_host_via_patch(self, as_user, host, other_host):
        prop = PropertyFactory(host=host)
        as_user(host).patch(
            url(prop), {"status": "published", "host": other_host.pk}, format="json"
        )
        prop.refresh_from_db()
        assert prop.status == "draft"
        assert prop.host == host

    def test_delete_only_draft(self, as_user, host):
        draft = PropertyFactory(host=host)
        published = make_published_property(host=host)
        assert as_user(host).delete(url(draft)).status_code == 204
        assert as_user(host).delete(url(published)).status_code == 409


class TestLifecycle:
    def test_submit_incomplete(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(url(prop, "submit"))
        assert response.status_code == 400
        assert "photos" in response.json()["errors"]

    def test_submit_then_withdraw(self, as_user, host):
        prop = make_published_property(host=host, status="draft")
        assert as_user(host).post(url(prop, "submit")).json()["status"] == "pending_review"
        assert as_user(host).post(url(prop, "withdraw")).json()["status"] == "draft"

    def test_pause_resume(self, as_user, host):
        prop = make_published_property(host=host)
        assert (
            as_user(host)
            .post(url(prop, "pause"), {"note": "travaux"}, format="json")
            .json()["status"]
            == "paused"
        )
        assert as_user(host).post(url(prop, "resume")).json()["status"] == "published"

    def test_invalid_transition_409(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(url(prop, "pause"))
        assert response.status_code == 409
        assert response.json()["code"] == "invalid_transition"


class TestPhotosAndPricing:
    def test_upload_photo(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(
            url(prop, "upload-photo"),
            {"image": png_upload(), "alt_text": "Salon"},
            format="multipart",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["is_cover"] is True
        assert body["taken_by_team"] is False
        assert body["variants"]["card"]

    def test_upload_not_image(self, as_user, host):
        prop = PropertyFactory(host=host)
        fake = SimpleUploadedFile("x.png", b"pas une image", content_type="image/png")
        response = as_user(host).post(
            url(prop, "upload-photo"), {"image": fake}, format="multipart"
        )
        assert response.status_code == 400

    def test_reorder_and_delete(self, as_user, host):
        prop = PropertyFactory(host=host)
        photos = [
            PropertyPhotoFactory(property=prop, order=i + 1, is_cover=i == 0) for i in range(2)
        ]
        order = [str(photos[1].public_id), str(photos[0].public_id)]
        response = as_user(host).post(url(prop, "reorder-photos"), {"order": order}, format="json")
        assert response.status_code == 200
        assert response.json()[0]["public_id"] == order[0]
        delete_url = f"{url(prop)}photos/{photos[1].public_id}/"
        assert as_user(host).delete(delete_url).status_code == 204
        assert prop.photos.count() == 1

    def test_cannot_delete_other_hosts_photo_via_own_property(self, as_user, host):
        prop = PropertyFactory(host=host)
        foreign = PropertyPhotoFactory()
        delete_url = f"{url(prop)}photos/{foreign.public_id}/"
        assert as_user(host).delete(delete_url).status_code == 404

    def test_set_and_delete_pricing(self, as_user, host):
        prop = PropertyFactory(host=host)
        response = as_user(host).post(
            url(prop, "set-pricing"),
            {"rental_mode": "monthly", "price": "900.00", "min_duration": 3},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()[0]["price"] == "900.00"
        bad = as_user(host).post(
            url(prop, "set-pricing"), {"rental_mode": "weekly", "price": "-1"}, format="json"
        )
        assert bad.status_code == 400
        assert as_user(host).delete(f"{url(prop)}pricing/monthly/").status_code == 204
        assert prop.pricing_plans.count() == 0
