from __future__ import annotations

from typing import Any

from rest_framework import serializers

from bookings.models import Booking, BookingRequest, Payment
from listings.models import Property, RentalMode
from listings.serializers import PhotoSerializer


class PropertyRefSerializer(serializers.ModelSerializer[Property]):
    cover_photo = serializers.SerializerMethodField()
    city = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Property
        fields = ("public_id", "slug", "title", "city", "cover_photo")

    def get_cover_photo(self, obj: Property) -> dict[str, Any] | None:
        cover = next((p for p in obj.photos.all() if p.is_cover), None)
        return PhotoSerializer(cover).data if cover else None


class PartySerializer(serializers.Serializer[Any]):
    public_id = serializers.UUIDField()
    display_name = serializers.SerializerMethodField()
    is_identity_verified = serializers.BooleanField()

    def get_display_name(self, obj: Any) -> str:
        profile = getattr(obj, "host_profile", None)
        return profile.display_name if profile else obj.full_name


class BookingRequestCreateSerializer(serializers.Serializer[Any]):
    property = serializers.SlugRelatedField(
        slug_field="slug", queryset=Property.objects.publicly_visible()
    )
    rental_mode = serializers.ChoiceField(choices=RentalMode.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    guests = serializers.IntegerField(min_value=1, max_value=20)
    message = serializers.CharField(max_length=2000, required=False, default="", allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["end_date"] <= attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit être après la date de début."}
            )
        return attrs


class BookingRequestSerializer(serializers.ModelSerializer[BookingRequest]):
    property = PropertyRefSerializer(read_only=True)
    traveler = PartySerializer(read_only=True)
    booking_public_id = serializers.UUIDField(
        source="booking.public_id", read_only=True, default=None
    )

    class Meta:
        model = BookingRequest
        fields = (
            "public_id",
            "property",
            "traveler",
            "rental_mode",
            "start_date",
            "end_date",
            "guests",
            "message",
            "status",
            "quoted_units",
            "quoted_unit_price",
            "quoted_subtotal",
            "quoted_fee",
            "quoted_total",
            "quoted_deposit",
            "expires_at",
            "decline_reason",
            "booking_public_id",
            "created_at",
        )
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer[Payment]):
    class Meta:
        model = Payment
        fields = (
            "public_id",
            "provider",
            "amount",
            "currency",
            "kind",
            "status",
            "checkout_url",
            "created_at",
        )
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer[Booking]):
    property = PropertyRefSerializer(read_only=True)
    traveler = PartySerializer(read_only=True)
    host = PartySerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    has_contract = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields: tuple[str, ...] = (
            "public_id",
            "property",
            "traveler",
            "host",
            "rental_mode",
            "start_date",
            "end_date",
            "total_amount",
            "deposit_amount",
            "platform_fee",
            "fee_payer",
            "status",
            "cancellation_reason",
            "payments",
            "has_contract",
            "created_at",
        )
        read_only_fields = fields

    def get_has_contract(self, obj: Booking) -> bool:
        return bool(obj.contract_pdf)


class BookingConfirmedSerializer(BookingSerializer):
    """Après confirmation, le voyageur obtient l'adresse exacte (accès journalisé côté vue)."""

    address_private = serializers.CharField(read_only=True, source="property.address_private")
    host_phone = serializers.CharField(read_only=True, source="host.phone")

    class Meta(BookingSerializer.Meta):
        fields = (*BookingSerializer.Meta.fields, "address_private", "host_phone")
        read_only_fields = fields


class DeclineSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)


class CancelSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)


class MockWebhookSerializer(serializers.Serializer[Any]):
    provider_ref = serializers.CharField(max_length=128)
    outcome = serializers.ChoiceField(choices=["succeeded", "failed"])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default="TND")
    signature = serializers.CharField(max_length=128)
