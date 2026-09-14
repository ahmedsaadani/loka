from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from PIL import Image, ImageStat

from core.imaging import enhance_photo
from listings.factories import PropertyPhotoFactory
from notifications.tasks import generate_photo_variants

pytestmark = pytest.mark.django_db


def _dull_photo(size: tuple[int, int] = (640, 480)) -> Image.Image:
    """Photo plate et jaunâtre : bruit déterministe resserré entre 80 et 180, dominante chaude."""
    import random

    rng = random.Random(7)  # nosec B311 - données de test
    pixels = []
    for _ in range(size[0] * size[1]):
        base = rng.randint(80, 180)
        pixels.append((min(255, round(base * 1.15)), base, round(base * 0.8)))
    image = Image.new("RGB", size)
    image.putdata(pixels)
    return image


def _colour_cast(image: Image.Image) -> float:
    """Dominante relative : écart entre canaux rapporté à la luminance moyenne."""
    means = ImageStat.Stat(image).mean[:3]
    return (max(means) - min(means)) / (sum(means) / 3)


class TestEnhancePhoto:
    def test_returns_new_rgb_image_same_size(self):
        source = _dull_photo()
        before = source.tobytes()
        out = enhance_photo(source)
        assert out is not source
        assert out.mode == "RGB"
        assert out.size == source.size
        assert source.tobytes() == before  # l'entrée n'est pas modifiée

    def test_stretches_levels_and_reduces_colour_cast(self):
        source = _dull_photo()
        out = enhance_photo(source)
        src_low, src_high = source.convert("L").getextrema()
        out_low, out_high = out.convert("L").getextrema()
        # Auto-niveaux : la plage de luminance s'élargit, sans dépasser la pente plafonnée.
        assert out_high - out_low > src_high - src_low
        assert (out_high - out_low) <= 1.8 * (src_high - src_low) + 4
        # Balance des blancs : la dominante jaune est atténuée, pas inversée.
        assert _colour_cast(out) < _colour_cast(source)
        r, g, b = ImageStat.Stat(out).mean[:3]
        assert r >= g >= b

    def test_grayscale_input_is_converted(self):
        out = enhance_photo(Image.new("L", (32, 32), 128))
        assert out.mode == "RGB"


class TestVariantsRespectFlag:
    def _photo(self, auto_enhance: bool):
        buffer = BytesIO()
        _dull_photo().save(buffer, format="JPEG", quality=90)
        photo = PropertyPhotoFactory(variants={}, auto_enhance=auto_enhance)
        photo.original.save("dull.jpg", ContentFile(buffer.getvalue()), save=True)
        return photo

    def _mean(self, photo, name: str) -> list[float]:
        from django.core.files.storage import storages

        key = f"photos/{photo.property_id}/{photo.public_id}_{name}.webp"
        with storages["default"].open(key, "rb") as fh, Image.open(fh) as img:
            return ImageStat.Stat(img.convert("RGB")).mean

    def test_enhanced_variant_differs_from_raw_variant(self):
        raw = self._photo(auto_enhance=False)
        enhanced = self._photo(auto_enhance=True)
        generate_photo_variants(raw.pk)
        generate_photo_variants(enhanced.pk)
        raw_mean = self._mean(raw, "card")
        enhanced_mean = self._mean(enhanced, "card")
        assert raw_mean != enhanced_mean

        def cast(means: list[float]) -> float:
            return (max(means) - min(means)) / (sum(means) / 3)

        assert cast(enhanced_mean) < cast(raw_mean)
        assert enhanced_mean[0] >= enhanced_mean[1] >= enhanced_mean[2]

    def test_original_is_never_rewritten(self):
        photo = self._photo(auto_enhance=True)
        with photo.original.open("rb") as fh:
            before = fh.read()
        generate_photo_variants(photo.pk)
        photo.refresh_from_db()
        with photo.original.open("rb") as fh:
            assert fh.read() == before
