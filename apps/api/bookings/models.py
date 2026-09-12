from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models

from core.models import PublicIdModel, TimeStampedModel
from core.storages import generated_name, private_storage
from listings.models import Property, RentalMode


class BookingRequestStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    ACCEPTED = "accepted", "Acceptée"
    DECLINED = "declined", "Refusée"
    EXPIRED = "expired", "Expirée"
    CANCELLED = "cancelled", "Annulée"


class BookingRequest(PublicIdModel, TimeStampedModel):
    """Demande de réservation d'un voyageur. Expire sans réponse de l'hôte (48 h)."""

    TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        BookingRequestStatus.PENDING: frozenset(
            {
                BookingRequestStatus.ACCEPTED,
                BookingRequestStatus.DECLINED,
                BookingRequestStatus.EXPIRED,
                BookingRequestStatus.CANCELLED,
            }
        ),
        BookingRequestStatus.ACCEPTED: frozenset(),
        BookingRequestStatus.DECLINED: frozenset(),
        BookingRequestStatus.EXPIRED: frozenset(),
        BookingRequestStatus.CANCELLED: frozenset(),
    }

    property = models.ForeignKey(
        Property, on_delete=models.PROTECT, related_name="booking_requests"
    )
    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="booking_requests"
    )
    rental_mode = models.CharField(max_length=8, choices=RentalMode.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1)
    message = models.TextField(blank=True, max_length=2000)
    status = models.CharField(
        max_length=12, choices=BookingRequestStatus.choices, default=BookingRequestStatus.PENDING
    )
    # Devis figé au moment de la demande (les prix peuvent changer ensuite).
    quoted_units = models.PositiveSmallIntegerField(default=1, help_text="Nuits ou mois")
    quoted_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quoted_subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    quoted_fee = models.DecimalField(max_digits=10, decimal_places=2)
    quoted_total = models.DecimalField(max_digits=10, decimal_places=2)
    quoted_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    expires_at = models.DateTimeField()
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "demande de réservation"
        verbose_name_plural = "demandes de réservation"
        indexes = [models.Index(fields=["status", "expires_at"])]

    def __str__(self) -> str:
        return f"Demande {self.public_id} ({self.status})"


class BookingStatus(models.TextChoices):
    AWAITING_DEPOSIT = "awaiting_deposit", "Acompte en attente"
    CONFIRMED = "confirmed", "Confirmée"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminée"
    CANCELLED = "cancelled", "Annulée"


def contract_upload_to(instance: Booking, filename: str) -> str:
    return generated_name(f"contracts/{instance.pk}", filename, forced_ext="pdf")


class Booking(PublicIdModel, TimeStampedModel):
    TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        BookingStatus.AWAITING_DEPOSIT: frozenset(
            {BookingStatus.CONFIRMED, BookingStatus.CANCELLED}
        ),
        BookingStatus.CONFIRMED: frozenset({BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED}),
        BookingStatus.IN_PROGRESS: frozenset({BookingStatus.COMPLETED}),
        BookingStatus.COMPLETED: frozenset(),
        BookingStatus.CANCELLED: frozenset(),
    }

    request = models.OneToOneField(BookingRequest, on_delete=models.PROTECT, related_name="booking")
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="bookings")
    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="host_bookings"
    )
    rental_mode = models.CharField(max_length=8, choices=RentalMode.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    fee_payer = models.CharField(max_length=8, help_text="traveler | host")
    status = models.CharField(
        max_length=20, choices=BookingStatus.choices, default=BookingStatus.AWAITING_DEPOSIT
    )
    contract_pdf = models.FileField(
        upload_to=contract_upload_to, storage=private_storage, null=True, blank=True
    )
    cancellation_reason = models.CharField(max_length=255, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "réservation"

    def __str__(self) -> str:
        return f"Réservation {self.public_id} ({self.status})"


class PaymentKind(models.TextChoices):
    DEPOSIT = "deposit", "Acompte"
    BALANCE = "balance", "Solde"
    REFUND = "refund", "Remboursement"


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", "Initié"
    SUCCEEDED = "succeeded", "Réussi"
    FAILED = "failed", "Échoué"
    REFUNDED = "refunded", "Remboursé"


class Payment(PublicIdModel, TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=24)
    provider_ref = models.CharField(max_length=128, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="TND")
    kind = models.CharField(max_length=8, choices=PaymentKind.choices)
    status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED
    )
    checkout_url = models.URLField(max_length=500, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "paiement"

    def __str__(self) -> str:
        return f"{self.kind} {self.amount} {self.currency} ({self.status})"
