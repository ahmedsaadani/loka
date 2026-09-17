import pytest
from django.urls import reverse

from accounts import services
from accounts.models import Role, User

pytestmark = pytest.mark.django_db

URL = reverse("v1:google-login")
CID = "test-client-id.apps.googleusercontent.com"


def _payload(**over):
    base = {
        "aud": CID,
        "iss": "https://accounts.google.com",
        "email_verified": "true",
        "email": "Nour.Google@example.com",
        "given_name": "Nour",
        "family_name": "Ben Salah",
    }
    base.update(over)
    return base


@pytest.fixture
def google(settings, monkeypatch):
    settings.GOOGLE_CLIENT_ID = CID

    def _set(payload):
        monkeypatch.setattr(services, "_fetch_google_payload", lambda credential: payload)

    return _set


class TestGoogleLogin:
    def test_creates_account_on_first_sign_in(self, api, google):
        google(_payload())
        res = api.post(URL, {"credential": "fake"})
        assert res.status_code == 200, res.data
        assert "access" in res.data
        user = User.objects.get(email="nour.google@example.com")
        assert user.role == Role.TRAVELER
        assert user.first_name == "Nour"
        assert not user.has_usable_password()

    def test_existing_user_logs_in_without_duplicate(self, api, google):
        User.objects.create_user(email="nour.google@example.com", password="Existant2026x")
        google(_payload())
        res = api.post(URL, {"credential": "fake"})
        assert res.status_code == 200
        assert User.objects.filter(email="nour.google@example.com").count() == 1

    def test_wrong_audience_rejected(self, api, google):
        google(_payload(aud="someone-else"))
        assert api.post(URL, {"credential": "fake"}).status_code == 400

    def test_unverified_email_rejected(self, api, google):
        google(_payload(email_verified="false"))
        assert api.post(URL, {"credential": "fake"}).status_code == 400

    def test_not_configured_rejected(self, api, settings, monkeypatch):
        settings.GOOGLE_CLIENT_ID = ""
        monkeypatch.setattr(services, "_fetch_google_payload", lambda credential: _payload())
        assert api.post(URL, {"credential": "fake"}).status_code == 400
