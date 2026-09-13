from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublicIdModel(models.Model):
    """UUID exposé dans les URLs publiques à la place de l'ID séquentiel."""

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True


class StatusLog(TimeStampedModel):
    """Journal de toutes les transitions d'état (Property, BookingRequest, Booking, ...)."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.content_type.model}#{self.object_id}: {self.from_status} -> {self.to_status}"


class SensitiveAccessLog(models.Model):
    """Chaque accès à une donnée sensible (document d'identité, contrat, adresse exacte)."""

    class Kind(models.TextChoices):
        IDENTITY_DOCUMENT = "identity_document", "Document d'identité"
        CONTRACT = "contract", "Contrat"
        PRIVATE_ADDRESS = "private_address", "Adresse exacte"
        BANK_DETAILS = "bank_details", "Coordonnées bancaires"
        PHOTO_ORIGINAL = "photo_original", "Photo originale"

    accessed_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)

    class Meta:
        ordering = ["-accessed_at"]
        indexes = [models.Index(fields=["kind", "target_type", "target_id"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.target_type}#{self.target_id} by {self.actor_id}"


class SiteContent(TimeStampedModel):
    """Contenu éditorial géré dans l'admin (CGU, confidentialité, contact...). Markdown simple."""

    key = models.SlugField(max_length=40, unique=True, help_text="cgu, confidentialite, contact")
    title = models.CharField(max_length=160)
    body = models.TextField(help_text="Markdown : titres (##), paragraphes, listes (-), gras (**).")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "contenu du site"
        verbose_name_plural = "contenus du site"

    def __str__(self) -> str:
        return f"{self.key} : {self.title}"
