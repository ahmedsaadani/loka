from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.gis.geos import Point
from rest_framework import serializers

from bookings.pricing import to_eur
from geo.models import City, Neighborhood
from listings import services
from listings.models import (
    Amenity,
    ConditionGrade,
    LocationPrecision,
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyType,
    RentalMode,
    VerificationLevel,
)

# ----------------------------------------------------------------- briques


class LatLngField(serializers.Field[Point | None, dict[str, float], dict[str, float] | None, Any]):
    """{lat, lng} <-> Point. `approximate=True` arrondit à ~100 m pour le public."""

    def __init__(self, *, approximate: bool = False, **kwargs: Any) -> None:
        self.approximate = approximate
        super().__init__(**kwargs)

    def to_representation(self, value: Point | None) -> dict[str, float] | None:
        if value is None:
            return None
        lat, lng = float(value.y), float(value.x)
        if self.approximate:
            lat, lng = round(lat, 3), round(lng, 3)
        return {"lat": lat, "lng": lng}

    def to_internal_value(self, data: dict[str, float]) -> Point:
        try:
            lat, lng = float(data["lat"]), float(data["lng"])
        except (KeyError, TypeError, ValueError) as exc:
            raise serializers.ValidationError("Format attendu : {lat, lng}.") from exc
        if not (30.0 <= lat <= 38.0 and 7.0 <= lng <= 12.0):
            raise serializers.ValidationError("Coordonnées hors de la Tunisie.")
        return Point(lng, lat, srid=4326)


def public_location(prop: Property) -> dict[str, float] | None:
    """Position publique : arrondie à ~100 m sauf si l'hôte a choisi la précision exacte."""
    if prop.location is None:
        return None
    approximate = prop.location_precision == LocationPrecision.APPROXIMATE
    return LatLngField(approximate=approximate).to_representation(prop.location)


class PhotoSerializer(serializers.ModelSerializer[PropertyPhoto]):
    class Meta:
        model = PropertyPhoto
        fields = (
            "public_id",
            "variants",
            "width",
            "height",
            "alt_text",
            "is_cover",
            "taken_by_team",
            "order",
        )
        read_only_fields = fields


class PricingPlanSerializer(serializers.ModelSerializer[PricingPlan]):
    price_eur = serializers.SerializerMethodField()

    class Meta:
        model = PricingPlan
        fields = ("rental_mode", "price", "price_eur", "min_duration", "max_duration", "is_active")
        read_only_fields = fields

    def get_price_eur(self, obj: PricingPlan) -> Decimal:
        return to_eur(obj.price)


class PricingPlanWriteSerializer(serializers.Serializer[Any]):
    rental_mode = serializers.ChoiceField(choices=RentalMode.choices)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    min_duration = serializers.IntegerField(min_value=1, default=1)
    max_duration = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    is_active = serializers.BooleanField(default=True)


class AmenitySerializer(serializers.ModelSerializer[Amenity]):
    class Meta:
        model = Amenity
        fields = ("code", "name", "icon", "category")


class CityRefSerializer(serializers.ModelSerializer[City]):
    class Meta:
        model = City
        fields = ("name", "slug")


class NeighborhoodRefSerializer(serializers.ModelSerializer[Neighborhood]):
    class Meta:
        model = Neighborhood
        fields = ("name", "slug")


class HostPublicSerializer(serializers.Serializer[Any]):
    display_name = serializers.CharField()
    is_identity_verified = serializers.BooleanField()
    member_since = serializers.DateTimeField()


# ----------------------------------------------------------------- public


