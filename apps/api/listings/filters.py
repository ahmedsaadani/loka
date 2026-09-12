from __future__ import annotations

from datetime import date

import django_filters
from django.contrib.gis.geos import Polygon
from django.db.models import Exists, OuterRef, Q, QuerySet

from listings.models import Amenity, PricingPlan, Property, PropertyType, RentalMode


class PropertyFilter(django_filters.FilterSet):
    """
    Filtres de la recherche publique. Tous optionnels, combinables, sérialisables en URL.
    Le prix se filtre sur le plan du `rental_mode` demandé (mensuel par défaut).
    """

    city = django_filters.CharFilter(field_name="city__slug")
    neighborhood = django_filters.CharFilter(field_name="neighborhood__slug")
    property_type = django_filters.MultipleChoiceFilter(choices=PropertyType.choices)
    rental_mode = django_filters.ChoiceFilter(
        choices=RentalMode.choices, method="filter_rental_mode"
    )
    min_price = django_filters.NumberFilter(method="filter_min_price")
    max_price = django_filters.NumberFilter(method="filter_max_price")
    bedrooms_min = django_filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    guests = django_filters.NumberFilter(field_name="max_guests", lookup_expr="gte")
    furnished = django_filters.BooleanFilter()
    condition_grade = django_filters.CharFilter(field_name="condition_grade")
    amenities = django_filters.CharFilter(method="filter_amenities")
    bbox = django_filters.CharFilter(method="filter_bbox")
    start = django_filters.DateFilter(method="filter_noop")
    end = django_filters.DateFilter(method="filter_availability")

    class Meta:
        model = Property
        fields: list[str] = []

    # --- helpers

    def _mode(self) -> str:
        return str(self.data.get("rental_mode") or RentalMode.MONTHLY)

    def _plans(self, **extra: object) -> QuerySet[PricingPlan]:
        return PricingPlan.objects.filter(
            property=OuterRef("pk"), rental_mode=self._mode(), is_active=True, **extra
        )

    # --- méthodes

    def filter_rental_mode(
        self, qs: QuerySet[Property], name: str, value: str
    ) -> QuerySet[Property]:
        return qs.filter(Exists(self._plans()))

    def filter_min_price(
        self, qs: QuerySet[Property], name: str, value: object
    ) -> QuerySet[Property]:
        return qs.filter(Exists(self._plans(price__gte=value)))

    def filter_max_price(
        self, qs: QuerySet[Property], name: str, value: object
    ) -> QuerySet[Property]:
        return qs.filter(Exists(self._plans(price__lte=value)))

    def filter_amenities(self, qs: QuerySet[Property], name: str, value: str) -> QuerySet[Property]:
        codes = [c for c in value.split(",") if c]
        for code in codes:
            qs = qs.filter(amenities__in=Amenity.objects.filter(code=code))
        return qs.distinct() if codes else qs

    def filter_bbox(self, qs: QuerySet[Property], name: str, value: str) -> QuerySet[Property]:
        try:
            min_lng, min_lat, max_lng, max_lat = (float(v) for v in value.split(","))
        except ValueError:
            return qs.none()
        polygon = Polygon.from_bbox((min_lng, min_lat, max_lng, max_lat))
        polygon.srid = 4326
        return qs.filter(location__within=polygon)

    def filter_noop(self, qs: QuerySet[Property], name: str, value: date) -> QuerySet[Property]:
        return qs

    def filter_availability(
        self, qs: QuerySet[Property], name: str, value: date
    ) -> QuerySet[Property]:
        start = self.form.cleaned_data.get("start")
        if not start or value <= start:
            return qs
        return qs.exclude(
            Q(availability_blocks__start__lt=value) & Q(availability_blocks__end__gt=start)
        ).distinct()
