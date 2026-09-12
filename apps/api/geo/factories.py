from __future__ import annotations

import factory
from django.contrib.gis.geos import Point

from geo.models import City, Governorate, Neighborhood


class GovernorateFactory(factory.django.DjangoModelFactory[Governorate]):
    class Meta:
        model = Governorate
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Gouvernorat {n}")
    slug = factory.Sequence(lambda n: f"gouvernorat-{n}")


class CityFactory(factory.django.DjangoModelFactory[City]):
    class Meta:
        model = City
        django_get_or_create = ("slug",)

    governorate = factory.SubFactory(GovernorateFactory)
    name = factory.Sequence(lambda n: f"Ville {n}")
    slug = factory.Sequence(lambda n: f"ville-{n}")
    centroid = factory.LazyFunction(lambda: Point(10.18, 36.86, srid=4326))
    is_featured = False


class NeighborhoodFactory(factory.django.DjangoModelFactory[Neighborhood]):
    class Meta:
        model = Neighborhood
        django_get_or_create = ("city", "slug")

    city = factory.SubFactory(CityFactory)
    name = factory.Sequence(lambda n: f"Quartier {n}")
    slug = factory.Sequence(lambda n: f"quartier-{n}")
    centroid = factory.LazyFunction(lambda: Point(10.19, 36.87, srid=4326))
