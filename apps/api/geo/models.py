from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models

from core.models import TimeStampedModel


class Governorate(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "gouvernorat"

    def __str__(self) -> str:
        return self.name


class SeoFieldsMixin(models.Model):
    seo_title = models.CharField(max_length=120, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    intro_text = models.TextField(blank=True, help_text="Texte d'introduction affiché sur la page")

    class Meta:
        abstract = True


class City(SeoFieldsMixin, TimeStampedModel):
    governorate = models.ForeignKey(Governorate, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    centroid = gis_models.PointField(srid=4326)
    is_featured = models.BooleanField(default=False, help_text="Affichée sur l'accueil")

    class Meta:
        ordering = ["name"]
        verbose_name = "ville"
        unique_together = [("governorate", "name")]

    def __str__(self) -> str:
        return self.name


class Neighborhood(SeoFieldsMixin, TimeStampedModel):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="neighborhoods")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    centroid = gis_models.PointField(srid=4326)
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "quartier"
        unique_together = [("city", "slug"), ("city", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.city.name})"
