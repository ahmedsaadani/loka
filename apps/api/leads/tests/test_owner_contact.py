import pytest
from django.core import mail
from django.urls import reverse

from accounts.factories import HostFactory
from leads.models import Lead, LeadSource, LeadStatus

pytestmark = pytest.mark.django_db

URL = reverse("v1:owner-contact")
PAYLOAD = {
    "name": "Mounir Ben Ali",
    "phone": "+216 22 333 444",
    "city": "Ariana",
    "property_type": "apartment",
    "message": "S+2 à Ennasr, disponible en octobre.",
}


class TestOwnerContact:
    def test_creates_manual_lead_and_notifies_staff(self, api, staff, admin):
        HostFactory()  # ne doit pas être notifié
        response = api.post(URL, PAYLOAD)
        assert response.status_code == 201, response.data
        lead = Lead.objects.get()
        assert lead.source == LeadSource.MANUAL
        assert lead.status == LeadStatus.NEW
        assert lead.city == "Ariana"
        assert lead.phone == "+216 22 333 444"
        assert lead.title == "Appartement à Ariana — Mounir Ben Ali"
        assert lead.raw_data["channel"] == "owner_contact_form"
        assert lead.raw_data["name"] == "Mounir Ben Ali"
        assert lead.notes == PAYLOAD["message"]
        recipients = sorted(m.to[0] for m in mail.outbox)
        assert recipients == sorted([staff.email, admin.email])
        assert "Mounir Ben Ali" in mail.outbox[0].body
        assert "+216 22 333 444" in mail.outbox[0].body

    def test_honeypot_filled_is_ignored_silently(self, api, staff):
        response = api.post(URL, {**PAYLOAD, "website": "http://spam.example"})
        assert response.status_code == 201
        assert Lead.objects.count() == 0
        assert mail.outbox == []

    @pytest.mark.parametrize(
        "field, value",
        [("phone", "abc"), ("phone", ""), ("name", ""), ("city", ""), ("property_type", "castle")],
    )
    def test_validation_errors(self, api, field, value):
        response = api.post(URL, {**PAYLOAD, field: value})
        assert response.status_code == 400
        assert field in response.data.get("errors", response.data)

    def test_no_staff_no_email_but_lead_kept(self, api):
        response = api.post(URL, PAYLOAD)
        assert response.status_code == 201
        assert Lead.objects.count() == 1
        assert mail.outbox == []

    def test_throttled_after_five_submissions(self, api, monkeypatch):
        from django.core.cache import cache
        from rest_framework.throttling import ScopedRateThrottle

        cache.clear()  # historique de throttle laissé par les tests précédents
        monkeypatch.setattr(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {**ScopedRateThrottle.THROTTLE_RATES, "owner_contact": "2/hour"},
        )
        assert api.post(URL, PAYLOAD).status_code == 201
        assert api.post(URL, PAYLOAD).status_code == 201
        assert api.post(URL, PAYLOAD).status_code == 429

    def test_staff_list_shows_the_lead(self, api, as_user, staff):
        api.post(URL, PAYLOAD)
        response = as_user(staff).get(reverse("v1:lead-list"))
        assert response.status_code == 200
        assert response.data["results"][0]["source"] == "manual"
