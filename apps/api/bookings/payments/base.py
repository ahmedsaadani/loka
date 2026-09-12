"""
Abstraction du prestataire de paiement. Une implémentation mock au MVP ;
Konnect / ClicToPay / Flouci implémenteront la même interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from django.conf import settings


@dataclass(frozen=True)
class CheckoutSession:
    provider: str
    provider_ref: str
    checkout_url: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentResult:
    provider_ref: str
    succeeded: bool
    amount: Decimal
    currency: str = "TND"
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(Protocol):
    name: str

    def create_checkout(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        description: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession: ...

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> PaymentResult: ...

    def refund(self, *, provider_ref: str, amount: Decimal) -> PaymentResult: ...


def get_payment_provider() -> PaymentProvider:
    name = settings.PAYMENT_PROVIDER
    if name == "mock":
        from bookings.payments.mock import MockPaymentProvider

        return MockPaymentProvider()
    raise NotImplementedError(f"Prestataire de paiement non implémenté : {name}")
