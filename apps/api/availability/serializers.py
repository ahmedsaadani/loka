from __future__ import annotations

from typing import Any

from rest_framework import serializers

from availability.models import AvailabilityBlock, CalendarSource, ExternalCalendar


class AvailabilityBlockSerializer(serializers.ModelSerializer[AvailabilityBlock]):
    booking_public_id = serializers.UUIDField(
        source="booking.public_id", read_only=True, default=None
    )

    class Meta:
        model = AvailabilityBlock
        fields = ("id", "start", "end", "kind", "note", "booking_public_id", "external_uid")
        read_only_fields = fields


class BlockDatesSerializer(serializers.Serializer[Any]):
    start = serializers.DateField()
    end = serializers.DateField()
    note = serializers.CharField(max_length=160, required=False, default="", allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError(
                {"end": "La date de fin doit être après la date de début."}
            )
        return attrs


class ExternalCalendarSerializer(serializers.ModelSerializer[ExternalCalendar]):
    class Meta:
        model = ExternalCalendar
        fields = ("id", "ical_url", "source", "last_synced_at", "last_error", "created_at")
        read_only_fields = ("id", "last_synced_at", "last_error", "created_at")

    def validate_ical_url(self, value: str) -> str:
        if not value.lower().startswith("https://"):
            raise serializers.ValidationError("Seules les URLs HTTPS sont acceptées.")
        return value

    def validate_source(self, value: str) -> str:
        if value not in CalendarSource.values:
            raise serializers.ValidationError("Source inconnue.")
        return value
