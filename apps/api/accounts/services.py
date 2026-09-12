from __future__ import annotations

import logging

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    HostProfile,
    IdentityDocument,
    IdentityDocumentStatus,
    Role,
    User,
)
from core.state import transition
from core.uploads import validate_document

audit_logger = logging.getLogger("loka.audit")


@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    role: str = Role.TRAVELER,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    display_name: str = "",
) -> User:
    """Inscription publique : seuls les rôles voyageur et hôte sont autorisés."""
    if role not in {Role.TRAVELER, Role.HOST}:
        raise ValueError("Rôle non autorisé à l'inscription.")
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
    )
    if role == Role.HOST:
        HostProfile.objects.create(user=user, display_name=display_name or user.full_name)
    return user


def ensure_host_profile(user: User) -> HostProfile:
    profile, _ = HostProfile.objects.get_or_create(
        user=user, defaults={"display_name": user.full_name}
    )
    return profile


@transaction.atomic
def submit_identity_document(
    user: User, *, doc_type: str, upload: UploadedFile
) -> IdentityDocument:
    mime = validate_document(upload)
    document = IdentityDocument(user=user, doc_type=doc_type, mime_type=mime)
    document.file.save(upload.name or "document", upload, save=False)
    document.save()
    audit_logger.info("identity_document_submitted user=%s doc=%s", user.pk, document.pk)
    return document


@transaction.atomic
def approve_identity_document(document: IdentityDocument, *, by: User) -> IdentityDocument:
    transition(
        document,
        IdentityDocumentStatus.APPROVED,
        actor=by,
        extra_fields={"reviewed_by": by, "reviewed_at": timezone.now(), "rejection_reason": ""},
    )
    User.objects.filter(pk=document.user_id).update(is_identity_verified=True)
    document.user.is_identity_verified = True
    return document


@transaction.atomic
def reject_identity_document(
    document: IdentityDocument, *, by: User, reason: str
) -> IdentityDocument:
    transition(
        document,
        IdentityDocumentStatus.REJECTED,
        actor=by,
        note=reason,
        extra_fields={"reviewed_by": by, "reviewed_at": timezone.now(), "rejection_reason": reason},
    )
    return document
