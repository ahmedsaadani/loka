import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from geo.factories import CityFactory
from leads.factories import LeadFactory
from leads.models import Lead
from listings.models import Property

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:lead-list")
IMPORT_URL = reverse("v1:lead-import-file")

CSV = 'source,source_url,title,price,city,phone,rooms\ntayara,https://t.tn/1,S+2 Ennasr,900,Ariana,+21620000001,S+2\nmubawab,https://m.tn/2,Studio Lac,"1 100",Tunis,,\n'


def status_url(lead):
    return reverse("v1:lead-set-status", kwargs={"public_id": lead.public_id})


class TestPermissions:
    def test_unauthenticated(self, api):
        assert api.get(LIST_URL).status_code == 401

    @pytest.mark.parametrize("fixture", ["traveler", "host"])
    def test_non_staff_forbidden(self, request, as_user, fixture):
        user = request.getfixturevalue(fixture)
        client = as_user(user)
        lead = LeadFactory()
        assert client.get(LIST_URL).status_code == 403
        assert client.post(LIST_URL, {"title": "x"}).status_code == 403
        assert (
            client.post(
                IMPORT_URL, {"file": SimpleUploadedFile("l.csv", CSV.encode())}, format="multipart"
            ).status_code
            == 403
        )
        assert client.post(status_url(lead), {"status": "contacted"}).status_code == 403


class TestCrud:
    def test_create_list_filter(self, as_user, staff):
        response = as_user(staff).post(
            LIST_URL,
            {"title": "Villa Kantaoui", "city": "Sousse", "source": "manual"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "new"
        LeadFactory(city="Ariana")
        body = as_user(staff).get(LIST_URL, {"city": "Sousse"}).json()
        assert body["count"] == 1

    def test_patch_cannot_change_status(self, as_user, staff):
        lead = LeadFactory()
        url = reverse("v1:lead-detail", kwargs={"public_id": lead.public_id})
        response = as_user(staff).patch(
            url, {"notes": "rappelé", "status": "converted"}, format="json"
        )
        assert response.status_code == 200
        lead.refresh_from_db()
        assert lead.notes == "rappelé"
        assert lead.status == "new"

    def test_assign_only_to_staff(self, as_user, staff, host):
        lead = LeadFactory()
        url = reverse("v1:lead-detail", kwargs={"public_id": lead.public_id})
        assert (
            as_user(staff).patch(url, {"assigned_to": host.email}, format="json").status_code == 400
        )
        assert (
            as_user(staff).patch(url, {"assigned_to": staff.email}, format="json").status_code
            == 200
        )


class TestStatus:
    def test_transitions(self, as_user, staff):
        lead = LeadFactory()
        client = as_user(staff)
        assert (
            client.post(
                status_url(lead), {"status": "contacted", "note": "OK tel"}, format="json"
            ).json()["status"]
            == "contacted"
        )
        assert (
            client.post(status_url(lead), {"status": "visit_scheduled"}, format="json").json()[
                "status"
            ]
            == "visit_scheduled"
        )
        invalid = client.post(status_url(lead), {"status": "new"}, format="json")
        assert invalid.status_code == 409
        lead.refresh_from_db()
        assert "OK tel" in lead.notes

    def test_invalid_status_value(self, as_user, staff):
        assert (
            as_user(staff)
            .post(status_url(LeadFactory()), {"status": "bidon"}, format="json")
            .status_code
            == 400
        )


class TestConvert:
    def test_convert_creates_draft(self, as_user, staff, host):
        lead = LeadFactory(status="contacted", raw_data={"description": "Bel appartement"})
        city = CityFactory(slug="ariana")
        url = reverse("v1:lead-convert", kwargs={"public_id": lead.public_id})
        response = as_user(staff).post(
            url, {"host_email": host.email, "city": city.slug}, format="json"
        )
        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["status"] == "draft"
        assert body["host_email"] == host.email
        prop = Property.objects.get(public_id=body["public_id"])
        assert prop.description == "Bel appartement"
        lead.refresh_from_db()
        assert lead.status == "converted"
        assert lead.converted_property == prop

    def test_convert_new_lead_forbidden(self, as_user, staff, host):
        lead = LeadFactory()
        url = reverse("v1:lead-convert", kwargs={"public_id": lead.public_id})
        response = as_user(staff).post(
            url, {"host_email": host.email, "city": CityFactory().slug}, format="json"
        )
        assert response.status_code == 409

    def test_convert_requires_host_account(self, as_user, staff, traveler):
        lead = LeadFactory(status="contacted")
        url = reverse("v1:lead-convert", kwargs={"public_id": lead.public_id})
        response = as_user(staff).post(
            url, {"host_email": traveler.email, "city": CityFactory().slug}, format="json"
        )
        assert response.status_code == 400


class TestImport:
    def test_import_csv(self, as_user, staff):
        upload = SimpleUploadedFile("leads.csv", CSV.encode(), content_type="text/csv")
        response = as_user(staff).post(IMPORT_URL, {"file": upload}, format="multipart")
        assert response.status_code == 200, response.json()
        assert response.json() == {"created": 2, "skipped": 0}
        lead = Lead.objects.get(source_url="https://m.tn/2")
        assert lead.price == 1100
        assert Lead.objects.get(source_url="https://t.tn/1").raw_data == {"rooms": "S+2"}

    def test_import_json_and_dedup(self, as_user, staff):
        LeadFactory(source_url="https://t.tn/1")
        data = [
            {"source": "tayara", "source_url": "https://t.tn/1", "title": "dup"},
            {"title": "Sans URL", "source": "facebook"},
        ]
        upload = SimpleUploadedFile(
            "leads.json", json.dumps(data).encode(), content_type="application/json"
        )
        response = as_user(staff).post(IMPORT_URL, {"file": upload}, format="multipart")
        assert response.json() == {"created": 1, "skipped": 1}

    def test_import_bad_format(self, as_user, staff):
        upload = SimpleUploadedFile(
            "leads.xlsx", b"PK\x03\x04", content_type="application/vnd.ms-excel"
        )
        assert (
            as_user(staff).post(IMPORT_URL, {"file": upload}, format="multipart").status_code == 400
        )

    def test_import_row_without_title(self, as_user, staff):
        upload = SimpleUploadedFile("leads.csv", b"title,city\n,Tunis\n", content_type="text/csv")
        assert (
            as_user(staff).post(IMPORT_URL, {"file": upload}, format="multipart").status_code == 400
        )
