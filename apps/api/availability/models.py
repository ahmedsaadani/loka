from __future__ import annotations

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from core.models import TimeStampedModel
from listings.models import Property


class DateRange(Func):
    """daterange(start, end, '[)') : fin exclue (départ le jour d'une arrivée possible)."""

    function = "DATERANGE"
    output_field = DateRangeField()


class BlockKind(models.TextChoices):
    BOOKED = "booked", "Réservé"
    BLOCKED_BY_HOST = "blocked_by_host", "Bloqué par l'hôte"
    EXTERNAL_ICAL = "external_ical", "Calendrier externe"
    MAINTENANCE = "maintenance", "Maintenance"


class AvailabilityBlock(TimeStampedModel):
    """
    Période indisponible [start, end). Deux blocs `booked` d'un même bien ne peuvent pas
    se chevaucher : contrainte d'exclusion PostgreSQL (btree_gist) + validation service.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="availability_blocks"
    )
    start = models.DateField()
    end = models.DateField()
    kind = models.CharField(max_length=16, choices=BlockKind.choices)
    booking = models.ForeignKey(
        "bookings.Booking",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="availability_blocks",
    )
    external_calendar = models.ForeignKey(
        "availability.ExternalCalendar",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    external_uid = models.CharField(max_length=255, blank=True)
    note = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["start"]
        verbose_name = "indisponibilité"
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="availability_end_after_start"
            ),
            ExclusionConstraint(
                name="availability_no_overlapping_bookings",
                expressions=[
                    (DateRange("start", "end", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("property", RangeOperators.EQUAL),
                ],
                condition=Q(kind="booked"),
            ),
        ]
        indexes = [models.Index(fields=["property", "start", "end"])]

    def __str__(self) -> str:
        return f"{self.property_id} {self.kind} {self.start} -> {self.end}"


class CalendarSource(models.TextChoices):
    AIRBNB = "airbnb", "Airbnb"
    BOOKING = "booking", "Booking.com"
    OTHER = "other", "Autre"


class ExternalCalendar(TimeStampedModel):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="external_calendars"
    )
    ical_url = models.URLField(max_length=500)
    source = models.CharField(
        max_length=8, choices=CalendarSource.choices, default=CalendarSource.OTHER
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "calendrier externe"
        unique_together = [("property", "ical_url")]

    def __str__(self) -> str:
        return f"{self.source} pour {self.property_id}"
