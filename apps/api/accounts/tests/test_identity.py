import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.factories import MINIMAL_PDF, IdentityDocumentFactory
from accounts.models import IdentityDocumentStatus
from accounts.services import approve_identity_document, reject_identity_document
from core.models import SensitiveAccessLog, StatusLog
from core.state import InvalidTransition

pytestmark = pytest.mark.django_db

LIST_URL = reverse("v1:identity-document-list")


def detail(doc, action=""):
    name = f"v1:identity-document-{action}" if action else "v1:identity-document-detail"
    return reverse(name, kwargs={"public_id": doc.public_id})


class TestUpload:
    def test_upload_pdf(self, as_user, traveler):
        upload = SimpleUploadedFile("cin.pdf", MINIMAL_PDF, content_type="application/pdf")
        response = as_user(traveler).post(
            LIST_URL, {"doc_type": "cin", "file": upload}, format="multipart"
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert "file" not in body and "url" not in body
        doc = traveler.identity_documents.get()
        assert doc.mime_type == "application/pdf"
        assert "cin.pdf" not in doc.file.name  # nom généré

    def test_upload_fake_file_rejected(self, as_user, traveler):
        upload = SimpleUploadedFile("cin.pdf", b"not a pdf at all", content_type="application/pdf")
        response = as_user(traveler).post(
            LIST_URL, {"doc_type": "cin", "file": upload}, format="multipart"
        )
        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_upload_unauthenticated(self, api):
        upload = SimpleUploadedFile("cin.pdf", MINIMAL_PDF)
        assert (
            api.post(LIST_URL, {"doc_type": "cin", "file": upload}, format="multipart").status_code
            == 401
        )

    def test_upload_bad_doc_type(self, as_user, traveler):
        upload = SimpleUploadedFile("cin.pdf", MINIMAL_PDF)
        response = as_user(traveler).post(
            LIST_URL, {"doc_type": "permis", "file": upload}, format="multipart"
        )
        assert response.status_code == 400


class TestAccess:
    def test_user_sees_only_own_documents(self, as_user, traveler):
        mine = IdentityDocumentFactory(user=traveler)
        IdentityDocumentFactory()
        body = as_user(traveler).get(LIST_URL).json()
        assert [d["public_id"] for d in body["results"]] == [str(mine.public_id)]

    def test_user_cannot_open_other_document(self, as_user, traveler):
        other = IdentityDocumentFactory()
        assert as_user(traveler).get(detail(other)).status_code == 404
        assert as_user(traveler).get(detail(other, "download")).status_code == 404

    def test_download_own_is_logged(self, as_user, traveler):
        doc = IdentityDocumentFactory(user=traveler)
        response = as_user(traveler).get(detail(doc, "download"))
        assert response.status_code == 200
        assert response.json()["expires_in"] == 300
        log = SensitiveAccessLog.objects.get()
        assert log.kind == "identity_document"
        assert log.actor == traveler
        assert log.target_id == str(doc.pk)

    def test_staff_sees_all_and_download_logged(self, as_user, staff):
        doc = IdentityDocumentFactory()
        client = as_user(staff)
        assert len(client.get(LIST_URL).json()["results"]) == 1
        assert client.get(detail(doc, "download")).status_code == 200
        assert SensitiveAccessLog.objects.filter(actor=staff).count() == 1

    def test_staff_pending_queue(self, as_user, staff):
        IdentityDocumentFactory()
        IdentityDocumentFactory(status=IdentityDocumentStatus.APPROVED)
        body = as_user(staff).get(reverse("v1:identity-document-pending")).json()
        assert body["count"] == 1
        assert body["results"][0]["user_email"]

    def test_traveler_cannot_use_staff_actions(self, as_user, traveler):
        doc = IdentityDocumentFactory(user=traveler)
        assert as_user(traveler).post(detail(doc, "approve")).status_code == 403
        assert as_user(traveler).post(detail(doc, "reject"), {"reason": "x"}).status_code == 403
        assert as_user(traveler).get(reverse("v1:identity-document-pending")).status_code == 403


class TestReview:
    def test_approve_marks_user_verified(self, as_user, staff):
        doc = IdentityDocumentFactory()
        response = as_user(staff).post(detail(doc, "approve"))
        assert response.status_code == 200
        doc.refresh_from_db()
        assert doc.status == "approved"
        assert doc.reviewed_by == staff
        assert doc.user.is_identity_verified is True
        assert StatusLog.objects.filter(to_status="approved").exists()

    def test_reject_requires_reason(self, as_user, staff):
        doc = IdentityDocumentFactory()
        assert as_user(staff).post(detail(doc, "reject"), {}).status_code == 400
        response = as_user(staff).post(detail(doc, "reject"), {"reason": "Document illisible"})
        assert response.status_code == 200
        doc.refresh_from_db()
        assert doc.status == "rejected"
        assert doc.rejection_reason == "Document illisible"
        assert doc.user.is_identity_verified is False

    def test_approve_twice_is_conflict(self, as_user, staff):
        doc = IdentityDocumentFactory()
        approve_identity_document(doc, by=staff)
        response = as_user(staff).post(detail(doc, "approve"))
        assert response.status_code == 409
        assert response.json()["code"] == "invalid_transition"

    def test_reject_then_approve_forbidden(self, staff):
        doc = IdentityDocumentFactory()
        reject_identity_document(doc, by=staff, reason="flou")
        with pytest.raises(InvalidTransition):
            approve_identity_document(doc, by=staff)
