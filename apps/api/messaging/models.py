"""
Messagerie interne : une conversation par (bien, voyageur), entre le voyageur et l'hôte
du bien. Les messages sont marqués lus par destinataire via `read_at`.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import PublicIdModel, TimeStampedModel


class Conversation(PublicIdModel, TimeStampedModel):
    property = models.ForeignKey(
        "listings.Property", on_delete=models.CASCADE, related_name="conversations"
    )
    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_traveler"
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_host"
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "traveler"], name="conversation_unique_property_traveler"
            )
        ]

    def __str__(self) -> str:
        return f"Conversation {self.public_id} — {self.property_id}"

    def other_party(self, user_id: int) -> object:
        return self.host if user_id == self.traveler_id else self.traveler


class Message(PublicIdModel, TimeStampedModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    body = models.TextField(max_length=4000)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"Message {self.public_id} de {self.sender_id}"
