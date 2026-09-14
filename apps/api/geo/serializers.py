from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.content import public_text
from geo.models import City, Governorate, Neighborhood


@extend_schema_field(
    {
        "type": "object",
        "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}},
        "required": ["lat", "lng"],
    }
)
class PointField(serializers.Field[Any, Any, Any, Any]):
    """Sérialise un Point PostGIS en {lat, lng}."""

    def to_representation(self, value: Point) -> dict[str, float]:
        return {"lat": float(value.y), "lng": float(value.x)}

    def to_internal_value(self, data: Any) -> Any:
        raise NotImplementedError("Lecture seule.")


class GovernorateSerializer(serializers.ModelSerializer[Governorate]):
    class Meta:
        model = Governorate
        fields = ("name", "slug")


class NeighborhoodSummarySerializer(serializers.ModelSerializer[Neighborhood]):
    centroid = PointField(read_only=True)
    property_count = serializers.IntegerField(read_only=True, default=0)
    avg_monthly_price = serializers.DecimalField(
        max_digits=10, decimal_places=0, read_only=True, allow_null=True, default=None
    )
    city_slug = serializers.SlugField(source="city.slug", read_only=True)

    class Meta:
        model = Neighborhood
        fields: tuple[str, ...] = (
            "name",
            "slug",
            "city_slug",
            "centroid",
            "property_count",
            "avg_monthly_price",
        )


class CitySummarySerializer(serializers.ModelSerializer[City]):
    centroid = PointField(read_only=True)
    governorate = GovernorateSerializer(read_only=True)
    property_count = serializers.IntegerField(read_only=True, default=0)
    avg_monthly_price = serializers.DecimalField(
        max_digits=10, decimal_places=0, read_only=True, allow_null=True, default=None
    )
    avg_nightly_price = serializers.DecimalField(
        max_digits=10, decimal_places=0, read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = City
        fields: tuple[str, ...] = (
            "name",
            "slug",
            "governorate",
            "centroid",
            "is_featured",
            "property_count",
            "avg_monthly_price",
            "avg_nightly_price",
        )


class EditorialTextsMixin(serializers.Serializer[Any]):
    """Textes éditoriaux : vides tant qu'ils sont marqués [À RÉDIGER] (le front masque)."""

    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()
    intro_text = serializers.SerializerMethodField()

    def get_seo_title(self, obj: Any) -> str:
        return public_text(obj.seo_title)

    def get_seo_description(self, obj: Any) -> str:
        return public_text(obj.seo_description)

    def get_intro_text(self, obj: Any) -> str:
        return public_text(obj.intro_text)


class CityDetailSerializer(EditorialTextsMixin, CitySummarySerializer):
    neighborhoods = NeighborhoodSummarySerializer(many=True, read_only=True)

    class Meta(CitySummarySerializer.Meta):
        fields = (
            *CitySummarySerializer.Meta.fields,
            "seo_title",
            "seo_description",
            "intro_text",
            "neighborhoods",
        )


class NeighborhoodDetailSerializer(EditorialTextsMixin, NeighborhoodSummarySerializer):
    city = CitySummarySerializer(read_only=True)

    class Meta(NeighborhoodSummarySerializer.Meta):
        fields = (
            *NeighborhoodSummarySerializer.Meta.fields,
            "city",
            "seo_title",
            "seo_description",
            "intro_text",
        )
