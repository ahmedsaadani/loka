from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from accounts.factories import MINIMAL_PDF
from core.uploads import validate_and_reencode_image, validate_document


def image_upload(
    fmt: str = "PNG", size: tuple[int, int] = (64, 48), name: str = "img.png"
) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "#123456").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class TestImageValidation:
    def test_png_is_reencoded_to_jpeg(self):
        content = validate_and_reencode_image(image_upload("PNG"))
        with Image.open(content) as img:
            assert img.format == "JPEG"
            assert img.size == (64, 48)

    def test_extension_does_not_matter_real_type_does(self):
        upload = SimpleUploadedFile(
            "notes.jpg", b"ceci n'est pas une image", content_type="image/jpeg"
        )
        with pytest.raises(ValidationError):
            validate_and_reencode_image(upload)

    def test_unsupported_format_rejected(self):
        with pytest.raises(ValidationError):
            validate_and_reencode_image(image_upload("BMP", name="img.bmp"))

    def test_too_large_rejected(self):
        with pytest.raises(ValidationError):
            validate_and_reencode_image(image_upload(), max_bytes=10)


class TestDocumentValidation:
    def test_pdf_detected(self):
        assert validate_document(SimpleUploadedFile("x.bin", MINIMAL_PDF)) == "application/pdf"

    def test_image_detected(self):
        assert validate_document(image_upload()) == "image/png"

    def test_executable_rejected(self):
        with pytest.raises(ValidationError):
            validate_document(SimpleUploadedFile("doc.pdf", b"MZ\x90\x00 fake exe"))
