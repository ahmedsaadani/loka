"""Tests du prestataire Konnect : HTTP mocké, réponses enregistrées dans fixtures/konnect."""

from __future__ import annotations

import io
import json
import urllib.error
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse

from bookings.factories import PaymentFactory
from bookings.models import BookingStatus, PaymentStatus
from bookings.payments.base import get_payment_provider
from bookings.payments.konnect import (
    PRODUCTION_BASE_URL,
    SANDBOX_BASE_URL,
    KonnectError,
    KonnectPaymentProvider,
    millimes_to_tnd,
    tnd_to_millimes,
)

FIXTURES = Path(__file__).parent / "fixtures" / "konnect"
REF = "66f0a1b2c3d4e5f6a7b8c9d0"
TOKEN = "webhook-token-de-test"
KONNECT_SETTINGS = {
    "PAYMENT_PROVIDER": "konnect",
    "KONNECT_API_KEY": "sk_test_123",
    "KONNECT_WALLET_ID": "wallet_abc",
    "KONNECT_SANDBOX": True,
    "KONNECT_WEBHOOK_URL": "https://api.loka.tn/api/v1/bookings/webhooks/konnect/",
    "KONNECT_WEBHOOK_TOKEN": TOKEN,
    "KONNECT_CHECKOUT_LIFESPAN_MINUTES": 30,
}


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fake_response(body: bytes, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = body
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def http_error(status: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", status, "err", {}, io.BytesIO(body))


@pytest.fixture
def konnect_settings():
    with override_settings(**KONNECT_SETTINGS):
        yield


@pytest.fixture
def provider(konnect_settings):
    return KonnectPaymentProvider()


# ----------------------------------------------------------------- montants


class TestMillimes:
    def test_tnd_to_millimes(self):
        assert tnd_to_millimes(Decimal("118.80")) == 118800
        assert tnd_to_millimes(Decimal("850")) == 850000
        assert tnd_to_millimes(Decimal("0.001")) == 1

    def test_rejects_non_integer_millimes(self):
        with pytest.raises(ValueError):
            tnd_to_millimes(Decimal("0.0005"))

    def test_rejects_non_positive(self):
        with pytest.raises(ValueError):
            tnd_to_millimes(Decimal("0"))

    def test_millimes_to_tnd(self):
        assert millimes_to_tnd(118800) == Decimal("118.80")
        assert millimes_to_tnd(1) == Decimal("0.001")


# ----------------------------------------------------------------- configuration


class TestConfiguration:
    def test_factory_returns_konnect(self, konnect_settings):
        assert isinstance(get_payment_provider(), KonnectPaymentProvider)

    @override_settings(**{**KONNECT_SETTINGS, "KONNECT_API_KEY": ""})
    def test_missing_api_key(self):
        with pytest.raises(ImproperlyConfigured):
            KonnectPaymentProvider()

    @override_settings(**{**KONNECT_SETTINGS, "KONNECT_WALLET_ID": ""})
    def test_missing_wallet_id(self):
        with pytest.raises(ImproperlyConfigured):
            KonnectPaymentProvider()

    def test_base_url_sandbox_vs_production(self, konnect_settings):
        assert KonnectPaymentProvider().base_url == SANDBOX_BASE_URL
        assert KonnectPaymentProvider(sandbox=False).base_url == PRODUCTION_BASE_URL
        with override_settings(KONNECT_SANDBOX=False):
            assert KonnectPaymentProvider().base_url == PRODUCTION_BASE_URL

    def test_webhook_url_includes_token(self, konnect_settings):
        assert KonnectPaymentProvider.webhook_url() == (
            f"https://api.loka.tn/api/v1/bookings/webhooks/konnect/?token={TOKEN}"
        )


# ----------------------------------------------------------------- create_checkout


class TestCreateCheckout:
    def test_request_and_mapping(self, provider):
        with patch(
            "urllib.request.urlopen", return_value=fake_response(fixture("init_payment.json"))
        ) as urlopen:
            session = provider.create_checkout(
                amount=Decimal("118.80"),
                currency="TND",
                reference="order-123",
                description="Acompte Loka - Studio",
                success_url="https://loka.tn/ok",
                cancel_url="https://loka.tn/ko",
                email="lea@example.com",
                phone_number="22123456",
            )
        request = urlopen.call_args.args[0]
        assert urlopen.call_args.kwargs["timeout"] == 15.0
        assert request.full_url == f"{SANDBOX_BASE_URL}/payments/init-payment"
        assert request.get_method() == "POST"
        assert request.get_header("X-api-key") == "sk_test_123"
        assert request.get_header("Content-type") == "application/json"
        body = json.loads(request.data)
        assert body == {
            "receiverWalletId": "wallet_abc",
            "token": "TND",
            "amount": 118800,
            "type": "immediate",
            "description": "Acompte Loka - Studio",
            "acceptedPaymentMethods": ["wallet", "bank_card", "e-DINAR"],
            "lifespan": 30,
            "checkoutForm": False,
            "addPaymentFeesToAmount": False,
            "orderId": "order-123",
            "webhook": f"https://api.loka.tn/api/v1/bookings/webhooks/konnect/?token={TOKEN}",
            "successUrl": "https://loka.tn/ok",
            "failUrl": "https://loka.tn/ko",
            "theme": "light",
            "email": "lea@example.com",
            "phoneNumber": "22123456",
        }
        assert session.provider == "konnect"
        assert session.provider_ref == REF
        assert session.checkout_url.startswith("https://gateway.sandbox.konnect.network/pay")
        assert session.raw["paymentRef"] == REF

    def test_production_url(self, konnect_settings):
        provider = KonnectPaymentProvider(sandbox=False)
        with patch(
            "urllib.request.urlopen", return_value=fake_response(fixture("init_payment.json"))
        ) as urlopen:
            provider.create_checkout(
                amount=Decimal("10"),
                currency="TND",
                reference="r",
                description="d",
                success_url="https://a",
                cancel_url="https://b",
            )
        assert urlopen.call_args.args[0].full_url == f"{PRODUCTION_BASE_URL}/payments/init-payment"

    def test_rejects_non_tnd(self, provider):
        with pytest.raises(ValueError):
            provider.create_checkout(
                amount=Decimal("10"),
                currency="EUR",
                reference="r",
                description="d",
                success_url="https://a",
                cancel_url="https://b",
            )

    def test_401_raises_konnect_error(self, provider):
        with (
            patch("urllib.request.urlopen", side_effect=http_error(401, fixture("error_401.json"))),
            pytest.raises(KonnectError) as excinfo,
        ):
            provider.create_checkout(
                amount=Decimal("10"),
                currency="TND",
                reference="r",
                description="d",
                success_url="https://a",
                cancel_url="https://b",
            )
        assert excinfo.value.status_code == 401
        assert "invalid or missing API key" in excinfo.value.body
        assert "sk_test_123" not in str(excinfo.value)

    def test_network_error(self, provider):
        with (
            patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")),
            pytest.raises(KonnectError),
        ):
            provider.get_payment(REF)


# ----------------------------------------------------------------- parse_webhook


class TestParseWebhook:
    def test_completed(self, provider):
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_completed.json")),
        ) as urlopen:
            result = provider.parse_webhook({"payment_ref": REF}, {})
        request = urlopen.call_args.args[0]
        assert request.full_url == f"{SANDBOX_BASE_URL}/payments/{REF}"
        assert request.get_method() == "GET"
        assert request.get_header("X-api-key") == "sk_test_123"
        assert result.succeeded is True
        assert result.provider_ref == REF
        assert result.amount == Decimal("118.80")
        assert result.currency == "TND"
        assert result.raw["payment"]["status"] == "completed"

    def test_pending(self, provider):
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_pending.json")),
        ):
            result = provider.parse_webhook({"payment_ref": REF}, {})
        assert result.succeeded is False
        assert result.amount == Decimal("118.80")

    def test_missing_ref(self, provider):
        with pytest.raises(ValueError):
            provider.parse_webhook({}, {})

    def test_refund_not_implemented(self, provider):
        with pytest.raises(NotImplementedError):
            provider.refund(provider_ref=REF, amount=Decimal("10"))


