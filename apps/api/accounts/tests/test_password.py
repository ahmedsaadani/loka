import re

import pytest
from django.core import mail
from django.urls import reverse

from accounts.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "nouveau-mot-de-passe-987"


def extract_reset_parts(body: str) -> tuple[str, str]:
    match = re.search(r"/reinitialisation/([^/\s]+)/([^/\s\"<]+)", body)
    assert match, body
    return match.group(1), match.group(2)


class TestPasswordReset:
    def test_request_sends_email_for_existing_user(self, api, traveler):
        response = api.post(reverse("v1:password-reset"), {"email": traveler.email.upper()})
        assert response.status_code == 202
        assert len(mail.outbox) == 1
        assert traveler.email in mail.outbox[0].to
        assert "/reinitialisation/" in mail.outbox[0].alternatives[0][0]

    def test_request_unknown_email_same_response_no_email(self, api):
        response = api.post(reverse("v1:password-reset"), {"email": "inconnu@loka.tn"})
        assert response.status_code == 202
        assert len(mail.outbox) == 0

    def test_request_invalid_payload(self, api):
        assert api.post(reverse("v1:password-reset"), {"email": "x"}).status_code == 400

    def test_confirm_resets_password_and_logs_in(self, api, traveler):
        api.post(reverse("v1:password-reset"), {"email": traveler.email})
        uid, token = extract_reset_parts(mail.outbox[0].alternatives[0][0])
        response = api.post(
            reverse("v1:password-reset-confirm"),
            {"uid": uid, "token": token, "password": NEW_PASSWORD},
        )
        assert response.status_code == 200
        assert "access" in response.json()
        traveler.refresh_from_db()
        assert traveler.check_password(NEW_PASSWORD)
        # Le lien est à usage unique
        again = api.post(
            reverse("v1:password-reset-confirm"),
            {"uid": uid, "token": token, "password": NEW_PASSWORD},
        )
        assert again.status_code == 400

    def test_confirm_bad_token(self, api, traveler):
        response = api.post(
            reverse("v1:password-reset-confirm"),
            {"uid": "abc", "token": "bad", "password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert "token" in response.json()["errors"]

    def test_confirm_weak_password(self, api, traveler):
        api.post(reverse("v1:password-reset"), {"email": traveler.email})
        uid, token = extract_reset_parts(mail.outbox[0].alternatives[0][0])
        response = api.post(
            reverse("v1:password-reset-confirm"),
            {"uid": uid, "token": token, "password": "12345678901"},
        )
        assert response.status_code == 400


class TestPasswordChange:
    def test_change_ok(self, as_user, traveler):
        response = as_user(traveler).post(
            reverse("v1:password-change"),
            {"current_password": DEFAULT_PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 204
        traveler.refresh_from_db()
        assert traveler.check_password(NEW_PASSWORD)

    def test_change_wrong_current(self, as_user, traveler):
        response = as_user(traveler).post(
            reverse("v1:password-change"),
            {"current_password": "faux", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert "current_password" in response.json()["errors"]

    def test_change_unauthenticated(self, api):
        assert api.post(reverse("v1:password-change"), {}).status_code == 401
