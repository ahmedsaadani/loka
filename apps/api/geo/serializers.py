from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from rest_framework import serializers

from geo.models import City, Governorate, Neighborhood


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


class CityDetailSerializer(CitySummarySerializer):
    neighborhoods = NeighborhoodSummarySerializer(many=True, read_only=True)

    class Meta(CitySummarySerializer.Meta):
        fields = (
            *CitySummarySerializer.Meta.fields,
            "seo_title",
            "seo_description",
            "intro_text",
            "neighborhoods",
        )


class NeighborhoodDetailSerializer(NeighborhoodSummarySerializer):
    city = CitySummarySerializer(read_only=True)

    class Meta(NeighborhoodSummarySerializer.Meta):
        fields = (
            *NeighborhoodSummarySerializer.Meta.fields,
            "city",
            "seo_title",
            "seo_description",
            "intro_text",
        )