# ----------------------------------------------------------------- webhook view


@pytest.mark.django_db
class TestWebhookView:
    url = reverse("v1:konnect-webhook")

    def test_token_mismatch(self, api, konnect_settings):
        with patch("urllib.request.urlopen") as urlopen:
            response = api.get(self.url, {"payment_ref": REF, "token": "faux"})
        assert response.status_code == 403
        urlopen.assert_not_called()

    def test_missing_token_setting_rejects(self, api):
        with override_settings(**{**KONNECT_SETTINGS, "KONNECT_WEBHOOK_TOKEN": ""}):
            response = api.get(self.url, {"payment_ref": REF, "token": ""})
        assert response.status_code == 403

    def test_disabled_when_provider_is_mock(self, api):
        response = api.get(self.url, {"payment_ref": REF, "token": TOKEN})
        assert response.status_code == 403

    def test_unknown_ref(self, api, konnect_settings):
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_completed.json")),
        ):
            response = api.get(self.url, {"payment_ref": REF, "token": TOKEN})
        assert response.status_code == 404

    def test_completed_confirms_booking(self, api, konnect_settings):
        payment = PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_completed.json")),
        ):
            response = api.get(self.url, {"payment_ref": REF, "token": TOKEN})
        assert response.status_code == 200, response.json()
        assert response.json() == {"status": "succeeded"}
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.booking.status == BookingStatus.CONFIRMED

    def test_post_json_body(self, api, konnect_settings):
        payment = PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_completed.json")),
        ):
            response = api.post(f"{self.url}?token={TOKEN}", {"payment_ref": REF}, format="json")
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_pending_marks_failed_without_confirming(self, api, konnect_settings):
        payment = PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_pending.json")),
        ):
            response = api.get(self.url, {"payment_ref": REF, "token": TOKEN})
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.booking.status == BookingStatus.AWAITING_DEPOSIT

    def test_konnect_unreachable_returns_502(self, api, konnect_settings):
        PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        with patch("urllib.request.urlopen", side_effect=http_error(500, b"boom")):
            response = api.get(self.url, {"payment_ref": REF, "token": TOKEN})
        assert response.status_code == 502

    def test_missing_payment_ref(self, api, konnect_settings):
        response = api.get(self.url, {"token": TOKEN})
        assert response.status_code == 400


