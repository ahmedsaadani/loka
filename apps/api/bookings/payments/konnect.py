"""
Prestataire Konnect (passerelle de paiement tunisienne, https://konnect.network).

Implémentation basée sur la documentation publique de l'API v2 :
- `POST /payments/init-payment` crée un paiement et renvoie `payUrl` + `paymentRef` ;
- `GET /payments/{paymentRef}` renvoie l'état du paiement ;
- le webhook est un simple `GET <webhook>?payment_ref=...` sans signature connue.

Montants : Konnect travaille en millimes (1 TND = 1000 millimes), Loka en TND décimaux.
Voir docs/payments.md et ADR 0008.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from bookings.payments.base import CheckoutSession, PaymentResult

logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://api.preprod.konnect.network/api/v2"
PRODUCTION_BASE_URL = "https://api.konnect.network/api/v2"
MILLIMES_PER_TND = Decimal("1000")
# Seul `completed` vaut encaissement. `pending`, `expired`, `failed`, `unpaid`... ne le sont pas.
STATUS_COMPLETED = "completed"
ACCEPTED_PAYMENT_METHODS = ["wallet", "bank_card", "e-DINAR"]
REQUEST_TIMEOUT_SECONDS = 15.0
BODY_EXCERPT_LENGTH = 300


class KonnectError(Exception):
    """Réponse non 2xx ou injoignable de l'API Konnect. Ne contient jamais la clé API."""

    def __init__(self, message: str, *, status_code: int | None = None, body: str = "") -> None:
        self.status_code = status_code
        self.body = body[:BODY_EXCERPT_LENGTH]
        detail = f"{message} (HTTP {status_code})" if status_code is not None else message
        if self.body:
            detail = f"{detail} : {self.body}"
        super().__init__(detail)


def tnd_to_millimes(amount: Decimal) -> int:
    """118.80 TND -> 118800 millimes. Refuse les montants non entiers en millimes ou <= 0."""
    millimes = amount * MILLIMES_PER_TND
    if millimes != millimes.to_integral_value():
        raise ValueError(f"Montant non représentable en millimes : {amount} TND")
    if millimes <= 0:
        raise ValueError(f"Montant invalide pour Konnect : {amount} TND")
    return int(millimes)


def millimes_to_tnd(millimes: int) -> Decimal:
    """118800 millimes -> Decimal('118.800') (quantifié au millime, comparable à 118.80)."""
    return (Decimal(millimes) / MILLIMES_PER_TND).quantize(Decimal("0.001"))


