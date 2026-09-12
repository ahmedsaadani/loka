"""
Validation stricte des uploads : type réel (pas l'extension), taille, ré-encodage des images.
"""

from __future__ import annotations

from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000  # anti "decompression bomb"

PDF_MAGIC = b"%PDF-"
_PIL_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def validate_and_reencode_image(
    upload: UploadedFile, *, max_bytes: int | None = None
) -> ContentFile:
    """
    Vérifie que le fichier est une vraie image JPEG/PNG/WEBP sous la taille max,
    puis la ré-encode en JPEG (métadonnées EXIF supprimées, orientation appliquée).
    """
    limit = max_bytes or settings.UPLOAD_MAX_IMAGE_BYTES
    if upload.size is None or upload.size > limit:
        raise ValidationError(
            {"image": f"Image trop volumineuse (max {limit // (1024 * 1024)} Mo)."}
        )
    image: Image.Image
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"image": "Fichier image illisible."}) from exc
    if image.format not in settings.UPLOAD_ALLOWED_IMAGE_FORMATS:
        raise ValidationError({"image": "Format accepté : JPEG, PNG ou WebP."})
    image = ImageOps.exif_transpose(image) or image
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    return ContentFile(buffer.getvalue())


def detect_document_mime(upload: UploadedFile) -> str:
    """Type MIME réel d'un document (PDF ou image), d'après les octets."""
    head = upload.read(16)
    upload.seek(0)
    if head.startswith(PDF_MAGIC):
        return "application/pdf"
    try:
        image = Image.open(upload)
        fmt = image.format or ""
    except (UnidentifiedImageError, OSError):
        return "application/octet-stream"
    finally:
        upload.seek(0)
    return _PIL_TO_MIME.get(fmt, "application/octet-stream")


def validate_document(upload: UploadedFile) -> str:
    """Retourne le MIME réel ou lève ValidationError."""
    if upload.size is None or upload.size > settings.UPLOAD_MAX_DOCUMENT_BYTES:
        raise ValidationError({"file": "Document trop volumineux (max 8 Mo)."})
    mime = detect_document_mime(upload)
    if mime not in settings.UPLOAD_ALLOWED_DOCUMENT_MIME:
        raise ValidationError({"file": "Format accepté : PDF, JPEG, PNG ou WebP."})
    return mime