# ----------------------------------------------------------------- commande check_payment


@pytest.mark.django_db
class TestCheckPaymentCommand:
    def test_completed_applies_result(self, konnect_settings):
        payment = PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        out = io.StringIO()
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_completed.json")),
        ):
            call_command("check_payment", REF, stdout=out)
        assert "status=completed" in out.getvalue()
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.booking.status == BookingStatus.CONFIRMED

    def test_pending_changes_nothing(self, konnect_settings):
        payment = PaymentFactory(provider="konnect", provider_ref=REF, amount=Decimal("118.80"))
        out = io.StringIO()
        with patch(
            "urllib.request.urlopen",
            return_value=fake_response(fixture("get_payment_pending.json")),
        ):
            call_command("check_payment", REF, stdout=out)
        assert "status=pending" in out.getvalue()
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.INITIATED

    def test_unknown_ref(self, konnect_settings):
        with (
            patch(
                "urllib.request.urlopen",
                return_value=fake_response(fixture("get_payment_completed.json")),
            ),
            pytest.raises(CommandError),
        ):
            call_command("check_payment", REF)

    def test_konnect_error(self, konnect_settings):
        with (
            patch("urllib.request.urlopen", side_effect=http_error(401, fixture("error_401.json"))),
            pytest.raises(CommandError),
        ):
            call_command("check_payment", REF)
