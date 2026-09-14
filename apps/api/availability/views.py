from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from availability import services
from availability.models import AvailabilityBlock, ExternalCalendar
from availability.serializers import (
    AvailabilityBlockSerializer,
    BlockDatesSerializer,
    ExternalCalendarSerializer,
)
from availability.tasks import sync_external_calendar
from core.auth import current_user
from core.permissions import IsHost
from listings.models import Property


class HostCalendarViewSet(viewsets.GenericViewSet[AvailabilityBlock]):
    """
    Calendrier d'un bien pour son propriétaire :
    GET  /availability/host/properties/{public_id}/blocks/
    POST /availability/host/properties/{public_id}/blocks/       (bloquer des dates)
    DELETE /availability/host/properties/{public_id}/blocks/{id}/
    GET/POST /availability/host/properties/{public_id}/calendars/ (iCal)
    """

    permission_classes = [IsAuthenticated, IsHost]
    serializer_class = AvailabilityBlockSerializer
    pagination_class = None

    def _property(self) -> Property:
        return get_object_or_404(
            Property, public_id=self.kwargs["property_public_id"], host=current_user(self.request)
        )

    def get_queryset(self) -> QuerySet[AvailabilityBlock]:
        if getattr(self, "swagger_fake_view", False):
            return AvailabilityBlock.objects.none()
        horizon = timezone.localdate() - timedelta(days=30)
        return (
            AvailabilityBlock.objects.filter(property=self._property(), end__gte=horizon)
            .select_related("booking")
            .order_by("start")
        )

    @extend_schema(responses={200: AvailabilityBlockSerializer(many=True)})
    @action(detail=False, methods=["get", "post"], url_path="blocks")
    def blocks(self, request: Request, property_public_id: str | None = None) -> Response:
        prop = self._property()
        if request.method == "GET":
            return Response(AvailabilityBlockSerializer(self.get_queryset(), many=True).data)
        serializer = BlockDatesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = services.block_dates(prop, **serializer.validated_data)
        return Response(AvailabilityBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={204: None})
    @action(detail=False, methods=["delete"], url_path=r"blocks/(?P<block_id>\d+)")
    def delete_block(
        self, request: Request, property_public_id: str | None = None, block_id: str | None = None
    ) -> Response:
        prop = self._property()
        block = get_object_or_404(AvailabilityBlock, pk=block_id, property=prop)
        services.unblock(block)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=ExternalCalendarSerializer, responses={200: ExternalCalendarSerializer(many=True)}
    )
    @action(detail=False, methods=["get", "post"], url_path="calendars")
    def calendars(self, request: Request, property_public_id: str | None = None) -> Response:
        prop = self._property()
        if request.method == "GET":
            return Response(
                ExternalCalendarSerializer(prop.external_calendars.all(), many=True).data
            )
        serializer = ExternalCalendarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        calendar = serializer.save(property=prop)
        sync_external_calendar.delay(calendar.pk)
        return Response(ExternalCalendarSerializer(calendar).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        methods=["DELETE"],
        request=None,
        responses={204: None},
        operation_id="availability_host_properties_calendar_destroy",
    )
    @extend_schema(
        methods=["POST"],
        request=None,
        responses={202: None},
        operation_id="availability_host_properties_calendar_resync",
    )
    @action(detail=False, methods=["delete", "post"], url_path=r"calendars/(?P<calendar_id>\d+)")
    def calendar_detail(
        self,
        request: Request,
        property_public_id: str | None = None,
        calendar_id: str | None = None,
    ) -> Response:
        prop = self._property()
        calendar = get_object_or_404(ExternalCalendar, pk=calendar_id, property=prop)
        if request.method == "DELETE":
            calendar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        sync_external_calendar.delay(calendar.pk)
        return Response({"detail": "Synchronisation lancée."}, status=status.HTTP_202_ACCEPTED)

    def get_serializer(self, *args: Any, **kwargs: Any) -> Any:
        return super().get_serializer(*args, **kwargs)
