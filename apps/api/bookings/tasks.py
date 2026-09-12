from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="bookings.tasks.expire_pending_requests")
def expire_pending_requests() -> int:
    from bookings import services
    from bookings.models import BookingRequest, BookingRequestStatus

    count = 0
    for request in BookingRequest.objects.filter(
        status=BookingRequestStatus.PENDING, expires_at__lte=timezone.now()
    ).select_related("property", "property__host", "traveler"):
        services.expire_request(request)
        count += 1
    return count


@shared_task(name="bookings.tasks.remind_hosts_of_pending_requests")
def remind_hosts_of_pending_requests() -> int:
    from bookings.models import BookingRequest, BookingRequestStatus
    from notifications import emails

    threshold = timezone.now() + timedelta(hours=settings.BOOKING_REQUEST_REMINDER_HOURS)
    count = 0
    for request in BookingRequest.objects.filter(
        status=BookingRequestStatus.PENDING,
        reminder_sent_at__isnull=True,
        expires_at__lte=threshold,
        expires_at__gt=timezone.now(),
    ).select_related("property", "property__host"):
        emails.send_booking_request_reminder(request)
        request.reminder_sent_at = timezone.now()
        request.save(update_fields=["reminder_sent_at", "updated_at"])
        count += 1
    return count


@shared_task(name="bookings.tasks.generate_contract", autoretry_for=(Exception,), max_retries=2)
def generate_contract(booking_id: int) -> str:
    """Contrat PDF pour les modes mensuel / annuel, stocké dans le bucket privé."""
    from bookings.models import Booking
    from bookings.services import build_contract_context

    booking = Booking.objects.select_related("property", "host", "traveler").get(pk=booking_id)
    if booking.rental_mode == "nightly":
        return ""
    html = render_to_string("contracts/lease.html", build_contract_context(booking))
    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html, base_url=settings.SITE_URL).write_pdf()
    except ImportError:  # pragma: no cover - dépendance système absente
        logger.warning("weasyprint indisponible : contrat non généré pour %s", booking_id)
        return ""
    booking.contract_pdf.save("contrat.pdf", ContentFile(pdf_bytes), save=True)
    return booking.contract_pdf.name


@shared_task(name="bookings.tasks.advance_booking_statuses")
def advance_booking_statuses() -> int:
    """Passe confirmed -> in_progress au jour d'arrivée et in_progress -> completed au départ."""
    from bookings import services
    from bookings.models import Booking, BookingStatus

    today = timezone.localdate()
    count = 0
    for booking in Booking.objects.filter(status=BookingStatus.CONFIRMED, start_date__lte=today):
        services.start_stay(booking)
        count += 1
    for booking in Booking.objects.filter(status=BookingStatus.IN_PROGRESS, end_date__lte=today):
        services.complete_stay(booking)
        count += 1
    return count
