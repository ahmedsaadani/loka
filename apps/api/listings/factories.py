from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any, cast

import factory
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from accounts.factories import HostFactory
from geo.factories import CityFactory, NeighborhoodFactory
from listings.models import (
    Amenity,
    ConditionGrade,
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyStatus,
    PropertyType,
    RentalMode,
    VerificationLevel,
)


def make_image_bytes(
    width: int = 640, height: int = 480, color: str = "#c96f4a", fmt: str = "JPEG"
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format=fmt)
    return buffer.getvalue()


class AmenityFactory(factory.django.DjangoModelFactory[Amenity]):
    class Meta:
        model = Amenity
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"amenity-{n}")
    name = factory.Sequence(lambda n: f"Équipement {n}")
    icon = "check"


class PropertyFactory(factory.django.DjangoModelFactory[Property]):
    class Meta:
        model = Property

    host = factory.SubFactory(HostFactory)
    title = factory.Sequence(lambda n: f"Appartement lumineux S+2 numéro {n}")
    description = factory.Faker("paragraph", nb_sentences=6, locale="fr_FR")
    property_type = PropertyType.APARTMENT
    rooms_label = "S+2"
    bedrooms = 2
    bathrooms = 1
    surface_m2 = 85
    floor = 2
    has_elevator = True
    furnished = True
    city = factory.SubFactory(CityFactory)
    neighborhood = factory.SubFactory(NeighborhoodFactory, city=factory.SelfAttribute("..city"))
    address_private = "12 rue des Oliviers, résidence Yasmine, appt 4"
    location = factory.LazyFunction(lambda: Point(10.19, 36.87, srid=4326))
    max_guests = 4
    status = PropertyStatus.DRAFT
    condition_grade = ConditionGrade.GOOD
    verification_level = VerificationLevel.VERIFIED
    deposit_months = 1
    distance_notes = {"ESPRIT": "8 min à pied"}

    class Params:
        published = factory.Trait(
            status=PropertyStatus.PUBLISHED,
            published_at=factory.LazyFunction(timezone.now),
            verified_at=factory.LazyFunction(timezone.now),
        )


class PricingPlanFactory(factory.django.DjangoModelFactory[PricingPlan]):
    class Meta:
        model = PricingPlan
        django_get_or_create = ("property", "rental_mode")

    property = factory.SubFactory(PropertyFactory)
    rental_mode = RentalMode.MONTHLY
    price = Decimal("850.00")
    min_duration = 1
    max_duration = None
    is_active = True


class PropertyPhotoFactory(factory.django.DjangoModelFactory[PropertyPhoto]):
    class Meta:
        model = PropertyPhoto

    property = factory.SubFactory(PropertyFactory)
    original = factory.LazyFunction(lambda: ContentFile(make_image_bytes(), name="photo.jpg"))
    variants = factory.LazyAttribute(
        lambda o: {
            name: f"https://cdn.test/photos/{o.property.pk}/{name}.webp"
            for name in ("thumb", "card", "gallery", "og")
        }
    )
    width = 640
    height = 480
    order = factory.Sequence(lambda n: n + 1)
    is_cover = False
    alt_text = "Séjour lumineux"


def verify_host_identity(host: Any) -> None:
    """ADR 0007 : un hôte doit avoir une pièce d'identité approuvée pour publier."""
    from accounts.factories import IdentityDocumentFactory
    from accounts.models import IdentityDocumentStatus

    if not host.identity_documents.filter(status=IdentityDocumentStatus.APPROVED).exists():
        IdentityDocumentFactory(user=host, status=IdentityDocumentStatus.APPROVED)
        host.is_identity_verified = True
        host.save(update_fields=["is_identity_verified"])


def make_published_property(**kwargs: Any) -> Property:
    """Bien publié complet : 3 photos, plan mensuel + nuitée, hôte à l'identité vérifiée."""
    prop = cast(Property, PropertyFactory(published=True, **kwargs))
    verify_host_identity(prop.host)
    for index in range(3):
        PropertyPhotoFactory(property=prop, order=index + 1, is_cover=index == 0)
    PricingPlanFactory(property=prop, rental_mode=RentalMode.MONTHLY, price=Decimal("850.00"))
    PricingPlanFactory(
        property=prop, rental_mode=RentalMode.NIGHTLY, price=Decimal("120.00"), min_duration=2
    )
    return prop
