from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsStaff


class StaffStatsView(APIView):
    """Chiffres clés du back-office."""

    permission_classes = [IsStaff]

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request: Request) -> Response:
        from django.db.models import Count
        from django.utils import timezone

        from accounts.models import IdentityDocument, IdentityDocumentStatus, User
        from bookings.models import Booking, BookingRequest, BookingRequestStatus, BookingStatus
        from leads.models import Lead, LeadStatus
        from listings.models import Property, PropertyStatus

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        requests_by_status = dict(
            BookingRequest.objects.values_list("status")
            .annotate(n=Count("id"))
            .values_list("status", "n")
        )
        answered = requests_by_status.get(
            BookingRequestStatus.ACCEPTED, 0
        ) + requests_by_status.get(BookingRequestStatus.DECLINED, 0)
        acceptance_rate = (
            round(requests_by_status.get(BookingRequestStatus.ACCEPTED, 0) / answered, 3)
            if answered
            else None
        )
        return Response(
            {
                "properties": dict(
                    Property.objects.values_list("status")
                    .annotate(n=Count("id"))
                    .values_list("status", "n")
                ),
                "properties_published": Property.objects.filter(
                    status=PropertyStatus.PUBLISHED
                ).count(),
                "pending_review": Property.objects.filter(
                    status__in=[PropertyStatus.PENDING_REVIEW, PropertyStatus.NEEDS_VISIT]
                ).count(),
                "requests": requests_by_status,
                "requests_this_month": BookingRequest.objects.filter(
                    created_at__gte=month_start
                ).count(),
                "acceptance_rate": acceptance_rate,
                "bookings_confirmed": Booking.objects.filter(
                    status__in=[
                        BookingStatus.CONFIRMED,
                        BookingStatus.IN_PROGRESS,
                        BookingStatus.COMPLETED,
                    ]
                ).count(),
                "bookings_this_month": Booking.objects.filter(created_at__gte=month_start).count(),
                "identity_pending": IdentityDocument.objects.filter(
                    status=IdentityDocumentStatus.PENDING
                ).count(),
                "leads_new": Lead.objects.filter(status=LeadStatus.NEW).count(),
                "hosts": User.objects.filter(role="host").count(),
                "travelers": User.objects.filter(role="traveler").count(),
            }
        )


class SiteContentView(APIView):
    """Page éditoriale publiée (CGU, confidentialité, contact), en Markdown brut."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request: Request, key: str) -> Response:
        from django.shortcuts import get_object_or_404

        from core.models import SiteContent

        content = get_object_or_404(SiteContent, key=key, is_published=True)
        return Response(
            {
                "key": content.key,
                "title": content.title,
                "body": content.body,
                "updated_at": content.updated_at,
                "needs_writing": "[À RÉDIGER]" in content.body or "[À RÉDIGER]" in content.title,
            }
        )


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes: list[type] = []

    @extend_schema(responses={200: {"type": "object"}}, description="Santé de l'API et de la base.")
    def get(self, request: Request) -> Response:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return Response({"status": "ok", "database": "ok"})