class PropertyCardSerializer(serializers.ModelSerializer[Property]):
    city = CityRefSerializer(read_only=True)
    neighborhood = NeighborhoodRefSerializer(read_only=True)
    cover_photo = serializers.SerializerMethodField()
    pricing_plans = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields: tuple[str, ...] = (
            "public_id",
            "slug",
            "title",
            "property_type",
            "rooms_label",
            "bedrooms",
            "bathrooms",
            "surface_m2",
            "furnished",
            "max_guests",
            "city",
            "neighborhood",
            "location",
            "location_precision",
            "cover_photo",
            "pricing_plans",
            "verification_level",
            "condition_grade",
            "verified_at",
            "distance_notes",
        )
        read_only_fields = fields

    def get_location(self, obj: Property) -> dict[str, float] | None:
        return public_location(obj)

    def get_cover_photo(self, obj: Property) -> dict[str, Any] | None:
        photos = list(obj.photos.all())
        cover = next((p for p in photos if p.is_cover and p.is_ready), None) or next(
            (p for p in photos if p.is_ready), None
        )
        return PhotoSerializer(cover).data if cover else None

    def get_pricing_plans(self, obj: Property) -> list[Any]:
        plans = [p for p in obj.pricing_plans.all() if p.is_active]
        return list(PricingPlanSerializer(plans, many=True).data)


class PropertyDetailSerializer(PropertyCardSerializer):
    photos = serializers.SerializerMethodField()
    amenities = AmenitySerializer(many=True, read_only=True)
    host = serializers.SerializerMethodField()

    class Meta(PropertyCardSerializer.Meta):
        fields = (
            *PropertyCardSerializer.Meta.fields,
            "description",
            "floor",
            "has_elevator",
            "photos",
            "amenities",
            "charges_included",
            "monthly_charges_estimate",
            "deposit_months",
            "min_lease_months",
            "house_rules",
            "meta_title",
            "meta_description",
            "published_at",
            "host",
        )
        read_only_fields = fields

    def get_photos(self, obj: Property) -> list[Any]:
        return list(PhotoSerializer([p for p in obj.photos.all() if p.is_ready], many=True).data)

    def get_host(self, obj: Property) -> dict[str, Any]:
        profile = getattr(obj.host, "host_profile", None)
        return {
            "display_name": profile.display_name if profile else obj.host.first_name or "Hôte Loka",
            "is_identity_verified": obj.host.is_identity_verified,
            "member_since": obj.host.created_at,
        }


class UnavailableRangeSerializer(serializers.Serializer[Any]):
    start = serializers.DateField()
    end = serializers.DateField()


class QuoteQuerySerializer(serializers.Serializer[Any]):
    rental_mode = serializers.ChoiceField(choices=RentalMode.choices)
    start = serializers.DateField()
    end = serializers.DateField()


class QuoteSerializer(serializers.Serializer[Any]):
    rental_mode = serializers.CharField()
    units = serializers.IntegerField()
    unit_label = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    fee_rate = serializers.DecimalField(max_digits=4, decimal_places=2)
    fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    fee_payer = serializers.CharField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    deposit = serializers.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_eur = serializers.SerializerMethodField()

    def get_total_eur(self, obj: Any) -> Decimal:
        return to_eur(obj.total)


# ----------------------------------------------------------------- hôte


