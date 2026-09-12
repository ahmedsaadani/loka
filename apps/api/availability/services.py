"""Disponibilités : vérification de chevauchement, blocs hôte, blocs de réservation, iCal."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from availability.models import AvailabilityBlock, BlockKind, ExternalCalendar
from core.exceptions import ConflictError
from listings.models import Property

if TYPE_CHECKING:
    from bookings.models import Booking

logger = logging.getLogger(__name__)


def overlapping_blocks(
    prop: Property, start: date, end: date, *, exclude_pk: int | None = None
) -> QuerySet[AvailabilityBlock]:
    """Blocs de toute nature chevauchant [start, end)."""
    qs = AvailabilityBlock.objects.filter(property=prop, start__lt=end, end__gt=start)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def is_available(prop: Property, start: date, end: date) -> bool:
    if end <= start:
        return False
    return not overlapping_blocks(prop, start, end).exists()


def assert_available(prop: Property, start: date, end: date) -> None:
    if end <= start:
        raise ValidationError({"end_date": "La date de fin doit être après la date de début."})
    if start < timezone.localdate():
        raise ValidationError({"start_date": "La date de début est déjà passée."})
    if overlapping_blocks(prop, start, end).exists():
        raise ConflictError("Ces dates ne sont plus disponibles.", code="unavailable")


def unavailable_ranges(prop: Property, from_date: date, to_date: date) -> list[tuple[date, date]]:
    """Périodes indisponibles (fusionnées) pour l'affichage du calendrier public."""
    blocks = overlapping_blocks(prop, from_date, to_date).order_by("start")
    merged: list[tuple[date, date]] = []
    for block in blocks:
        start, end = max(block.start, from_date), min(block.end, to_date)
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


@transaction.atomic
def block_dates(
    prop: Property, start: date, end: date, *, note: str = "", kind: str = BlockKind.BLOCKED_BY_HOST
) -> AvailabilityBlock:
    """Blocage manuel par l'hôte. Refusé si une réservation existe sur la période."""
    if end <= start:
        raise ValidationError({"end": "La date de fin doit être après la date de début."})
    if overlapping_blocks(prop, start, end).filter(kind=BlockKind.BOOKED).exists():
        raise ConflictError("Une réservation existe déjà sur cette période.", code="booked")
    return AvailabilityBlock.objects.create(
        property=prop, start=start, end=end, kind=kind, note=note
    )


@transaction.atomic
def unblock(block: AvailabilityBlock) -> None:
    if block.kind == BlockKind.BOOKED:
        raise ConflictError(
            "Un bloc de réservation ne se supprime pas manuellement.", code="booked"
        )
    block.delete()


@transaction.atomic
def book_period(booking: Booking) -> AvailabilityBlock:
    """Crée le bloc `booked`. La contrainte d'exclusion protège contre les courses."""
    prop = booking.property
    if overlapping_blocks(prop, booking.start_date, booking.end_date).exists():
        raise ConflictError("Ces dates ne sont plus disponibles.", code="unavailable")
    try:
        return AvailabilityBlock.objects.create(
            property=prop,
            start=booking.start_date,
            end=booking.end_date,
            kind=BlockKind.BOOKED,
            booking=booking,
        )
    except IntegrityError as exc:
        raise ConflictError("Ces dates viennent d'être réservées.", code="unavailable") from exc


@transaction.atomic
def release_booking(booking: Booking) -> int:
    deleted, _ = AvailabilityBlock.objects.filter(booking=booking).delete()
    return deleted


# ----------------------------------------------------------------- iCal

_ICAL_DATE = re.compile(r"^(?P<key>DTSTART|DTEND|UID)(?:;[^:]*)?:(?P<value>.+)$")


def parse_ical_events(text: str) -> list[tuple[str, date, date]]:
    """Parseur iCal minimal : (uid, start, end) pour chaque VEVENT. Dates DATE ou DATE-TIME UTC."""
    events: list[tuple[str, date, date]] = []
    current: dict[str, str] = {}
    lines = text.replace("\r\n", "\n").replace("\n ", "").split("\n")
    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if "DTSTART" in current and "DTEND" in current:
                events.append(
                    (
                        current.get("UID", ""),
                        _ical_to_date(current["DTSTART"]),
                        _ical_to_date(current["DTEND"]),
                    )
                )
        else:
            match = _ICAL_DATE.match(line)
            if match:
                current[match["key"]] = match["value"]
    return events


def _ical_to_date(value: str) -> date:
    value = value.strip().rstrip("Z")
    if "T" in value:
        return datetime.strptime(value, "%Y%m%dT%H%M%S").date()
    return datetime.strptime(value, "%Y%m%d").date()


@transaction.atomic
def apply_ical_events(calendar: ExternalCalendar, events: list[tuple[str, date, date]]) -> int:
    """Remplace les blocs du calendrier par les événements reçus.

    Les événements qui chevauchent une réservation sont ignorés.
    """
    AvailabilityBlock.objects.filter(external_calendar=calendar).delete()
    created = 0
    horizon = timezone.localdate() - timedelta(days=1)
    for uid, start, end in events:
        if end <= start or end <= horizon:
            continue
        conflicts = overlapping_blocks(calendar.property, start, end).filter(
            Q(kind=BlockKind.BOOKED)
        )
        if conflicts.exists():
            logger.warning("ical_conflict calendar=%s uid=%s", calendar.pk, uid)
            continue
        AvailabilityBlock.objects.create(
            property=calendar.property,
            start=start,
            end=end,
            kind=BlockKind.EXTERNAL_ICAL,
            external_calendar=calendar,
            external_uid=uid[:255],
        )
        created += 1
    calendar.last_synced_at = timezone.now()
    calendar.last_error = ""
    calendar.save(update_fields=["last_synced_at", "last_error", "updated_at"])
    return created
