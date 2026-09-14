from __future__ import annotations

import hmac
from typing import Any

from django.conf import settings
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.serializers import SignedUrlSerializer
from bookings import services
from bookings.models import Booking, BookingRequest, BookingStatus, Payment
from bookings.payments.base import get_payment_provider
from bookings.payments.konnect import KonnectError
from bookings.serializers import (
    BookingConfirmedSerializer,
    BookingRequestCreateSerializer,
    BookingRequestSerializer,
    BookingSerializer,
    CancelSerializer,
    DeclineSerializer,
    MockWebhookSerializer,
    PaymentSerializer,
)
from core.audit import log_sensitive_access
from core.auth import current_user
from core.exceptions import DomainError
from core.models import SensitiveAccessLog
from core.permissions import IsHost, IsStaff, is_staff_user
from core.storages import signed_private_url

CONFIRMED_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED}


# ----------------------------------------------------------------- voyageur


class TravelerRequestViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[BookingRequest]
):
    """Demandes du voyageur connecté."""

    permission_classes = [IsAuthenticated]
    serializer_class = BookingRequestSerializer
    lookup_field = "public_id"

    def get_queryset(self) -> QuerySet[BookingRequest]:
        if getattr(self, "swagger_fake_view", False):
            return BookingRequest.objects.none()
        return (
            BookingRequest.objects.filter(traveler=current_user(self.request))
            .select_related("property", "property__city", "traveler", "booking")
            .prefetch_related("property__photos")
        )

    @extend_schema(
        request=BookingRequestCreateSerializer, responses={201: BookingRequestSerializer}
    )
    def create(self, request: Request) -> Response:
        serializer = BookingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking_request = services.create_booking_request(
            prop=data["property"],
            traveler=current_user(request),
            rental_mode=data["rental_mode"],
            start=data["start_date"],
            end=data["end_date"],
            guests=data["guests"],
            message=data["message"],
        )
        return Response(
            BookingRequestSerializer(booking_request).data, status=status.HTTP_201_CREATED
        )

    def get_throttles(self) -> list[Any]:
        if self.action == "create":
            self.throttle_scope = "booking_request"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @extend_schema(request=None, responses={200: BookingRequestSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, public_id: str | None = None) -> Response:
        booking_request = self.get_object()
        services.cancel_request(booking_request, by=current_user(request))
        return Response(BookingRequestSerializer(booking_request).data)


class TravelerBookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Booking]
):
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self) -> QuerySet[Booking]:
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        return (
            Booking.objects.filter(traveler=current_user(self.request))
            .select_related("property", "property__city", "traveler", "host", "host__host_profile")
            .prefetch_related("payments", "property__photos")
        )

    def get_serializer_class(self) -> type[BookingSerializer]:
        return BookingSerializer

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        booking = self.get_object()
        if booking.status in CONFIRMED_STATUSES:
            log_sensitive_access(
                request._request, SensitiveAccessLog.Kind.PRIVATE_ADDRESS, booking.property
            )
            return Response(BookingConfirmedSerializer(booking).data)
        return Response(BookingSerializer(booking).data)

    @extend_schema(request=None, responses={201: PaymentSerializer})
    @action(detail=True, methods=["post"], url_path="pay-deposit")
    def pay_deposit(self, request: Request, public_id: str | None = None) -> Response:
        booking = self.get_object()
        payment = services.start_deposit_payment(booking, by=current_user(request))
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CancelSerializer, responses={200: BookingSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, public_id: str | None = None) -> Response:
        booking = self.get_object()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_booking(
            booking, by=current_user(request), reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)

    @extend_schema(responses={200: SignedUrlSerializer})
    @action(detail=True, methods=["get"])
    def contract(self, request: Request, public_id: str | None = None) -> Response:
        booking = self.get_object()
        return _contract_response(request, booking)


def _contract_response(request: Request, booking: Booking) -> Response:
    if not booking.contract_pdf:
        raise DomainError("Contrat non disponible.", code="no_contract")
    log_sensitive_access(request._request, SensitiveAccessLog.Kind.CONTRACT, booking)
    return Response(
        {
            "url": signed_private_url(booking.contract_pdf.name),
            "expires_in": settings.S3_PRIVATE_URL_EXPIRY_SECONDS,
        }
    )


# ----------------------------------------------------------------- hôte


class HostRequestViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[BookingRequest]
):
    """Demandes reçues sur les biens de l'hôte connecté."""

    permission_classes = [IsAuthenticated, IsHost]
    serializer_class = BookingRequestSerializer
    lookup_field = "public_id"
    filterset_fields = {"status": ["exact"], "property__public_id": ["exact"]}

    def get_queryset(self) -> QuerySet[BookingRequest]:
        if getattr(self, "swagger_fake_view", False):
            return BookingRequest.objects.none()
        return (
            BookingRequest.objects.filter(property__host=current_user(self.request))
            .select_related("property", "property__city", "traveler", "booking")
            .prefetch_related("property__photos")
        )

    @extend_schema(request=None, responses={201: BookingSerializer})
    @action(detail=True, methods=["post"])
    def accept(self, request: Request, public_id: str | None = None) -> Response:
        booking_request = self.get_object()
        booking = services.accept_request(booking_request, by=current_user(request))
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=DeclineSerializer, responses={200: BookingRequestSerializer})
    @action(detail=True, methods=["post"])
    def decline(self, request: Request, public_id: str | None = None) -> Response:
        booking_request = self.get_object()
        serializer = DeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.decline_request(
            booking_request, by=current_user(request), reason=serializer.validated_data["reason"]
        )
        return Response(BookingRequestSerializer(booking_request).data)


class HostBookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Booking]
):
    permission_classes = [IsAuthenticated, IsHost]
    serializer_class = BookingSerializer
    lookup_field = "public_id"
    filterset_fields = {"status": ["exact"], "property__public_id": ["exact"]}

    def get_queryset(self) -> QuerySet[Booking]:
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        return (
            Booking.objects.filter(host=current_user(self.request))
            .select_related("property", "property__city", "traveler", "host", "host__host_profile")
            .prefetch_related("payments", "property__photos")
        )

    @extend_schema(request=CancelSerializer, responses={200: BookingSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, public_id: str | None = None) -> Response:
        booking = self.get_object()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_booking(
            booking, by=current_user(request), reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)

    @extend_schema(responses={200: SignedUrlSerializer})
    @action(detail=True, methods=["get"])
    def contract(self, request: Request, public_id: str | None = None) -> Response:
        return _contract_response(request, self.get_object())


# ----------------------------------------------------------------- équipe


class StaffBookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Booking]
):
    permission_classes = [IsAuthenticated, IsStaff]
    serializer_class = BookingSerializer
    lookup_field = "public_id"
    filterset_fields = {"status": ["exact"], "rental_mode": ["exact"]}

    def get_queryset(self) -> QuerySet[Booking]:
        return Booking.objects.select_related(
            "property", "property__city", "traveler", "host", "host__host_profile"
        ).prefetch_related("payments", "property__photos")

    @extend_schema(request=CancelSerializer, responses={200: BookingSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, public_id: str | None = None) -> Response:
        booking = self.get_object()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_booking(
            booking, by=current_user(request), reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)


class StaffRequestViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[BookingRequest]):
    permission_classes = [IsAuthenticated, IsStaff]
    serializer_class = BookingRequestSerializer
    filterset_fields = {"status": ["exact"]}

    def get_queryset(self) -> QuerySet[BookingRequest]:
        return BookingRequest.objects.select_related(
            "property", "property__city", "traveler", "booking"
        ).prefetch_related("property__photos")


# ----------------------------------------------------------------- webhooks


class MockPaymentWebhookView(APIView):
    """Webhook du prestataire mock. Signé HMAC avec SECRET_KEY : non forgeable depuis le front."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(request=MockWebhookSerializer, responses={200: PaymentSerializer})
    def post(self, request: Request) -> Response:
        if settings.PAYMENT_PROVIDER != "mock":
            raise PermissionDenied("Webhook mock désactivé.")
        serializer = MockWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = get_payment_provider()
        try:
            result = provider.parse_webhook(dict(serializer.validated_data), {})
        except ValueError as exc:
            raise PermissionDenied(str(exc)) from exc
        payment = services.handle_payment_result(result)
        return Response(PaymentSerializer(payment).data)


class KonnectPaymentWebhookView(APIView):
    """
    Webhook Konnect : `GET|POST /webhooks/konnect/?payment_ref=...&token=...`.
    Le payload n'est pas signé : le prestataire relit l'état via l'API Konnect
    (voir `KonnectPaymentProvider.parse_webhook`). Le jeton secret filtre les pings forgés.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(exclude=True)
    def get(self, request: Request) -> Response:
        return self._handle(request)

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        return self._handle(request)

    def _handle(self, request: Request) -> Response:
        if settings.PAYMENT_PROVIDER != "konnect":
            raise PermissionDenied("Webhook Konnect désactivé.")
        expected = str(settings.KONNECT_WEBHOOK_TOKEN)
        given = str(request.query_params.get("token", ""))
        if not expected or not hmac.compare_digest(given, expected):
            raise PermissionDenied("Jeton de webhook invalide.")
        body = request.data if isinstance(request.data, dict) else {}
        payment_ref = request.query_params.get("payment_ref") or body.get("payment_ref", "")
        provider = get_payment_provider()
        try:
            result = provider.parse_webhook({"payment_ref": payment_ref}, {})
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except KonnectError as exc:
            # Konnect réessaiera ; on ne confirme jamais sans avoir relu l'état.
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        try:
            payment = services.handle_payment_result(result)
        except Payment.DoesNotExist:
            return Response({"detail": "Paiement inconnu."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": payment.status})


class MockPaymentSignView(APIView):
    """
    DEV UNIQUEMENT : renvoie la signature attendue par le webhook mock pour la page /paiement/mock.
    Réservé à l'utilisateur propriétaire du paiement.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request: Request, provider_ref: str) -> Response:
        if settings.PAYMENT_PROVIDER != "mock":
            raise PermissionDenied("Mock désactivé.")
        from bookings.models import Payment
        from bookings.payments.mock import MockPaymentProvider

        payment = (
            Payment.objects.select_related("booking").filter(provider_ref=provider_ref).first()
        )
        if payment is None or (
            payment.booking.traveler_id != request.user.pk and not is_staff_user(request.user)
        ):
            raise PermissionDenied("Paiement introuvable.")
        return Response(
            {
                "provider_ref": provider_ref,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "signatures": {
                    outcome: MockPaymentProvider.sign(provider_ref, outcome)
                    for outcome in ("succeeded", "failed")
                },
            }
        )
