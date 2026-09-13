from decimal import Decimal
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from core.models import StatusLog
from core.state import InvalidTransition
from listings import services
from listings.factories import (
    PricingPlanFactory,
    PropertyFactory,
    PropertyPhotoFactory,
    make_published_property,
    verify_host_identity,
)
from listings.models import Property, PropertyStatus

pytestmark = pytest.mark.django_db

S = PropertyStatus

ALL_TRANSITIONS = {
    (S.DRAFT, S.PENDING_REVIEW),
    (S.PENDING_REVIEW, S.NEEDS_VISIT),
    (S.PENDING_REVIEW, S.PUBLISHED),
    (S.PENDING_REVIEW, S.REJECTED),
    (S.PENDING_REVIEW, S.DRAFT),
    (S.NEEDS_VISIT, S.PUBLISHED),
    (S.NEEDS_VISIT, S.REJECTED),
    (S.NEEDS_VISIT, S.PENDING_REVIEW),
    (S.PUBLISHED, S.PAUSED),
    (S.PUBLISHED, S.PENDING_REVIEW),
    (S.PAUSED, S.PUBLISHED),
    (S.PAUSED, S.DRAFT),
    (S.PAUSED, S.PENDING_REVIEW),
    (S.REJECTED, S.DRAFT),
}


def ready_property(**kwargs) -> Property:
    prop = PropertyFactory(**kwargs)
    prop.description = "x" * 100
    prop.save()
    verify_host_identity(prop.host)
    for i in range(3):
        PropertyPhotoFactory(property=prop, order=i + 1, is_cover=i == 0)
    PricingPlanFactory(property=prop)
    return prop


class TestTransitionTable:
    def test_declared_transitions_match_expected(self):
        declared = {(src, dst) for src, dsts in Property.TRANSITIONS.items() for dst in dsts}
        assert declared == ALL_TRANSITIONS

    @pytest.mark.parametrize("source", list(S.values))
    @pytest.mark.parametrize("target", list(S.values))
    def test_every_pair(self, source, target, staff):
        prop = ready_property(status=source)
        allowed = (source, target) in ALL_TRANSITIONS
        actions = {
            S.PENDING_REVIEW: lambda: (
                services.submit_for_review(prop, by=staff)
                if source == S.DRAFT
                else (
                    services.update_property(prop, by=staff, data={"title": "Titre modifié ok"})
                    if source in {S.PUBLISHED, S.PAUSED}
                    else services.back_to_review(prop, by=staff)
                )
            ),
            S.NEEDS_VISIT: lambda: services.schedule_visit(prop, by=staff, visit_at=timezone.now()),
            S.PUBLISHED: lambda: (
                services.publish(
                    prop, by=staff, verification_level="verified", condition_grade="good"
                )
                if source != S.PAUSED
                else services.resume(prop, by=staff)
            ),
            S.REJECTED: lambda: services.reject(prop, by=staff, reason="non conforme"),
            S.DRAFT: lambda: services.withdraw_to_draft(prop, by=staff),
            S.PAUSED: lambda: services.pause(prop, by=staff),
        }
        if allowed:
            actions[target]()
            prop.refresh_from_db()
            assert prop.status == target
            assert StatusLog.objects.filter(to_status=target).exists()
        else:
            with pytest.raises(InvalidTransition):
                actions[target]()
            prop.refresh_from_db()
            assert prop.status == source


