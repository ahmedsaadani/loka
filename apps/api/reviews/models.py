"""Squelette des avis. Non exposé par l'API au MVP."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import PublicIdModel, TimeStampedModel


class Review(PublicIdModel, TimeStampedModel):
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="review"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, max_length=2000)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "avis"
        verbose_name_plural = "avis"

    def __str__(self) -> str:
        return f"{self.rating}/5 par {self.author_id}"
