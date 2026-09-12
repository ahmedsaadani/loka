from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models

from core.models import PublicIdModel, TimeStampedModel


class LeadSource(models.TextChoices):
    TAYARA = "tayara", "Tayara"
    MUBAWAB = "mubawab", "Mubawab"
    FACEBOOK = "facebook", "Facebook"
    MANUAL = "manual", "Manuel"


class LeadStatus(models.TextChoices):
    NEW = "new", "Nouveau"
    CONTACTED = "contacted", "Contacté"
    VISIT_SCHEDULED = "visit_scheduled", "Visite planifiée"
    CONVERTED = "converted", "Converti"
    REJECTED = "rejected", "Rejeté"


class Lead(PublicIdModel, TimeStampedModel):
    """Bien repéré sur un site d'annonces, à contacter par l'équipe. Jamais public."""

    TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        LeadStatus.NEW: frozenset({LeadStatus.CONTACTED, LeadStatus.REJECTED}),
        LeadStatus.CONTACTED: frozenset(
            {LeadStatus.VISIT_SCHEDULED, LeadStatus.CONVERTED, LeadStatus.REJECTED}
        ),
        LeadStatus.VISIT_SCHEDULED: frozenset({LeadStatus.CONVERTED, LeadStatus.REJECTED}),
        LeadStatus.CONVERTED: frozenset(),
        LeadStatus.REJECTED: frozenset({LeadStatus.NEW}),
    }

    source = models.CharField(max_length=10, choices=LeadSource.choices, default=LeadSource.MANUAL)
    source_url = models.URLField(max_length=500, blank=True)
    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=LeadStatus.choices, default=LeadStatus.NEW)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
    )
    notes = models.TextField(blank=True)
    converted_property = models.ForeignKey(
        "listings.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_leads",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "lead"
        constraints = [
            models.UniqueConstraint(
                fields=["source_url"],
                condition=~models.Q(source_url=""),
                name="lead_unique_source_url",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.source}, {self.status})"
