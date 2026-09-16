from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.auth import current_user
from listings.models import Property, PropertyStatus
from messaging.models import Conversation, Message
from messaging.serializers import (
    ConversationSerializer,
    MessageSerializer,
    MessageWriteSerializer,
    StartConversationSerializer,
)


class ConversationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Conversation]
):
    """Conversations de l'utilisateur courant (comme voyageur ou comme hôte)."""

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    lookup_field = "public_id"

    def get_queryset(self) -> QuerySet[Conversation]:
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        user = current_user(self.request)
        return (
            Conversation.objects.filter(Q(traveler=user) | Q(host=user))
            .select_related("property", "property__city", "traveler", "host")
            .prefetch_related("property__photos", "messages")
        )

    def get_serializer_context(self) -> dict[str, Any]:
        ctx = super().get_serializer_context()
        ctx["user"] = current_user(self.request)
        return ctx

    @extend_schema(responses={200: ConversationSerializer})
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        conversation = self.get_object()
        user = current_user(request)
        # Marque lus les messages reçus.
        conversation.messages.filter(read_at__isnull=True).exclude(sender=user).update(
            read_at=timezone.now()
        )
        data = self.get_serializer(conversation).data
        data["messages"] = MessageSerializer(
            conversation.messages.order_by("created_at"), many=True, context={"user": user}
        ).data
        return Response(data)

    @extend_schema(request=StartConversationSerializer, responses={201: ConversationSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        prop = get_object_or_404(
            Property, slug=serializer.validated_data["property"], status=PropertyStatus.PUBLISHED
        )
        if prop.host_id == user.id:
            return Response(
                {"detail": "Vous êtes l'hôte de ce logement."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conversation, _ = Conversation.objects.get_or_create(
            property=prop, traveler=user, defaults={"host": prop.host}
        )
        self._add_message(conversation, user, serializer.validated_data["body"])
        return Response(self.get_serializer(conversation).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=MessageWriteSerializer, responses={201: MessageSerializer})
    @action(detail=True, methods=["post"])
    def messages(self, request: Request, public_id: str | None = None) -> Response:
        conversation = self.get_object()
        serializer = MessageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        message = self._add_message(conversation, user, serializer.validated_data["body"])
        return Response(
            MessageSerializer(message, context={"user": user}).data,
            status=status.HTTP_201_CREATED,
        )

    def _add_message(self, conversation: Conversation, sender: Any, body: str) -> Message:
        message = Message.objects.create(conversation=conversation, sender=sender, body=body)
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=["last_message_at", "updated_at"])
        return message


class UnreadCountSerializer(serializers.Serializer[Any]):
    count = serializers.IntegerField()


class UnreadCountView(viewsets.ViewSet):
    """Nombre total de messages non lus (pastille de notification)."""

    permission_classes = [IsAuthenticated]
    serializer_class = UnreadCountSerializer

    @extend_schema(responses={200: UnreadCountSerializer})
    def list(self, request: Request) -> Response:
        user = current_user(request)
        count = (
            Message.objects.filter(
                Q(conversation__traveler=user) | Q(conversation__host=user), read_at__isnull=True
            )
            .exclude(sender=user)
            .count()
        )
        return Response({"count": count})
