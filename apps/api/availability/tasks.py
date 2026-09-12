from __future__ import annotations

import logging
import urllib.request

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

ICAL_TIMEOUT_SECONDS = 15
ICAL_MAX_BYTES = 2 * 1024 * 1024


@shared_task(
    name="availability.tasks.sync_external_calendar", autoretry_for=(OSError,), max_retries=2
)
def sync_external_calendar(calendar_id: int) -> int:
    from availability import services
    from availability.models import ExternalCalendar

    calendar = ExternalCalendar.objects.select_related("property").get(pk=calendar_id)
    if not calendar.ical_url.startswith("https://"):
        calendar.last_error = "Seules les URLs HTTPS sont acceptées."
        calendar.save(update_fields=["last_error", "updated_at"])
        return 0
    try:
        with urllib.request.urlopen(  # noqa: S310  # nosec B310 - schéma https vérifié ci-dessus
            calendar.ical_url, timeout=ICAL_TIMEOUT_SECONDS
        ) as response:
            raw = response.read(ICAL_MAX_BYTES + 1)
    except OSError as exc:
        calendar.last_error = str(exc)[:255]
        calendar.last_synced_at = timezone.now()
        calendar.save(update_fields=["last_error", "last_synced_at", "updated_at"])
        raise
    if len(raw) > ICAL_MAX_BYTES:
        calendar.last_error = "Fichier iCal trop volumineux."
        calendar.save(update_fields=["last_error", "updated_at"])
        return 0
    events = services.parse_ical_events(raw.decode("utf-8", errors="replace"))
    return services.apply_ical_events(calendar, events)


@shared_task(name="availability.tasks.sync_all_external_calendars")
def sync_all_external_calendars() -> int:
    from availability.models import ExternalCalendar

    ids = list(ExternalCalendar.objects.values_list("pk", flat=True))
    for calendar_id in ids:
        sync_external_calendar.delay(calendar_id)
    return len(ids)
