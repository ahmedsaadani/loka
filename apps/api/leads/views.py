from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from core.auth import current_user
from core.permissions import IsStaff
from leads import services
from leads.models import Lead
from leads.serializers import (
    LeadConvertSerializer,
    LeadImportResultSerializer,
    LeadImportSerializer,
    LeadSerializer,
    LeadStatusSerializer,
    LeadWriteSerializer,
)
from listings.serializers import PropertyStaffSerializer

IMPORT_MAX_BYTES = 5 * 1024 * 1024


class LeadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet[Lead],
):
    """Outil interne : biens repérés à contacter. Staff uniquement."""

    permission_classes = [IsAuthenticated, IsStaff]
    lookup_field = "public_id"
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = {"status": ["exact"], "source": ["exact"], "city": ["exact", "icontains"]}
    ordering_fields = ("created_at", "updated_at", "price")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self) -> QuerySet[Lead]:
        return Lead.objects.select_related("assigned_to", "converted_property").order_by(
            "-created_at"
        )

    def get_serializer_class(self) -> type[Any]:
        if self.action in {"create", "partial_update", "update"}:
            return LeadWriteSerializer
        return LeadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = LeadWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        lead = self.get_object()
        serializer = LeadWriteSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeadSerializer(lead).data)

    @extend_schema(request=LeadStatusSerializer, responses={200: LeadSerializer})
    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request: Request, public_id: str | None = None) -> Response:
        lead = self.get_object()
        serializer = LeadStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_status(
            lead,
            serializer.validated_data["status"],
            by=current_user(request),
            note=serializer.validated_data["note"],
        )
        return Response(LeadSerializer(lead).data)

    @extend_schema(request=LeadConvertSerializer, responses={201: PropertyStaffSerializer})
    @action(detail=True, methods=["post"])
    def convert(self, request: Request, public_id: str | None = None) -> Response:
        lead = self.get_object()
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop = services.convert_to_property(
            lead,
            host=serializer.validated_data["host_email"],
            city=serializer.validated_data["city"],
            by=current_user(request),
        )
        return Response(PropertyStaffSerializer(prop).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=LeadImportSerializer, responses={200: LeadImportResultSerializer})
    @action(
        detail=False, methods=["post"], url_path="import", throttle_classes=[ScopedRateThrottle]
    )
    def import_file(self, request: Request) -> Response:
        serializer = LeadImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        if upload.size > IMPORT_MAX_BYTES:
            raise ValidationError({"file": "Fichier trop volumineux (max 5 Mo)."})
        content_type = upload.content_type or ""
        if (
            "json" not in content_type
            and "csv" not in content_type
            and not str(upload.name).endswith((".csv", ".json"))
        ):
            raise ValidationError({"file": "Format accepté : CSV ou JSON."})
        if str(upload.name).endswith(".json"):
            content_type = "application/json"
        rows = services.parse_import_payload(upload.read(), content_type)
        created, skipped = services.import_leads(rows, by=current_user(request))
        return Response({"created": created, "skipped": skipped})

    import_file.throttle_scope = "lead_import"  # type: ignore[attr-defined]
