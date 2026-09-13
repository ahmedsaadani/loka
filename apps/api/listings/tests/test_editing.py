"""ADR 0007 : modification d'un bien publié, instantané public, identité requise."""

from io import BytesIO

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from accounts.factories import IdentityDocumentFactory
from accounts.models import IdentityDocumentStatus
from core.models import StatusLog
from listings import services
from listings.factories import PropertyFactory, PropertyPhotoFactory, make_published_property
from listings.models import Property, PropertyStatus

pytestmark = pytest.mark.django_db


def png_upload() -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (640, 480), "#334455").save(buffer, format="PNG")
    return SimpleUploadedFile("photo.png", buffer.getvalue(), content_type="image/png")


class TestIdentityRequired:
    def test_submit_blocked_without_approved_document(self, host):
        prop = make_published_property(host=host, status="draft")
        host.identity_documents.all().delete()
        host.is_identity_verified = False
        host.save()
        with pytest.raises(services.PropertyNotReady) as exc:
            services.submit_for_review(prop, by=host)
        assert "identity" in exc.value.message_dict
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.DRAFT

    def test_pending_document_is_not_enough(self, host):
        prop = make_published_property(host=host, status="draft")
        host.identity_documents.all().delete()
        host.is_identity_verified = False
        host.save()
        IdentityDocumentFactory(user=host, status=IdentityDocumentStatus.PENDING)
        assert "identity" in services.readiness_errors(prop)

    def test_api_submit_returns_clear_error(self, as_user, host):
        prop = make_published_property(host=host, status="draft")
        host.identity_documents.all().delete()
        host.is_identity_verified = False
        host.save()
        url = reverse("v1:host-property-submit", kwargs={"public_id": prop.public_id})
        response = as_user(host).post(url)
        assert response.status_code == 400
        assert "identity" in response.json()["errors"]

    def test_approved_document_unblocks(self, host):
        prop = make_published_property(host=host, status="draft")
        services.submit_for_review(prop, by=host)
        assert prop.status == PropertyStatus.PENDING_REVIEW


class TestUpdatePublishedProperty:
    def test_review_field_sends_to_review_with_snapshot(self, host):
        prop = make_published_property(host=host)
        prop.published_snapshot = services.build_published_snapshot(prop)
        prop.save()
        old_title = prop.title
        services.update_property(prop, by=host, data={"title": "Titre entièrement nouveau"})
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PENDING_REVIEW
        assert prop.title == "Titre entièrement nouveau"
        assert prop.is_serving_snapshot
        assert prop.published_snapshot["detail"]["title"] == old_title
        log = StatusLog.objects.filter(to_status="pending_review").latest("created_at")
        assert "title" in log.note
        assert len(mail.outbox) == 1
        assert "vérification" in mail.outbox[0].subject

    @pytest.mark.parametrize(
        "data",
        [
            {"house_rules": {"pets": True}},
            {"charges_included": True},
            {"deposit_months": 2},
            {"min_lease_months": 3},
        ],
    )
    def test_live_fields_stay_published(self, host, data):
        prop = make_published_property(host=host)
        services.update_property(prop, by=host, data=data)
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PUBLISHED
        assert len(mail.outbox) == 0

    def test_unchanged_review_field_does_not_trigger_review(self, host):
        prop = make_published_property(host=host)
        services.update_property(prop, by=host, data={"title": prop.title})
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PUBLISHED

    def test_paused_property_goes_to_review_too(self, host):
        prop = make_published_property(host=host, status="paused")
        services.update_property(prop, by=host, data={"description": "d" * 120})
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PENDING_REVIEW

    def test_draft_edit_stays_draft(self, host):
        prop = PropertyFactory(host=host)
        services.update_property(prop, by=host, data={"title": "Un titre de brouillon"})
        assert prop.status == PropertyStatus.DRAFT

    def test_photo_upload_and_delete_trigger_review(self, host):
        prop = make_published_property(host=host)
        photo = services.add_photo(prop, upload=png_upload(), by=host)
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PENDING_REVIEW
        # Une deuxième modification pendant la revue ne relance rien (déjà en revue).
        services.delete_photo(photo, by=host)
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PENDING_REVIEW
        assert len(mail.outbox) == 1

    def test_team_photo_does_not_trigger_review(self, staff):
        prop = make_published_property()
        services.add_photo(prop, upload=png_upload(), taken_by_team=True, by=staff)
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PUBLISHED

    def test_reorder_photos_stays_published(self, host):
        prop = make_published_property(host=host)
        ids = [str(p.public_id) for p in prop.photos.order_by("-order")]
        services.reorder_photos(prop, ids)
        prop.refresh_from_db()
        assert prop.status == PropertyStatus.PUBLISHED


