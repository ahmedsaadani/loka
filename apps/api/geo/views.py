from __future__ import annotations

from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from geo.models import City, Neighborhood
from geo.selectors import cities_with_stats, neighborhoods_with_stats
from geo.serializers import (
    CityDetailSerializer,
    CitySummarySerializer,
    NeighborhoodDetailSerializer,
    NeighborhoodSummarySerializer,
)


class CityViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[City]):
    """Villes avec statistiques de biens publiés. Public."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    lookup_field = "slug"
    filterset_fields = {"is_featured": ["exact"], "governorate__slug": ["exact"]}
    ordering_fields = ("name", "property_count")

    def get_queryset(self) -> QuerySet[City]:
        qs = cities_with_stats()
        if self.action == "retrieve":
            qs = qs.prefetch_related(Prefetch("neighborhoods", queryset=neighborhoods_with_stats()))
        return qs

    def get_serializer_class(self) -> type[CitySummarySerializer]:
        return CityDetailSerializer if self.action == "retrieve" else CitySummarySerializer


class NeighborhoodListView(mixins.ListModelMixin, viewsets.GenericViewSet[Neighborhood]):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    serializer_class = NeighborhoodSummarySerializer
    filterset_fields = {"city__slug": ["exact"]}

    def get_queryset(self) -> QuerySet[Neighborhood]:
        return neighborhoods_with_stats()


class NeighborhoodDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(responses={200: NeighborhoodDetailSerializer})
    def get(self, request: Request, city_slug: str, slug: str) -> Response:
        neighborhood = get_object_or_404(
            neighborhoods_with_stats(), city__slug=city_slug, slug=slug
        )
        city = get_object_or_404(cities_with_stats(), slug=city_slug)
        neighborhood.city = city
        return Response(NeighborhoodDetailSerializer(neighborhood).data)
