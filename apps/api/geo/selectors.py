"""Requêtes de lecture réutilisées par l'API publique et le front SEO."""

from __future__ import annotations

from django.db.models import Avg, Count, Q, QuerySet

from geo.models import City, Neighborhood

PUBLISHED = Q(properties__status="published")


def cities_with_stats() -> QuerySet[City]:
    return (
        City.objects.select_related("governorate")
        .annotate(
            property_count=Count("properties", filter=PUBLISHED, distinct=True),
            avg_monthly_price=Avg(
                "properties__pricing_plans__price",
                filter=PUBLISHED
                & Q(properties__pricing_plans__rental_mode="monthly")
                & Q(properties__pricing_plans__is_active=True),
            ),
            avg_nightly_price=Avg(
                "properties__pricing_plans__price",
                filter=PUBLISHED
                & Q(properties__pricing_plans__rental_mode="nightly")
                & Q(properties__pricing_plans__is_active=True),
            ),
        )
        .order_by("-property_count", "name")
    )


def neighborhoods_with_stats(city: City | None = None) -> QuerySet[Neighborhood]:
    qs = Neighborhood.objects.select_related("city", "city__governorate")
    if city is not None:
        qs = qs.filter(city=city)
    return qs.annotate(
        property_count=Count("properties", filter=PUBLISHED, distinct=True),
        avg_monthly_price=Avg(
            "properties__pricing_plans__price",
            filter=PUBLISHED
            & Q(properties__pricing_plans__rental_mode="monthly")
            & Q(properties__pricing_plans__is_active=True),
        ),
    ).order_by("-property_count", "name")
