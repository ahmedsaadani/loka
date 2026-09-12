import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from accounts.factories import DEFAULT_PASSWORD, TravelerFactory
from accounts.models import HostProfile, User

pytestmark = pytest.mark.django_db

REGISTER_PAYLOAD = {
    "email": "Nouveau@Loka.tn",
    "password": "un-mot-de-passe-long-42",
    "first_name": "Nour",
    "last_name": "Ben Ali",
    "role": "traveler",
}


class TestRegister:
    def test_register_traveler(self, api):
        response = api.post(reverse("v1:register"), REGISTER_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["user"]["email"] == "nouveau@loka.tn"
        assert body["user"]["role"] == "traveler"
        assert "access" in body
        assert settings.JWT_REFRESH_COOKIE_NAME in response.cookies
        cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
        assert cookie["path"] == "/api/v1/auth/"

    def test_register_host_creates_profile(self, api):
        response = api.post(
            reverse("v1:register"),
            {**REGISTER_PAYLOAD, "role": "host", "display_name": "Nour Immo"},
        )
        assert response.status_code == 201
        user = User.objects.get(email="nouveau@loka.tn")
        assert HostProfile.objects.get(user=user).display_name == "Nour Immo"

    def test_register_staff_role_refused(self, api):
        response = api.post(reverse("v1:register"), {**REGISTER_PAYLOAD, "role": "staff"})
        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_register_duplicate_email(self, api):
        TravelerFactory(email="nouveau@loka.tn")
        response = api.post(reverse("v1:register"), REGISTER_PAYLOAD)
        assert response.status_code == 400
        assert "email" in response.json()["errors"]

    def test_register_weak_password(self, api):
        response = api.post(reverse("v1:register"), {**REGISTER_PAYLOAD, "password": "12345678901"})
        assert response.status_code == 400

    def test_register_invalid_payload(self, api):
        response = api.post(reverse("v1:register"), {"email": "pas-un-email"})
        assert response.status_code == 400
        assert "password" in response.json()["errors"]


class TestLoginRefreshLogout:
    def test_login_ok(self, api, traveler):
        response = api.post(
            reverse("v1:login"), {"email": traveler.email.upper(), "password": DEFAULT_PASSWORD}
        )
        assert response.status_code == 200
        assert response.json()["user"]["public_id"] == str(traveler.public_id)
        assert settings.JWT_REFRESH_COOKIE_NAME in response.cookies

    def test_login_bad_password(self, api, traveler):
        response = api.post(reverse("v1:login"), {"email": traveler.email, "password": "faux"})
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_login_inactive_user(self, api):
        user = TravelerFactory(is_active=False)
        response = api.post(
            reverse("v1:login"), {"email": user.email, "password": DEFAULT_PASSWORD}
        )
        assert response.status_code == 401

    def test_refresh_rotates_and_blacklists(self, api, traveler):
        login = api.post(
            reverse("v1:login"), {"email": traveler.email, "password": DEFAULT_PASSWORD}
        )
        first_cookie = login.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        api.cookies[settings.JWT_REFRESH_COOKIE_NAME] = first_cookie
        refresh = api.post(reverse("v1:refresh"))
        assert refresh.status_code == 200
        assert "access" in refresh.json()
        second_cookie = refresh.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        assert second_cookie != first_cookie
        assert BlacklistedToken.objects.count() == 1
        # L'ancien refresh ne marche plus
        api.cookies[settings.JWT_REFRESH_COOKIE_NAME] = first_cookie
        reused = api.post(reverse("v1:refresh"))
        assert reused.status_code == 401
        assert reused.json()["code"] == "refresh_invalid"

    def test_refresh_without_cookie(self, api):
        response = api.post(reverse("v1:refresh"))
        assert response.status_code == 401
        assert response.json()["code"] == "refresh_missing"

    def test_logout_blacklists_and_clears_cookie(self, api, traveler):
        login = api.post(
            reverse("v1:login"), {"email": traveler.email, "password": DEFAULT_PASSWORD}
        )
        api.cookies[settings.JWT_REFRESH_COOKIE_NAME] = login.cookies[
            settings.JWT_REFRESH_COOKIE_NAME
        ].value
        response = api.post(reverse("v1:logout"))
        assert response.status_code == 204
        assert BlacklistedToken.objects.count() == 1
        assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value == ""

    def test_access_token_grants_me(self, api, traveler):
        login = api.post(
            reverse("v1:login"), {"email": traveler.email, "password": DEFAULT_PASSWORD}
        )
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        response = api.get(reverse("v1:me"))
        assert response.status_code == 200
        assert response.json()["email"] == traveler.email


class TestMe:
    def test_me_unauthenticated(self, api):
        assert api.get(reverse("v1:me")).status_code == 401

    def test_me_patch_allowed_fields_only(self, as_user, traveler):
        response = as_user(traveler).patch(
            reverse("v1:me"), {"first_name": "Zied", "role": "admin", "email": "x@y.z"}
        )
        assert response.status_code == 200
        traveler.refresh_from_db()
        assert traveler.first_name == "Zied"
        assert traveler.role == "traveler"
        assert traveler.email != "x@y.z"

    def test_me_never_exposes_password_or_iban(self, as_user, host):
        host.host_profile.bank_iban_private = "TN5910006035183598478831"
        host.host_profile.save()
        body = as_user(host).get(reverse("v1:me")).json()
        assert "password" not in body
        assert "bank_iban_private" not in body["host_profile"]
        assert body["host_profile"]["bank_details_masked"] == "TN59 **** 8831"


class TestThrottling:
    def test_login_rate_limited(self, api, traveler, monkeypatch):
        rates = {**ScopedRateThrottle.THROTTLE_RATES, "auth": "2/min"}
        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", rates)
        cache.clear()
        payload = {"email": traveler.email, "password": "faux"}
        assert api.post(reverse("v1:login"), payload).status_code == 401
        assert api.post(reverse("v1:login"), payload).status_code == 401
        response = api.post(reverse("v1:login"), payload)
        assert response.status_code == 429
        assert response.json()["code"] == "throttled"
