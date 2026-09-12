import pytest
from django.core import mail
from django.core.files.storage import storages

from accounts.factories import TravelerFactory
from listings.factories import PropertyPhotoFactory
from notifications import emails
from notifications.tasks import generate_photo_variants, send_email

pytestmark = pytest.mark.django_db


class TestEmails:
    def test_send_email_task(self):
        send_email("a@b.tn", "Sujet", "texte", "<p>html</p>")
        assert len(mail.outbox) == 1
        assert mail.outbox[0].alternatives[0][1] == "text/html"

    def test_welcome_uses_template(self):
        user = TravelerFactory(first_name="Nour")
        emails.send_welcome(user)
        assert len(mail.outbox) == 1
        assert "Nour" in mail.outbox[0].body
        assert "http://localhost:3000" in mail.outbox[0].alternatives[0][0]


class TestPhotoVariants:
    def test_generates_all_variants_in_public_storage(self):
        photo = PropertyPhotoFactory(variants={})
        variants = generate_photo_variants(photo.pk)
        assert set(variants) == {"thumb", "card", "gallery", "og"}
        photo.refresh_from_db()
        assert photo.variants == variants
        public = storages["default"]
        assert public.exists(f"photos/{photo.property_id}/{photo.public_id}_card.webp")

    def test_missing_photo_is_noop(self):
        assert generate_photo_variants(999999) == {}
