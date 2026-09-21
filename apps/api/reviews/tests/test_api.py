from __future__ import annotations

import pytest
from django.urls import reverse

from bookings.factories import BookingFactory
from bookings.models import BookingStatus
from listings.models import Property
from reviews.models import Review

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:review-list")
PENDING_URL = reverse("v1:review-pending")
MINE_URL = reverse("v1:review-mine")
STAFF_LIST_URL = reverse("v1:staff-review-list")


def _completed_booking(**over):
    return BookingFactory(status=BookingStatus.COMPLETED, **over)


class TestReviewCreation:
    def test_traveler_reviews_completed_stay(self, as_user):
        booking = _completed_booking()
        client = as_user(booking.traveler)
        res = client.post(
            LIST_URL, {"booking": str(booking.public_id), "rating": 5, "comment": "Parfait."}
        )
        assert res.status_code == 201, res.data
        assert Review.objects.filter(booking=booking).count() == 1
        booking.property.refresh_from_db()
        assert booking.property.review_count == 1
        assert float(booking.property.rating) == 5.0

    def test_cannot_review_uncompleted_stay(self, as_user):
        booking = BookingFactory(status=BookingStatus.CONFIRMED)
        client = as_user(booking.traveler)
        res = client.post(LIST_URL, {"booking": str(booking.public_id), "rating": 4})
        assert res.status_code == 409, res.data
        assert Review.objects.count() == 0

    def test_cannot_review_others_booking(self, as_user, traveler):
        booking = _completed_booking()
        res = as_user(traveler).post(LIST_URL, {"booking": str(booking.public_id), "rating": 4})
        assert res.status_code == 409
        assert Review.objects.count() == 0

    def test_no_duplicate_review(self, as_user):
        booking = _completed_booking()
        client = as_user(booking.traveler)
        first = client.post(LIST_URL, {"booking": str(booking.public_id), "rating": 5})
        assert first.status_code == 201
        second = client.post(LIST_URL, {"booking": str(booking.public_id), "rating": 3})
        assert second.status_code == 409

    def test_anonymous_cannot_create(self, api):
        booking = _completed_booking()
        res = api.post(LIST_URL, {"booking": str(booking.public_id), "rating": 5})
        assert res.status_code in (401, 403)


class TestReviewListing:
    def test_public_list_by_property(self, as_user, api):
        booking = _completed_booking()
        as_user(booking.traveler).post(
            LIST_URL, {"booking": str(booking.public_id), "rating": 5, "comment": "Top."}
        )
        res = api.get(LIST_URL, {"property": booking.property.slug})
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["comment"] == "Top."
        assert "author_name" in res.data["results"][0]

    def test_pending_lists_completed_without_review(self, as_user):
        booking = _completed_booking()
        client = as_user(booking.traveler)
        res = client.get(PENDING_URL)
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["property_slug"] == booking.property.slug
        client.post(LIST_URL, {"booking": str(booking.public_id), "rating": 5})
        assert len(client.get(PENDING_URL).data) == 0

    def test_mine_lists_own_reviews(self, as_user):
        booking = _completed_booking()
        client = as_user(booking.traveler)
        client.post(LIST_URL, {"booking": str(booking.public_id), "rating": 4})
        res = client.get(MINE_URL)
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["property_title"] == booking.property.title


class TestStaffModeration:
    def _reviewed(self, as_user):
        booking = _completed_booking()
        as_user(booking.traveler).post(
            LIST_URL, {"booking": str(booking.public_id), "rating": 5, "comment": "Nickel."}
        )
        return booking

    def test_non_staff_forbidden(self, as_user, traveler):
        assert as_user(traveler).get(STAFF_LIST_URL).status_code == 403

    def test_staff_lists_all_reviews(self, as_user, staff):
        self._reviewed(as_user)
        res = as_user(staff).get(STAFF_LIST_URL)
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["is_published"] is True
        assert "author_email" in res.data["results"][0]

    def test_staff_hides_review_and_updates_rating(self, as_user, staff):
        booking = self._reviewed(as_user)
        review = Review.objects.get(booking=booking)
        booking.property.refresh_from_db()
        assert booking.property.review_count == 1
        url = reverse("v1:staff-review-set-visibility", args=[review.public_id])
        res = as_user(staff).post(url, {"is_published": False})
        assert res.status_code == 200
        assert res.data["is_published"] is False
        booking.property.refresh_from_db()
        assert booking.property.review_count == 0
        assert booking.property.rating is None


class TestRatingAggregation:
    def test_average_over_two_reviews(self, as_user):
        prop = None
        ratings = [5, 4]
        for r in ratings:
            booking = _completed_booking()
            if prop is None:
                prop = booking.property
            else:
                booking.property = prop
                booking.save(update_fields=["property"])
            as_user(booking.traveler).post(
                LIST_URL, {"booking": str(booking.public_id), "rating": r}
            )
        assert prop is not None
        prop.refresh_from_db()
        assert prop.review_count == 2
        assert float(prop.rating) == 4.5
        assert Property.objects.get(pk=prop.pk).rating == prop.rating
