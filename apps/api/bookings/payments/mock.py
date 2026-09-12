"""Prestataire mock : le checkout est une URL du front qui simule un paiement réussi ou échoué."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings

from bookings.payments.base import CheckoutSession, PaymentResult


class MockPaymentProvider:
    name = "mock"

    def create_checkout(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        description: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        provider_ref = f"mock_{uuid.uuid4().hex[:16]}"
        checkout_url = (
            f"{settings.SITE_URL}/paiement/mock?ref={provider_ref}&amount={amount}"
            f"&currency={currency}&reference={reference}"
        )
        return CheckoutSession(
            provider=self.name,
            provider_ref=provider_ref,
            checkout_url=checkout_url,
            raw={"description": description, "success_url": success_url, "cancel_url": cancel_url},
        )

    @staticmethod
    def sign(provider_ref: str, outcome: str) -> str:
        """Signature HMAC du webhook mock : impossible de forger un succès sans SECRET_KEY."""
        return hmac.new(
            settings.SECRET_KEY.encode(), f"{provider_ref}:{outcome}".encode(), hashlib.sha256
        ).hexdigest()

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> PaymentResult:
        provider_ref = str(payload.get("provider_ref", ""))
        outcome = str(payload.get("outcome", "failed"))
        signature = str(payload.get("signature", ""))
        if not hmac.compare_digest(signature, self.sign(provider_ref, outcome)):
            raise ValueError("Signature de webhook invalide.")
        return PaymentResult(
            provider_ref=provider_ref,
            succeeded=outcome == "succeeded",
            amount=Decimal(str(payload.get("amount", "0"))),
            currency=str(payload.get("currency", "TND")),
            raw=payload,
        )

    def refund(self, *, provider_ref: str, amount: Decimal) -> PaymentResult:
        return PaymentResult(
            provider_ref=f"{provider_ref}_refund", succeeded=True, amount=amount, raw={"mock": True}
        )
