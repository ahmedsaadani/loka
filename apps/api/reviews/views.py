from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from bookings.models import Booking, BookingStatus
from core.auth import current_user
from reviews import services
from reviews.models import Review
from reviews.serializers import (
    MyReviewSerializer,
    ReviewableBookingSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)


class ReviewViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[Review]):
    """Avis des voyageurs. Lecture publique par bien, création réservée aux séjours terminés."""

    serializer_class = ReviewSerializer
    lookup_field = "public_id"

    def get_permissions(self) -> list[Any]:
        if self.action in {"create", "pending", "mine"}:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self) -> QuerySet[Review]:
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        qs = Review.objects.filter(is_published=True).select_related("author", "booking__property")
        slug = self.request.query_params.get("property")
        if slug:
            qs = qs.filter(booking__property__slug=slug)
        return qs.order_by("-created_at")

    @extend_schema(
        parameters=[OpenApiParameter("property", str, description="Slug du bien (obligatoire)")],
        responses={200: ReviewSerializer(many=True)},
    )
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        booking = get_object_or_404(Booking, public_id=serializer.validated_data["booking"])
        review = services.create_review(
            booking=booking,
            author=user,
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data["comment"],
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ReviewableBookingSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def pending(self, request: Request) -> Response:
        """Séjours terminés du voyageur qui n'ont pas encore d'avis."""
        user = current_user(request)
        bookings = (
            Booking.objects.filter(
                traveler=user, status=BookingStatus.COMPLETED, review__isnull=True
            )
            .select_related("property", "property__city")
            .order_by("-end_date")
        )
        return Response(ReviewableBookingSerializer(bookings, many=True).data)

    @extend_schema(responses={200: MyReviewSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def mine(self, request: Request) -> Response:
        """Avis déjà rédigés par le voyageur."""
        user = current_user(request)
        reviews = (
            Review.objects.filter(author=user)
            .select_related("author", "booking__property")
            .order_by("-created_at")
        )
        return Response(MyReviewSerializer(reviews, many=True).data)
