"""
Retouche automatique des photos prises par l'équipe (variantes publiques uniquement).

L'original du bucket privé n'est jamais modifié : la retouche s'applique en mémoire
au moment de générer les variantes WebP. Réglages volontairement doux, pensés pour
des intérieurs et des extérieurs photographiés au téléphone :

- redressement d'après l'orientation EXIF (appliqué en amont par `ImageOps.exif_transpose`) ;
- balance des blancs « gray world » atténuée (appliquée en premier) : les canaux sont
  ramenés à mi-chemin vers la moyenne, avec un gain borné pour préserver une ambiance chaude ;
- auto-niveaux sur la luminance (même courbe pour les trois canaux, donc sans dérive de
  teinte) : la plage 0,5 % – 99,5 % est étirée, avec une pente plafonnée pour qu'une photo
  très plate ne soit pas brutalisée ;
- contraste et netteté légèrement relevés.

Désactivable photo par photo (PropertyPhoto.auto_enhance, admin Django).
"""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageStat

LEVELS_CUTOFF = 0.005  # part des pixels ignorée à chaque extrémité de l'histogramme
LEVELS_MAX_SLOPE = 1.5  # étirement maximal (1 = aucun)
WHITE_BALANCE_STRENGTH = 0.5  # 0 = aucune correction, 1 = gray world complet
WHITE_BALANCE_MAX_GAIN = 1.12  # gain maximal par canal (et 1/max en minimal)
CONTRAST_FACTOR = 1.06
SHARPNESS_FACTOR = 1.08


def _percentile_bounds(histogram: list[int], cutoff: float) -> tuple[int, int]:
    total = sum(histogram)
    if total == 0:
        return 0, 255
    low_target = total * cutoff
    high_target = total * (1 - cutoff)
    cumulative = 0
    low, high = 0, 255
    for value, count in enumerate(histogram):
        cumulative += count
        if cumulative >= low_target:
            low = value
            break
    cumulative = 0
    for value, count in enumerate(histogram):
        cumulative += count
        if cumulative >= high_target:
            high = value
            break
    return low, max(high, low + 1)


def _auto_levels(image: Image.Image) -> Image.Image:
    """Étire la luminance entre ses percentiles, pente plafonnée, même LUT par canal."""
    low_i, high_i = _percentile_bounds(image.convert("L").histogram(), LEVELS_CUTOFF)
    low, high = float(low_i), float(high_i)
    slope = 255 / (high - low)
    if slope <= 1.0:
        return image
    if slope > LEVELS_MAX_SLOPE:
        # On recentre une plage plus large autour du milieu pour respecter la pente maximale.
        span = 255 / LEVELS_MAX_SLOPE
        middle = (low + high) / 2
        low = max(0.0, middle - span / 2)
        high = min(255.0, low + span)
        low = max(0.0, high - span)
        slope = 255 / (high - low)
    lut = [min(255, max(0, round((v - low) * slope))) for v in range(256)]
    return image.point(lut * 3)


def _white_balance(image: Image.Image) -> Image.Image:
    """Gray world atténué : chaque canal est ramené partiellement vers la luminance moyenne."""
    r_mean, g_mean, b_mean = ImageStat.Stat(image).mean[:3]
    if min(r_mean, g_mean, b_mean) <= 0:
        return image
    gray = (r_mean + g_mean + b_mean) / 3
    gains = []
    for mean in (r_mean, g_mean, b_mean):
        full = gray / mean
        gain = 1 + (full - 1) * WHITE_BALANCE_STRENGTH
        gains.append(min(max(gain, 1 / WHITE_BALANCE_MAX_GAIN), WHITE_BALANCE_MAX_GAIN))
    if all(abs(g - 1) < 0.005 for g in gains):
        return image
    channels = [
        channel.point(lambda v, g=g: min(255, round(v * g)))
        for channel, g in zip(image.split(), gains, strict=True)
    ]
    return Image.merge("RGB", channels)


def enhance_photo(image: Image.Image) -> Image.Image:
    """Retourne une nouvelle image RGB retouchée ; l'image d'entrée n'est pas modifiée."""
    rgb = image.convert("RGB") if image.mode != "RGB" else image.copy()
    # Balance des blancs avant les niveaux : l'étirement conserve ensuite les proportions.
    out = _white_balance(rgb)
    out = _auto_levels(out)
    out = ImageEnhance.Contrast(out).enhance(CONTRAST_FACTOR)
    out = ImageEnhance.Sharpness(out).enhance(SHARPNESS_FACTOR)
    return out
