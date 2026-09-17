import pytest
from django.urls import reverse

from accounts import services
from accounts.models import Role, User

pytestmark = pytest.mark.django_db

URL = reverse("v1:facebook-login")


def _payload(**over):
    base = {
        "email": "Yassine.FB@example.com",
        "first_name": "Yassine",
        "last_name": "Trabelsi",
    }
    base.update(over)
    return base


@pytest.fixture
def facebook(settings, monkeypatch):
    settings.FACEBOOK_APP_ID = "1070070768956722"
    settings.FACEBOOK_APP_SECRET = "test-secret"

    def _set(payload):
        monkeypatch.setattr(services, "_fetch_facebook_payload", lambda access_token: payload)

    return _set


class TestFacebookLogin:
    def test_creates_account_on_first_sign_in(self, api, facebook):
        facebook(_payload())
        res = api.post(URL, {"access_token": "fake"})
        assert res.status_code == 200, res.data
        assert "access" in res.data
        user = User.objects.get(email="yassine.fb@example.com")
        assert user.role == Role.TRAVELER
        assert user.first_name == "Yassine"
        assert not user.has_usable_password()

    def test_existing_user_logs_in_without_duplicate(self, api, facebook):
        User.objects.create_user(email="yassine.fb@example.com", password="Existant2026x")
        facebook(_payload())
        res = api.post(URL, {"access_token": "fake"})
        assert res.status_code == 200
        assert User.objects.filter(email="yassine.fb@example.com").count() == 1

    def test_missing_email_rejected(self, api, facebook):
        facebook(_payload(email=""))
        assert api.post(URL, {"access_token": "fake"}).status_code == 400

    def test_not_configured_rejected(self, api, settings, monkeypatch):
        settings.FACEBOOK_APP_ID = ""
        settings.FACEBOOK_APP_SECRET = ""
        monkeypatch.setattr(services, "_fetch_facebook_payload", lambda access_token: _payload())
        assert api.post(URL, {"access_token": "fake"}).status_code == 400
