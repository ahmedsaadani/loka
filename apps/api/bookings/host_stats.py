from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Avg, Count, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking, BookingRequest, BookingRequestStatus, BookingStatus
from core.auth import current_user
from core.permissions import IsHost
from listings.models import Property, PropertyStatus

ACTIVE_BOOKINGS = (BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED)


class HostStatsSerializer(serializers.Serializer[Any]):
    properties_total = serializers.IntegerField()
    properties_published = serializers.IntegerField()
    requests_total = serializers.IntegerField()
    requests_pending = serializers.IntegerField()
    acceptance_rate = serializers.FloatField(allow_null=True)
    response_rate = serializers.FloatField(allow_null=True)
    bookings_active = serializers.IntegerField()
    bookings_completed = serializers.IntegerField()
    revenue_completed = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_rating = serializers.FloatField(allow_null=True)
    reviews_total = serializers.IntegerField()


class HostStatsView(APIView):
    """Indicateurs de l'espace hôte, calculés sur les biens du propriétaire connecté."""

    permission_classes = [IsAuthenticated, IsHost]

    @extend_schema(responses={200: HostStatsSerializer})
    def get(self, request: Request) -> Response:
        user = current_user(request)
        props = Property.objects.filter(host=user)
        by_status = dict(
            BookingRequest.objects.filter(property__host=user)
            .values_list("status")
            .annotate(n=Count("id"))
            .values_list("status", "n")
        )
        accepted = by_status.get(BookingRequestStatus.ACCEPTED, 0)
        declined = by_status.get(BookingRequestStatus.DECLINED, 0)
        expired = by_status.get(BookingRequestStatus.EXPIRED, 0)
        answered = accepted + declined
        acceptance_rate = round(accepted / answered, 3) if answered else None
        # Taux de réponse : part des demandes traitées avant expiration.
        handled_base = answered + expired
        response_rate = round(answered / handled_base, 3) if handled_base else None

        bookings = Booking.objects.filter(host=user)
        revenue = bookings.filter(status=BookingStatus.COMPLETED).aggregate(s=Sum("total_amount"))[
            "s"
        ] or Decimal("0.00")
        rating_agg = props.filter(status=PropertyStatus.PUBLISHED, rating__isnull=False).aggregate(
            avg=Avg("rating"), reviews=Sum("review_count")
        )

        data = {
            "properties_total": props.count(),
            "properties_published": props.filter(status=PropertyStatus.PUBLISHED).count(),
            "requests_total": sum(by_status.values()),
            "requests_pending": by_status.get(BookingRequestStatus.PENDING, 0),
            "acceptance_rate": acceptance_rate,
            "response_rate": response_rate,
            "bookings_active": bookings.filter(status__in=ACTIVE_BOOKINGS).count(),
            "bookings_completed": bookings.filter(status=BookingStatus.COMPLETED).count(),
            "revenue_completed": revenue,
            "average_rating": round(rating_agg["avg"], 2) if rating_agg["avg"] else None,
            "reviews_total": rating_agg["reviews"] or 0,
        }
        return Response(HostStatsSerializer(data).data)
