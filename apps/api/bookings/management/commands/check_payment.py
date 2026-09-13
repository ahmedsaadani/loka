"""
Réconciliation manuelle Konnect : `manage.py check_payment <provider_ref>`.
Relit l'état du paiement via l'API Konnect et, s'il est encaissé, applique le résultat
(idempotent) comme l'aurait fait le webhook. Utile si un webhook a été perdu.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from bookings import services
from bookings.models import Payment
from bookings.payments.base import PaymentResult
from bookings.payments.konnect import KonnectError, KonnectPaymentProvider


class Command(BaseCommand):
    help = "Vérifie l'état d'un paiement Konnect et applique le résultat s'il est encaissé."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("provider_ref", help="paymentRef Konnect (Payment.provider_ref)")

    def handle(self, *args: Any, **options: Any) -> None:
        provider_ref = str(options["provider_ref"])
        provider = KonnectPaymentProvider()
        try:
            data = provider.get_payment(provider_ref)
        except KonnectError as exc:
            raise CommandError(str(exc)) from exc
        result = provider.result_from_payment(data)
        payment_status = str(data["payment"].get("status", "?"))
        self.stdout.write(
            f"Konnect {provider_ref} : status={payment_status} "
            f"amount={result.amount} {result.currency}"
        )
        if not result.succeeded:
            self.stdout.write("Paiement non encaissé : aucune modification.")
            return
        try:
            payment = services.handle_payment_result(
                PaymentResult(
                    provider_ref=provider_ref,
                    succeeded=True,
                    amount=result.amount,
                    currency=result.currency,
                    raw=result.raw,
                )
            )
        except Payment.DoesNotExist as exc:
            raise CommandError(f"Aucun Payment avec provider_ref={provider_ref}.") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Payment {payment.public_id} -> {payment.status} ; "
                f"réservation {payment.booking.public_id} -> {payment.booking.status}"
            )
        )
