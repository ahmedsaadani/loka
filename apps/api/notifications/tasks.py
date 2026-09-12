from __future__ import annotations

import logging
from io import BytesIO

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from PIL import Image, ImageOps

from core.storages import public_storage

logger = logging.getLogger(__name__)


@shared_task(name="notifications.tasks.send_email", autoretry_for=(Exception,), max_retries=3)
def send_email(to: str, subject: str, text: str, html: str) -> None:
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    message.attach_alternative(html, "text/html")
    message.send()


@shared_task(
    name="notifications.tasks.generate_photo_variants",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
)
def generate_photo_variants(photo_id: int) -> dict[str, str]:
    """Génère les variantes WebP publiques depuis l'original privé."""
    from listings.models import PropertyPhoto

    try:
        photo = PropertyPhoto.objects.get(pk=photo_id)
    except PropertyPhoto.DoesNotExist:
        return {}
    storage = public_storage()
    variants: dict[str, str] = {}
    with photo.original.open("rb") as fh, Image.open(fh) as source:
        image = ImageOps.exif_transpose(source) or source
        if image.mode != "RGB":
            image = image.convert("RGB")
        for name, (width, height) in settings.PHOTO_VARIANTS.items():
            if name == "og":
                variant = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
            else:
                variant = image.copy()
                variant.thumbnail((width, height), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            variant.save(buffer, format="WEBP", quality=82, method=4)
            key = f"photos/{photo.property_id}/{photo.public_id}_{name}.webp"
            saved = storage.save(key, ContentFile(buffer.getvalue()))
            variants[name] = storage.url(saved)
    photo.variants = variants
    photo.save(update_fields=["variants", "updated_at"])
    return variants
