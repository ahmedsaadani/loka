import pytest
from django.urls import reverse

from core.models import StatusLog
from core.state import InvalidTransition, can_transition, transition
from leads.factories import LeadFactory
from leads.models import LeadStatus

pytestmark = pytest.mark.django_db


class TestStateMachine:
    def test_valid_transition_updates_status_and_logs(self, staff):
        lead = LeadFactory()
        transition(lead, LeadStatus.CONTACTED, actor=staff, note="appelé")
        lead.refresh_from_db()
        assert lead.status == LeadStatus.CONTACTED
        log = StatusLog.objects.get()
        assert (log.from_status, log.to_status, log.actor, log.note) == (
            "new",
            "contacted",
            staff,
            "appelé",
        )

    def test_invalid_transition_raises_and_keeps_status(self):
        lead = LeadFactory()
        with pytest.raises(InvalidTransition):
            transition(lead, LeadStatus.CONVERTED)
        lead.refresh_from_db()
        assert lead.status == LeadStatus.NEW
        assert StatusLog.objects.count() == 0

    def test_unknown_status_is_invalid(self):
        lead = LeadFactory()
        assert not can_transition(lead, "nope")

    def test_extra_fields_are_saved(self, staff):
        lead = LeadFactory()
        transition(lead, LeadStatus.REJECTED, actor=staff, extra_fields={"notes": "hors zone"})
        lead.refresh_from_db()
        assert lead.notes == "hors zone"


class TestHealthAndHeaders:
    def test_health(self, api):
        response = api.get(reverse("v1:health"))
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}

    def test_security_headers_present(self, api):
        response = api.get(reverse("v1:health"))
        assert "Content-Security-Policy" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_error_format_not_found(self, api):
        response = api.get("/api/v1/listings/properties/inexistant/")
        assert response.status_code == 404
        assert response.json() == {"detail": "Introuvable.", "code": "not_found"}

    def test_error_format_unauthenticated(self, api):
        response = api.get(reverse("v1:me"))
        assert response.status_code == 401
        body = response.json()
        assert set(body) == {"detail", "code"}
