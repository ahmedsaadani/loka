import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from core.models import SensitiveAccessLog
from listings.factories import PropertyFactory, make_published_property
from listings.tests.test_host_api import png_upload

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:staff-property-list")


def url(prop, action=""):
    name = f"v1:staff-property-{action}" if action else "v1:staff-property-detail"
    return reverse(name, kwargs={"public_id": prop.public_id})


class TestPermissions:
    def test_unauthenticated(self, api):
        assert api.get(LIST_URL).status_code == 401

    @pytest.mark.parametrize("role", ["traveler", "host"])
    def test_non_staff_forbidden(self, as_user, role, traveler, host):
        user = traveler if role == "traveler" else host
        prop = PropertyFactory(host=host, status="pending_review")
        client = as_user(user)
        assert client.get(LIST_URL).status_code == 403
        assert client.get(url(prop)).status_code == 403
        assert (
            client.post(
                url(prop, "publish"), {"verification_level": "verified", "condition_grade": "good"}
            ).status_code
            == 403
        )
        assert client.post(url(prop, "reject"), {"reason": "x"}).status_code == 403
        assert (
            client.post(
                url(prop, "schedule-visit"), {"visit_at": timezone.now().isoformat()}
            ).status_code
            == 403
        )


class TestQueue:
    def test_list_filter_by_status(self, as_user, staff):
        pending = PropertyFactory(status="pending_review")
        PropertyFactory(status="draft")
        body = as_user(staff).get(LIST_URL, {"status": "pending_review"}).json()
        assert [p["public_id"] for p in body["results"]] == [str(pending.public_id)]
        assert body["results"][0]["host_email"]

    def test_retrieve_logs_private_address_access(self, as_user, staff):
        prop = PropertyFactory(address_private="7 rue cachée")
        body = as_user(staff).get(url(prop)).json()
        assert body["address_private"] == "7 rue cachée"
        assert body["verification_notes"] == ""
        log = SensitiveAccessLog.objects.get()
        assert log.kind == "private_address"
        assert log.actor == staff
        assert log.target_id == str(prop.pk)


class TestActions:
    def test_schedule_visit(self, as_user, staff):
        prop = PropertyFactory(status="pending_review")
        when = timezone.now() + timezone.timedelta(days=2)
        response = as_user(staff).post(
            url(prop, "schedule-visit"),
            {"visit_at": when.isoformat(), "note": "matin"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "needs_visit"
        assert response.json()["visit_scheduled_at"]

    def test_publish_sends_email(self, as_user, staff):
        prop = make_published_property(status="needs_visit")
        response = as_user(staff).post(
            url(prop, "publish"),
            {"verification_level": "selection", "condition_grade": "excellent", "notes": "ok"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["status"] == "published"
        assert body["verification_level"] == "selection"
        assert len(mail.outbox) == 1
        assert prop.host.email in mail.outbox[0].to
        assert "en ligne" in mail.outbox[0].subject

    def test_publish_incomplete_property(self, as_user, staff):
        prop = PropertyFactory(status="pending_review")
        response = as_user(staff).post(
            url(prop, "publish"),
            {"verification_level": "verified", "condition_grade": "good"},
            format="json",
        )
        assert response.status_code == 400
        assert "photos" in response.json()["errors"]

    def test_publish_invalid_payload(self, as_user, staff):
        prop = make_published_property(status="pending_review")
        response = as_user(staff).post(
            url(prop, "publish"), {"verification_level": "gold"}, format="json"
        )
        assert response.status_code == 400

    def test_reject_sends_email(self, as_user, staff):
        prop = PropertyFactory(status="pending_review")
        response = as_user(staff).post(
            url(prop, "reject"), {"reason": "Adresse introuvable"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
        assert response.json()["rejection_reason"] == "Adresse introuvable"
        assert len(mail.outbox) == 1
        assert "Adresse introuvable" in mail.outbox[0].body

    def test_reject_published_is_conflict(self, as_user, staff):
        prop = make_published_property()
        assert (
            as_user(staff).post(url(prop, "reject"), {"reason": "x"}, format="json").status_code
            == 409
        )

    def test_team_photo_flagged(self, as_user, staff):
        prop = PropertyFactory(status="needs_visit")
        response = as_user(staff).post(
            url(prop, "upload-team-photo"), {"image": png_upload()}, format="multipart"
        )
        assert response.status_code == 201
        assert response.json()["taken_by_team"] is True
