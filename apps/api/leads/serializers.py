from __future__ import annotations

from typing import Any

from rest_framework import serializers

from accounts.models import User
from geo.models import City
from leads.models import Lead, LeadStatus


class LeadSerializer(serializers.ModelSerializer[Lead]):
    assigned_to_email = serializers.EmailField(
        source="assigned_to.email", read_only=True, default=None
    )
    converted_property_public_id = serializers.UUIDField(
        source="converted_property.public_id", read_only=True, default=None
    )

    class Meta:
        model = Lead
        fields = (
            "public_id",
            "source",
            "source_url",
            "title",
            "price",
            "city",
            "phone",
            "raw_data",
            "status",
            "assigned_to_email",
            "notes",
            "converted_property_public_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "public_id",
            "status",
            "assigned_to_email",
            "converted_property_public_id",
            "created_at",
            "updated_at",
        )


class LeadWriteSerializer(serializers.ModelSerializer[Lead]):
    assigned_to = serializers.SlugRelatedField(
        slug_field="email",
        queryset=User.objects.filter(role__in=["staff", "admin"]),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Lead
        fields = (
            "source",
            "source_url",
            "title",
            "price",
            "city",
            "phone",
            "raw_data",
            "notes",
            "assigned_to",
        )


class LeadStatusSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=LeadStatus.choices)
    note = serializers.CharField(max_length=1000, required=False, default="", allow_blank=True)


class LeadConvertSerializer(serializers.Serializer[Any]):
    host_email = serializers.SlugRelatedField(
        slug_field="email", queryset=User.objects.filter(role="host")
    )
    city = serializers.SlugRelatedField(slug_field="slug", queryset=City.objects.all())


class LeadImportSerializer(serializers.Serializer[Any]):
    file = serializers.FileField()


class LeadImportResultSerializer(serializers.Serializer[Any]):
    created = serializers.IntegerField()
    skipped = serializers.IntegerField()


class OwnerContactSerializer(serializers.Serializer[dict[str, Any]]):
    """Formulaire public « Devenir hôte » : crée un lead manuel pour l'équipe."""

    PROPERTY_TYPES = (
        ("studio", "Studio"),
        ("apartment", "Appartement"),
        ("villa", "Villa"),
        ("room_in_shared_flat", "Chambre en colocation"),
        ("other", "Autre"),
    )

    name = serializers.CharField(max_length=120)
    phone = serializers.RegexField(
        r"^\+?[0-9][0-9 .-]{6,19}$",
        max_length=32,
        error_messages={"invalid": "Numéro de téléphone invalide."},
    )
    city = serializers.CharField(max_length=80)
    property_type = serializers.ChoiceField(choices=PROPERTY_TYPES)
    message = serializers.CharField(max_length=1500, required=False, allow_blank=True, default="")
    # Champ piège invisible côté front : rempli uniquement par les robots.
    website = serializers.CharField(required=False, allow_blank=True, default="")