class TestSubmitAndPublish:
    def test_submit_requires_completeness(self, host):
        prop = PropertyFactory(host=host, description="court")
        with pytest.raises(ValidationError) as exc:
            services.submit_for_review(prop, by=host)
        errors = exc.value.message_dict
        assert set(errors) >= {"description", "photos", "pricing_plans"}
        prop.refresh_from_db()
        assert prop.status == S.DRAFT

    def test_submit_ok(self, host):
        prop = ready_property(host=host)
        services.submit_for_review(prop, by=host)
        assert prop.status == S.PENDING_REVIEW

    def test_publish_sets_verification_fields(self, staff):
        prop = ready_property(status=S.PENDING_REVIEW)
        services.publish(
            prop, by=staff, verification_level="selection", condition_grade="excellent", notes="RAS"
        )
        prop.refresh_from_db()
        assert prop.verified_by == staff
        assert prop.verified_at is not None
        assert prop.published_at is not None
        assert prop.verification_level == "selection"
        assert prop.condition_grade == "excellent"
        assert prop.verification_notes == "RAS"

    def test_publish_keeps_first_published_at(self, staff):
        prop = ready_property(status=S.PAUSED)
        first = timezone.now() - timezone.timedelta(days=10)
        prop.published_at = first
        prop.save()
        services.resume(prop, by=staff)
        prop.refresh_from_db()
        assert prop.published_at == first

    def test_reject_stores_reason(self, staff):
        prop = ready_property(status=S.NEEDS_VISIT)
        services.reject(prop, by=staff, reason="Photos non conformes")
        prop.refresh_from_db()
        assert prop.rejection_reason == "Photos non conformes"

    def test_slug_is_unique_and_generated(self):
        a = PropertyFactory(title="Studio lumineux")
        b = PropertyFactory(title="Studio lumineux", city=a.city)
        assert a.slug != b.slug
        assert a.slug.startswith("studio-lumineux")


class TestPhotos:
    def upload(self):
        buffer = BytesIO()
        Image.new("RGB", (800, 600), "#abcdef").save(buffer, format="PNG")
        return SimpleUploadedFile("Mon Salon.PNG", buffer.getvalue(), content_type="image/png")

    def test_add_photo_reencodes_and_sets_cover(self):
        prop = PropertyFactory()
        photo = services.add_photo(prop, upload=self.upload(), alt_text="Salon")
        assert photo.is_cover is True
        assert photo.order == 1
        assert (photo.width, photo.height) == (800, 600)
        assert photo.original.name.endswith(".jpg")
        assert "Mon Salon" not in photo.original.name
        # Celery en mode eager : variantes générées
        photo.refresh_from_db()
        assert set(photo.variants) == {"thumb", "card", "gallery", "og"}

    def test_second_photo_not_cover(self):
        prop = PropertyFactory()
        services.add_photo(prop, upload=self.upload())
        second = services.add_photo(prop, upload=self.upload())
        assert second.is_cover is False
        assert second.order == 2

    def test_reorder(self):
        prop = make_published_property()
        photos = list(prop.photos.order_by("order"))
        services.reorder_photos(
            prop, [str(photos[2].public_id), str(photos[0].public_id), str(photos[1].public_id)]
        )
        reordered = list(prop.photos.order_by("order"))
        assert reordered[0].pk == photos[2].pk
        assert reordered[0].is_cover and not reordered[1].is_cover

    def test_reorder_requires_all_photos(self):
        prop = make_published_property()
        with pytest.raises(ValidationError):
            services.reorder_photos(prop, [str(prop.photos.first().public_id)])

    def test_delete_cover_promotes_next(self):
        prop = make_published_property()
        cover = prop.photos.get(is_cover=True)
        services.delete_photo(cover)
        assert prop.photos.filter(is_cover=True).count() == 1


class TestPricing:
    def test_upsert_creates_then_updates(self):
        prop = PropertyFactory()
        services.upsert_pricing_plan(prop, rental_mode="monthly", price=Decimal("900"))
        services.upsert_pricing_plan(
            prop, rental_mode="monthly", price=Decimal("950"), min_duration=3
        )
        plan = prop.pricing_plans.get()
        assert plan.price == Decimal("950")
        assert plan.min_duration == 3

    def test_max_below_min_rejected(self):
        prop = PropertyFactory()
        with pytest.raises(ValidationError):
            services.upsert_pricing_plan(
                prop, rental_mode="nightly", price=Decimal("100"), min_duration=5, max_duration=2
            )
