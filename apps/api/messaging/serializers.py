from __future__ import annotations

from typing import Any

from rest_framework import serializers

from listings.models import Property
from messaging.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer[Message]):
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("public_id", "body", "is_me", "read_at", "created_at")
        read_only_fields = fields

    def get_is_me(self, obj: Message) -> bool:
        user = self.context.get("user")
        return bool(user and obj.sender_id == user.id)


def _cover(prop: Property) -> str | None:
    photo = next(
        (p for p in prop.photos.all() if p.is_cover and p.variants),
        next((p for p in prop.photos.all() if p.variants), None),
    )
    if not photo:
        return None
    return photo.variants.get("thumb") or photo.variants.get("card")


class ConversationSerializer(serializers.ModelSerializer[Conversation]):
    property = serializers.SerializerMethodField()
    other_party = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "public_id",
            "property",
            "other_party",
            "last_message",
            "unread_count",
            "last_message_at",
        )
        read_only_fields = fields

    def get_property(self, obj: Conversation) -> dict[str, Any]:
        prop = obj.property
        return {
            "slug": prop.slug,
            "title": prop.title,
            "city": prop.city.name,
            "cover": _cover(prop),
        }

    def get_other_party(self, obj: Conversation) -> dict[str, str]:
        user = self.context.get("user")
        other = obj.host if user and user.id == obj.traveler_id else obj.traveler
        name = (other.first_name or "").strip() or other.email.split("@")[0]
        role = "Hôte" if other.id == obj.host_id else "Voyageur"
        return {"name": name, "role": role}

    def get_last_message(self, obj: Conversation) -> dict[str, Any] | None:
        msg = obj.messages.order_by("created_at").last()
        if not msg:
            return None
        user = self.context.get("user")
        return {
            "body": msg.body[:140],
            "is_me": bool(user and msg.sender_id == user.id),
            "created_at": msg.created_at,
        }

    def get_unread_count(self, obj: Conversation) -> int:
        user = self.context.get("user")
        if not user:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender=user).count()


class StartConversationSerializer(serializers.Serializer[dict[str, Any]]):
    property = serializers.SlugField()
    body = serializers.CharField(max_length=4000)


class MessageWriteSerializer(serializers.Serializer[dict[str, Any]]):
    body = serializers.CharField(max_length=4000)