class PropertyHostSerializer(serializers.ModelSerializer[Property]):
    """Vue complète pour le propriétaire du bien (adresse exacte incluse : c'est la sienne)."""

    city = CityRefSerializer(read_only=True)
    neighborhood = NeighborhoodRefSerializer(read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    pricing_plans = PricingPlanSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    location = LatLngField(read_only=True)
    readiness_errors = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields: tuple[str, ...] = (
            "public_id",
            "slug",
            "title",
            "description",
            "property_type",
            "rooms_label",
            "bedrooms",
            "bathrooms",
            "surface_m2",
            "floor",
            "has_elevator",
            "furnished",
            "max_guests",
            "city",
            "neighborhood",
            "address_private",
            "location",
            "location_precision",
            "status",
            "rejection_reason",
            "visit_scheduled_at",
            "verification_level",
            "condition_grade",
            "verified_at",
            "charges_included",
            "monthly_charges_estimate",
            "deposit_months",
            "min_lease_months",
            "distance_notes",
            "house_rules",
            "meta_title",
            "meta_description",
            "photos",
            "pricing_plans",
            "amenities",
            "readiness_errors",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_readiness_errors(self, obj: Property) -> dict[str, str]:
        return services.readiness_errors(obj)


class PropertyWriteSerializer(serializers.ModelSerializer[Property]):
    city = serializers.SlugRelatedField(slug_field="slug", queryset=City.objects.all())
    neighborhood = serializers.SlugRelatedField(
        slug_field="slug", queryset=Neighborhood.objects.all(), required=False, allow_null=True
    )
    location = LatLngField(required=False, allow_null=True)
    amenities = serializers.SlugRelatedField(
        slug_field="code", queryset=Amenity.objects.all(), many=True, required=False
    )
    property_type = serializers.ChoiceField(choices=PropertyType.choices)

    class Meta:
        model = Property
        fields = (
            "title",
            "description",
            "property_type",
            "rooms_label",
            "bedrooms",
            "bathrooms",
            "surface_m2",
            "floor",
            "has_elevator",
            "furnished",
            "max_guests",
            "city",
            "neighborhood",
            "address_private",
            "location",
            "location_precision",
            "charges_included",
            "monthly_charges_estimate",
            "deposit_months",
            "min_lease_months",
            "distance_notes",
            "house_rules",
            "amenities",
        )
        extra_kwargs = {
            "title": {"min_length": 3, "max_length": 140},
            "max_guests": {"min_value": 1, "max_value": 20},
            "bedrooms": {"max_value": 20},
            "bathrooms": {"min_value": 1, "max_value": 10},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        neighborhood = attrs.get("neighborhood")
        current = self.instance if isinstance(self.instance, Property) else None
        city = attrs.get("city") or (current.city if current else None)
        if neighborhood is not None and city is not None and neighborhood.city_id != city.pk:
            raise serializers.ValidationError(
                {"neighborhood": "Ce quartier n'est pas dans cette ville."}
            )
        for key in ("distance_notes", "house_rules"):
            value = attrs.get(key)
            if value is not None and not isinstance(value, dict):
                raise serializers.ValidationError({key: "Objet JSON attendu."})
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Property:
        amenities = validated_data.pop("amenities", [])
        prop = Property.objects.create(**validated_data)
        prop.amenities.set(amenities)
        return prop

    def update(self, instance: Property, validated_data: dict[str, Any]) -> Property:
        amenities = validated_data.pop("amenities", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if amenities is not None:
            instance.amenities.set(amenities)
        return instance


class PhotoUploadSerializer(serializers.Serializer[Any]):
    image = serializers.ImageField()
    alt_text = serializers.CharField(max_length=160, required=False, default="")


class PhotoReorderSerializer(serializers.Serializer[Any]):
    order = serializers.ListField(child=serializers.UUIDField(), min_length=1)


# ----------------------------------------------------------------- équipe


class PropertyStaffSerializer(PropertyHostSerializer):
    host_email = serializers.EmailField(source="host.email", read_only=True)
    host_public_id = serializers.UUIDField(source="host.public_id", read_only=True)
    host_identity_verified = serializers.BooleanField(
        source="host.is_identity_verified", read_only=True
    )

    class Meta(PropertyHostSerializer.Meta):
        fields = (
            *PropertyHostSerializer.Meta.fields,
            "host_email",
            "host_public_id",
            "host_identity_verified",
            "verification_notes",
        )
        read_only_fields = fields


class PublishSerializer(serializers.Serializer[Any]):
    verification_level = serializers.ChoiceField(choices=VerificationLevel.choices)
    condition_grade = serializers.ChoiceField(choices=ConditionGrade.choices)
    notes = serializers.CharField(required=False, default="", allow_blank=True, max_length=2000)


class ScheduleVisitSerializer(serializers.Serializer[Any]):
    visit_at = serializers.DateTimeField()
    note = serializers.CharField(required=False, default="", allow_blank=True, max_length=500)


class ReasonSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255)


class NoteSerializer(serializers.Serializer[Any]):
    note = serializers.CharField(required=False, default="", allow_blank=True, max_length=500)
