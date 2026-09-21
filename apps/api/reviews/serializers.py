from __future__ import annotations

from typing import Any

from rest_framework import serializers

from reviews.models import Review


def _author_label(author: Any) -> str:
    """Prénom + initiale du nom (respect de la vie privée), ex. « Nour B. »."""
    first = (author.first_name or "").strip()
    last = (author.last_name or "").strip()
    if not first:
        return "Voyageur Loka"
    return f"{first} {last[0]}." if last else first


class ReviewSerializer(serializers.ModelSerializer[Review]):
    """Avis publié, tel qu'affiché sur la fiche d'un bien."""

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields: tuple[str, ...] = ("public_id", "rating", "comment", "author_name", "created_at")
        read_only_fields = fields

    def get_author_name(self, obj: Review) -> str:
        return _author_label(obj.author)


class ReviewCreateSerializer(serializers.Serializer[dict[str, Any]]):
    booking = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")


class ReviewableBookingSerializer(serializers.Serializer[Any]):
    """Réservation terminée en attente d'avis (côté voyageur)."""

    booking = serializers.UUIDField(source="public_id")
    property_title = serializers.CharField(source="property.title")
    property_slug = serializers.CharField(source="property.slug")
    city = serializers.CharField(source="property.city.name")
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class MyReviewSerializer(ReviewSerializer):
    """Avis rédigé par le voyageur, avec le bien concerné."""

    property_title = serializers.CharField(source="booking.property.title", read_only=True)
    property_slug = serializers.CharField(source="booking.property.slug", read_only=True)

    class Meta(ReviewSerializer.Meta):
        fields = (*ReviewSerializer.Meta.fields, "property_title", "property_slug")
        read_only_fields = fields


class StaffReviewSerializer(serializers.ModelSerializer[Review]):
    """Avis vu par l'équipe : nom complet de l'auteur + statut de publication."""

    author_name = serializers.SerializerMethodField()
    author_email = serializers.EmailField(source="author.email", read_only=True)
    property_title = serializers.CharField(source="booking.property.title", read_only=True)
    property_slug = serializers.CharField(source="booking.property.slug", read_only=True)

    class Meta:
        model = Review
        fields = (
            "public_id",
            "rating",
            "comment",
            "author_name",
            "author_email",
            "property_title",
            "property_slug",
            "is_published",
            "created_at",
        )
        read_only_fields = fields

    def get_author_name(self, obj: Review) -> str:
        full = f"{obj.author.first_name} {obj.author.last_name}".strip()
        return full or obj.author.email


class SetVisibilitySerializer(serializers.Serializer[dict[str, Any]]):
    is_published = serializers.BooleanField()