class KonnectPaymentProvider:
    name = "konnect"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        wallet_id: str | None = None,
        sandbox: bool | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.KONNECT_API_KEY
        self.wallet_id = wallet_id if wallet_id is not None else settings.KONNECT_WALLET_ID
        self.sandbox = sandbox if sandbox is not None else settings.KONNECT_SANDBOX
        self.timeout = timeout
        if not self.api_key or not self.wallet_id:
            raise ImproperlyConfigured(
                "KONNECT_API_KEY et KONNECT_WALLET_ID sont requis quand PAYMENT_PROVIDER=konnect."
            )

    @property
    def base_url(self) -> str:
        return SANDBOX_BASE_URL if self.sandbox else PRODUCTION_BASE_URL

    @staticmethod
    def webhook_url() -> str:
        """URL de webhook déclarée à Konnect, avec le jeton secret en query string."""
        url = str(settings.KONNECT_WEBHOOK_URL)
        token = str(settings.KONNECT_WEBHOOK_TOKEN)
        if not token:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{urllib.parse.urlencode({'token': token})}"

    # ------------------------------------------------------------- HTTP

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"x-api-key": self.api_key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310
        logger.info("konnect_request method=%s path=%s", method, path)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310  # nosec B310 - URL https fixée par base_url
                raw = response.read().decode("utf-8", errors="replace")
                status_code = int(response.status)
        except urllib.error.HTTPError as exc:
            excerpt = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise KonnectError(
                f"Konnect a répondu une erreur sur {method} {path}",
                status_code=exc.code,
                body=excerpt,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise KonnectError(f"Konnect injoignable sur {method} {path} : {exc}") from exc
        if not 200 <= status_code < 300:
            raise KonnectError(
                f"Réponse inattendue de Konnect sur {method} {path}",
                status_code=status_code,
                body=raw,
            )
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise KonnectError(
                f"Réponse Konnect non JSON sur {method} {path}", status_code=status_code, body=raw
            ) from exc
        if not isinstance(parsed, dict):
            raise KonnectError(
                f"Réponse Konnect inattendue sur {method} {path}", status_code=status_code, body=raw
            )
        return parsed

    # ------------------------------------------------------------- PaymentProvider

    def create_checkout(
        self,
        *,
        amount: Decimal,
        currency: str,
        reference: str,
        description: str,
        success_url: str,
        cancel_url: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        phone_number: str = "",
    ) -> CheckoutSession:
        if currency != "TND":
            raise ValueError(f"Konnect n'accepte que le TND (reçu : {currency}).")
        body: dict[str, Any] = {
            "receiverWalletId": self.wallet_id,
            "token": "TND",  # nosec B105 - code devise, pas un secret
            "amount": tnd_to_millimes(amount),
            "type": "immediate",
            "description": description,
            "acceptedPaymentMethods": ACCEPTED_PAYMENT_METHODS,
            "lifespan": int(settings.KONNECT_CHECKOUT_LIFESPAN_MINUTES),
            "checkoutForm": False,
            "addPaymentFeesToAmount": False,
            "orderId": reference,
            "webhook": self.webhook_url(),
            "successUrl": success_url,
            "failUrl": cancel_url,
            "theme": "light",
        }
        optional = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "phoneNumber": phone_number,
        }
        body.update({key: value for key, value in optional.items() if value})
        response = self._request("POST", "/payments/init-payment", body)
        pay_url = response.get("payUrl")
        payment_ref = response.get("paymentRef")
        if not pay_url or not payment_ref:
            raise KonnectError(
                "Réponse init-payment sans payUrl/paymentRef", body=json.dumps(response)
            )
        return CheckoutSession(
            provider=self.name,
            provider_ref=str(payment_ref),
            checkout_url=str(pay_url),
            raw=response,
        )

    def get_payment(self, payment_ref: str) -> dict[str, Any]:
        """État brut d'un paiement (`{"payment": {...}}`). Source de vérité pour le webhook."""
        if not payment_ref:
            raise ValueError("payment_ref manquant.")
        return self._request("GET", f"/payments/{urllib.parse.quote(payment_ref, safe='')}")

    def result_from_payment(self, data: dict[str, Any]) -> PaymentResult:
        """Convertit la réponse de `GET /payments/{ref}` en PaymentResult."""
        payment = data.get("payment")
        if not isinstance(payment, dict):
            raise KonnectError("Réponse Konnect sans objet `payment`", body=json.dumps(data))
        payment_ref = str(payment.get("id") or payment.get("paymentRef") or "")
        if not payment_ref:
            raise KonnectError(
                "Réponse Konnect sans identifiant de paiement", body=json.dumps(data)
            )
        amount_millimes = int(payment.get("amount") or 0)
        return PaymentResult(
            provider_ref=payment_ref,
            succeeded=str(payment.get("status", "")).lower() == STATUS_COMPLETED,
            amount=millimes_to_tnd(amount_millimes),
            currency=str(payment.get("token") or "TND"),
            raw=data,
        )

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> PaymentResult:
        """
        Le webhook Konnect ne porte qu'un `payment_ref` et n'est pas signé : on ne lui fait
        jamais confiance. L'état réel est relu via `GET /payments/{ref}` avec la clé API.

        TODO(konnect): confirmer avec le support Konnect s'il existe une signature de webhook ;
        en attendant, la vérification se fait par lecture de l'API.
        """
        payment_ref = str(payload.get("payment_ref") or payload.get("paymentRef") or "")
        if not payment_ref:
            raise ValueError("Webhook Konnect sans payment_ref.")
        data = self.get_payment(payment_ref)
        result = self.result_from_payment(data)
        # On répond avec la référence reçue : c'est celle stockée dans Payment.provider_ref.
        return PaymentResult(
            provider_ref=payment_ref,
            succeeded=result.succeeded,
            amount=result.amount,
            currency=result.currency,
            raw=result.raw,
        )

    def refund(self, *, provider_ref: str, amount: Decimal) -> PaymentResult:
        # TODO(konnect): l'API publique ne documente pas de remboursement. À implémenter quand
        # Konnect fournira un endpoint ; d'ici là, remboursement manuel depuis le tableau de bord.
        raise NotImplementedError(
            "Konnect ne propose pas de remboursement par API : rembourser manuellement depuis "
            f"le tableau de bord Konnect (paiement {provider_ref}, {amount} TND)."
        )