class TestSnapshotVisibility:
    def in_review(self, **kwargs) -> Property:
        prop = make_published_property(**kwargs)
        prop.published_snapshot = services.build_published_snapshot(prop)
        prop.save()
        services.update_property(prop, by=prop.host, data={"title": "Nouveau titre en revue"})
        prop.refresh_from_db()
        return prop

    def test_public_list_and_detail_serve_old_version(self, api):
        prop = self.in_review()
        old_title = prop.published_snapshot["detail"]["title"]
        listing = api.get(reverse("v1:property-list")).json()
        assert [r["title"] for r in listing["results"]] == [old_title]
        detail = api.get(reverse("v1:property-detail", kwargs={"slug": prop.slug})).json()
        assert detail["title"] == old_title
        assert detail["description"] == prop.published_snapshot["detail"]["description"]

    def test_booking_request_allowed_during_review(self, api, traveler):
        from datetime import date, timedelta

        prop = self.in_review()
        start = (date.today() + timedelta(days=20)).replace(day=10)
        if start <= date.today():
            start = date(start.year + start.month // 12, start.month % 12 + 1, 10)
        end = date(start.year + start.month // 12, start.month % 12 + 1, 10)
        api.force_authenticate(traveler)
        response = api.post(
            reverse("v1:request-list"),
            {
                "property": prop.slug,
                "rental_mode": "monthly",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "guests": 1,
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_publish_refreshes_snapshot_and_reject_hides(self, api, staff):
        prop = self.in_review()
        services.publish(prop, by=staff, verification_level="verified", condition_grade="good")
        prop.refresh_from_db()
        assert prop.published_snapshot["detail"]["title"] == "Nouveau titre en revue"
        detail = api.get(reverse("v1:property-detail", kwargs={"slug": prop.slug})).json()
        assert detail["title"] == "Nouveau titre en revue"

        services.update_property(prop, by=prop.host, data={"title": "Encore une autre version"})
        services.reject(prop, by=staff, reason="Photos non conformes")
        prop.refresh_from_db()
        assert prop.published_snapshot is None
        assert api.get(reverse("v1:property-detail", kwargs={"slug": prop.slug})).status_code == 404

    def test_pending_without_snapshot_is_hidden(self, api):
        prop = make_published_property(status="pending_review")
        assert api.get(reverse("v1:property-detail", kwargs={"slug": prop.slug})).status_code == 404

    def test_withdraw_to_draft_clears_snapshot(self):
        prop = self.in_review()
        services.withdraw_to_draft(prop, by=prop.host)
        prop.refresh_from_db()
        assert prop.published_snapshot is None
        assert not prop.is_publicly_visible

    def test_host_serializer_exposes_flags(self, as_user):
        prop = self.in_review()
        body = (
            as_user(prop.host)
            .get(reverse("v1:host-property-detail", kwargs={"public_id": prop.public_id}))
            .json()
        )
        assert body["is_serving_snapshot"] is True
        assert body["is_publicly_visible"] is True
        assert body["status"] == "pending_review"

    def test_photo_factory_snapshot_keeps_photos(self):
        prop = make_published_property()
        PropertyPhotoFactory(property=prop, order=9)
        snapshot = services.build_published_snapshot(prop)
        assert len(snapshot["detail"]["photos"]) == 4
        assert snapshot["card"]["cover_photo"]["is_cover"] is True
