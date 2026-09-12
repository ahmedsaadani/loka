from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import HostProfile, IdentityDocument, IdentityDocumentType, Role, User


class HostProfileSerializer(serializers.ModelSerializer[HostProfile]):
    class Meta:
        model = HostProfile
        fields = ("display_name", "bio", "company_name", "bank_details_masked")
        read_only_fields = ("bank_details_masked",)


class UserSerializer(serializers.ModelSerializer[User]):
    host_profile = HostProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "public_id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_identity_verified",
            "preferred_language",
            "host_profile",
            "created_at",
        )
        read_only_fields = ("public_id", "email", "role", "is_identity_verified", "created_at")


class UserUpdateSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "preferred_language")


class RegisterSerializer(serializers.Serializer[User]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)
    first_name = serializers.CharField(max_length=80, required=False, default="")
    last_name = serializers.CharField(max_length=80, required=False, default="")
    phone = serializers.CharField(max_length=24, required=False, default="")
    role = serializers.ChoiceField(choices=[Role.TRAVELER, Role.HOST], default=Role.TRAVELER)
    display_name = serializers.CharField(max_length=80, required=False, default="")

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        probe = User(
            email=attrs["email"], first_name=attrs["first_name"], last_name=attrs["last_name"]
        )
        validate_password(attrs["password"], user=probe)
        return attrs


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AccessTokenSerializer(serializers.Serializer[Any]):
    access = serializers.CharField()
    user = UserSerializer(read_only=True)


class IdentityDocumentSerializer(serializers.ModelSerializer[IdentityDocument]):
    """Jamais d'URL de fichier ici : l'accès passe par l'endpoint /download/ signé."""

    class Meta:
        model = IdentityDocument
        fields: tuple[str, ...] = (
            "public_id",
            "doc_type",
            "status",
            "rejection_reason",
            "created_at",
            "reviewed_at",
        )
        read_only_fields = fields


class IdentityDocumentUploadSerializer(serializers.Serializer[Any]):
    doc_type = serializers.ChoiceField(choices=IdentityDocumentType.choices)
    file = serializers.FileField()


class IdentityDocumentStaffSerializer(IdentityDocumentSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_public_id = serializers.UUIDField(source="user.public_id", read_only=True)

    class Meta(IdentityDocumentSerializer.Meta):
        fields = (*IdentityDocumentSerializer.Meta.fields, "user_email", "user_public_id")
        read_only_fields = fields


class RejectSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255)


class SignedUrlSerializer(serializers.Serializer[Any]):
    url = serializers.URLField()
    expires_in = serializers.IntegerField()
