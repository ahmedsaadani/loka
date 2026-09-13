from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import OuterRef, QuerySet, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.services import ensure_host_profile
from availability import services as availability_services
from bookings import services as booking_services
from core.audit import log_sensitive_access
from core.auth import current_user
from core.exceptions import ConflictError
from core.models import SensitiveAccessLog
from core.permissions import IsHost, IsStaff
from listings import services
from listings.filters import PropertyFilter
from listings.models import (
    Amenity,
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyStatus,
    RentalMode,
)
from listings.serializers import (
    AmenitySerializer,
    NoteSerializer,
    PhotoReorderSerializer,
    PhotoSerializer,
    PhotoUploadSerializer,
    PricingPlanSerializer,
    PricingPlanWriteSerializer,
    PropertyCardSerializer,
    PropertyDetailSerializer,
    PropertyHostSerializer,
    PropertyStaffSerializer,
    PropertyWriteSerializer,
    PublishSerializer,
    QuoteQuerySerializer,
    QuoteSerializer,
    ReasonSerializer,
    ScheduleVisitSerializer,
    UnavailableRangeSerializer,
)

MAX_CALENDAR_DAYS = 400


# ----------------------------------------------------------------- public


class PublicPropertyViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Property]
):
    """Biens publiés. Recherche filtrable, fiche, calendrier et devis."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    lookup_field = "slug"
    filterset_class = PropertyFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self) -> QuerySet[Property]:
        qs = Property.objects.for_public()
        ordering = self.request.query_params.get("ordering", "newest")
        mode = self.request.query_params.get("rental_mode") or RentalMode.MONTHLY
        if ordering in {"price", "-price"}:
            price_sq = PricingPlan.objects.filter(
                property=OuterRef("pk"), rental_mode=mode, is_active=True
            ).values("price")[:1]
            qs = qs.annotate(sort_price=Subquery(price_sq)).order_by(
                ("-" if ordering.startswith("-") else "") + "sort_price", "-published_at"
            )
        else:
            qs = qs.order_by("-published_at", "-id")
        return qs

    def get_serializer_class(self) -> type[Any]:
        return PropertyDetailSerializer if self.action == "retrieve" else PropertyCardSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, description="Date ISO (défaut : aujourd'hui)"),
            OpenApiParameter("to", str, description="Date ISO (défaut : +180 jours)"),
        ],
        responses={200: UnavailableRangeSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def availability(self, request: Request, slug: str | None = None) -> Response:
        prop = self.get_object()
        today = timezone.localdate()
        from_date = _parse_date(request.query_params.get("from"), today)
        to_date = _parse_date(request.query_params.get("to"), today + timedelta(days=180))
        to_date = min(to_date, from_date + timedelta(days=MAX_CALENDAR_DAYS))
        ranges = availability_services.unavailable_ranges(prop, from_date, to_date)
        return Response([{"start": s, "end": e} for s, e in ranges])

    @extend_schema(
        parameters=[
            OpenApiParameter("rental_mode", str, required=True),
            OpenApiParameter("start", str, required=True),
            OpenApiParameter("end", str, required=True),
        ],
        responses={200: QuoteSerializer},
    )
    @action(detail=True, methods=["get"])
    def quote(self, request: Request, slug: str | None = None) -> Response:
        prop = self.get_object()
        params = QuoteQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        quote = booking_services.quote_for(
            prop,
            params.validated_data["rental_mode"],
            params.validated_data["start"],
            params.validated_data["end"],
        )
        available = availability_services.is_available(
            prop, params.validated_data["start"], params.validated_data["end"]
        )
        data = QuoteSerializer(quote).data
        data["available"] = available
        return Response(data)


def _parse_date(raw: str | None, default: date) -> date:
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return default


class AmenityListView(mixins.ListModelMixin, viewsets.GenericViewSet[Amenity]):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    serializer_class = AmenitySerializer
    queryset = Amenity.objects.all()
    pagination_class = None


# ----------------------------------------------------------------- hôte


class HostPropertyViewSet(viewsets.ModelViewSet[Property]):
    """Biens du propriétaire connecté. Un hôte ne voit et ne modifie que les siens."""

    permission_classes = [IsAuthenticated, IsHost]
    lookup_field = "public_id"
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Property]:
        return (
            Property.objects.filter(host=current_user(self.request))
            .select_related("city", "neighborhood")
            .prefetch_related("photos", "pricing_plans", "amenities")
            .order_by("-updated_at")
        )

    def get_serializer_class(self) -> type[Any]:
        if self.action in {"create", "partial_update"}:
            return PropertyWriteSerializer
        return PropertyHostSerializer

    def perform_create(self, serializer: Any) -> None:
        ensure_host_profile(current_user(self.request))
        serializer.save(host=current_user(self.request))

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PropertyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            PropertyHostSerializer(serializer.instance).data, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        prop = self.get_object()
        # ADR 0007 : modifiable dans tous les états ; les champs descriptifs d'un bien publié
        # le renvoient en validation (l'ancienne version reste visible).
        services.update_property(prop, by=current_user(request), data=dict(request.data.items()))
        prop.refresh_from_db()
        return Response(PropertyHostSerializer(prop).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        prop = self.get_object()
        if prop.status != PropertyStatus.DRAFT:
            raise ConflictError("Seul un brouillon peut être supprimé.", code="not_draft")
        prop.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- transitions

    @extend_schema(request=None, responses={200: PropertyHostSerializer})
    @action(detail=True, methods=["post"])
    def submit(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        services.submit_for_review(prop, by=current_user(request))
        return Response(PropertyHostSerializer(prop).data)

    @extend_schema(request=None, responses={200: PropertyHostSerializer})
    @action(detail=True, methods=["post"])
    def withdraw(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        services.withdraw_to_draft(prop, by=current_user(request))
        return Response(PropertyHostSerializer(prop).data)

    @extend_schema(request=NoteSerializer, responses={200: PropertyHostSerializer})
    @action(detail=True, methods=["post"])
    def pause(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        note = NoteSerializer(data=request.data)
        note.is_valid(raise_exception=True)
        services.pause(prop, by=current_user(request), note=note.validated_data["note"])
        return Response(PropertyHostSerializer(prop).data)

    @extend_schema(request=None, responses={200: PropertyHostSerializer})
    @action(detail=True, methods=["post"])
    def resume(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        services.resume(prop, by=current_user(request))
        return Response(PropertyHostSerializer(prop).data)

    # --- photos

    @extend_schema(request=PhotoUploadSerializer, responses={201: PhotoSerializer})
    @action(
        detail=True,
        methods=["post"],
        throttle_classes=[ScopedRateThrottle],
        url_path="photos",
    )
    def upload_photo(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = services.add_photo(
            prop,
            upload=serializer.validated_data["image"],
            alt_text=serializer.validated_data["alt_text"],
            by=current_user(request),
        )
        return Response(PhotoSerializer(photo).data, status=status.HTTP_201_CREATED)

    upload_photo.throttle_scope = "upload"  # type: ignore[attr-defined]

    @extend_schema(request=PhotoReorderSerializer, responses={200: PhotoSerializer(many=True)})
    @action(detail=True, methods=["post"], url_path="photos/reorder")
    def reorder_photos(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PhotoReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reorder_photos(prop, [str(u) for u in serializer.validated_data["order"]])
        photos = PropertyPhoto.objects.filter(property=prop).order_by("order")
        return Response(PhotoSerializer(photos, many=True).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>[0-9a-f-]{36})")
    def delete_photo(
        self, request: Request, public_id: str | None = None, photo_id: str | None = None
    ) -> Response:
        prop = self.get_object()
        photo = get_object_or_404(PropertyPhoto, property=prop, public_id=photo_id)
        services.delete_photo(photo, by=current_user(request))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- tarifs

    @extend_schema(
        request=PricingPlanWriteSerializer, responses={200: PricingPlanSerializer(many=True)}
    )
    @action(detail=True, methods=["post"], url_path="pricing")
    def set_pricing(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PricingPlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.upsert_pricing_plan(prop, **serializer.validated_data)
        plans = PricingPlan.objects.filter(property=prop)
        return Response(PricingPlanSerializer(plans, many=True).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"pricing/(?P<mode>nightly|monthly|yearly)")
    def delete_pricing(
        self, request: Request, public_id: str | None = None, mode: str | None = None
    ) -> Response:
        prop = self.get_object()
        prop.pricing_plans.filter(rental_mode=mode).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------- équipe


class StaffPropertyViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Property]
):
    """File de validation et actions de l'équipe. L'accès à l'adresse exacte est journalisé."""

    permission_classes = [IsAuthenticated, IsStaff]
    lookup_field = "public_id"
    serializer_class = PropertyStaffSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = {"status": ["exact"], "city__slug": ["exact"]}
    ordering_fields = ("updated_at", "created_at", "visit_scheduled_at")

    def get_queryset(self) -> QuerySet[Property]:
        return (
            Property.objects.select_related("city", "neighborhood", "host")
            .prefetch_related("photos", "pricing_plans", "amenities")
            .order_by("-updated_at")
        )

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        prop = self.get_object()
        log_sensitive_access(request._request, SensitiveAccessLog.Kind.PRIVATE_ADDRESS, prop)
        return Response(PropertyStaffSerializer(prop).data)

    @extend_schema(request=ScheduleVisitSerializer, responses={200: PropertyStaffSerializer})
    @action(detail=True, methods=["post"], url_path="schedule-visit")
    def schedule_visit(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = ScheduleVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.schedule_visit(
            prop,
            by=current_user(request),
            visit_at=serializer.validated_data["visit_at"],
            note=serializer.validated_data["note"],
        )
        return Response(PropertyStaffSerializer(prop).data)

    @extend_schema(request=NoteSerializer, responses={200: PropertyStaffSerializer})
    @action(detail=True, methods=["post"], url_path="back-to-review")
    def back_to_review(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.back_to_review(
            prop, by=current_user(request), note=serializer.validated_data["note"]
        )
        return Response(PropertyStaffSerializer(prop).data)

    @extend_schema(request=PublishSerializer, responses={200: PropertyStaffSerializer})
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.publish(prop, by=current_user(request), **serializer.validated_data)
        from notifications import emails

        emails.send_property_published(prop)
        return Response(PropertyStaffSerializer(prop).data)

    @extend_schema(request=ReasonSerializer, responses={200: PropertyStaffSerializer})
    @action(detail=True, methods=["post"])
    def reject(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject(prop, by=current_user(request), reason=serializer.validated_data["reason"])
        from notifications import emails

        emails.send_property_rejected(prop)
        return Response(PropertyStaffSerializer(prop).data)

    @extend_schema(request=PhotoUploadSerializer, responses={201: PhotoSerializer})
    @action(detail=True, methods=["post"], url_path="photos")
    def upload_team_photo(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = services.add_photo(
            prop,
            upload=serializer.validated_data["image"],
            alt_text=serializer.validated_data["alt_text"],
            taken_by_team=True,
        )
        return Response(PhotoSerializer(photo).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=PhotoReorderSerializer, responses={200: PhotoSerializer(many=True)})
    @action(detail=True, methods=["post"], url_path="photos/reorder")
    def reorder_photos(self, request: Request, public_id: str | None = None) -> Response:
        prop = self.get_object()
        serializer = PhotoReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reorder_photos(prop, [str(u) for u in serializer.validated_data["order"]])
        photos = PropertyPhoto.objects.filter(property=prop).order_by("order")
        return Response(PhotoSerializer(photos, many=True).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>[0-9a-f-]{36})")
    def delete_photo(
        self, request: Request, public_id: str | None = None, photo_id: str | None = None
    ) -> Response:
        prop = self.get_object()
        photo = get_object_or_404(PropertyPhoto, property=prop, public_id=photo_id)
        services.delete_photo(photo)
        return Response(status=status.HTTP_204_NO_CONTENT)
