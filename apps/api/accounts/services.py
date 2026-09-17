from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
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

INVALID_LINK_MESSAGE = "Lien invalide ou expiré."
INCORRECT_CURRENT_MESSAGE = "Mot de passe actuel incorrect."


def request_password_reset(email: str) -> None:
    """Envoie le lien si le compte existe. Réponse identique sinon (pas d'énumération)."""
    from django.conf import settings
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    from notifications import emails

    user = User.objects.filter(email=email.lower().strip(), is_active=True).first()
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    emails.send_password_reset(user, f"{settings.PASSWORD_RESET_URL}/{uid}/{token}")
    audit_logger.info("password_reset_requested user=%s", user.pk)


def confirm_password_reset(*, uid: str, token: str, password: str) -> User:
    from django.contrib.auth.password_validation import validate_password
    from django.contrib.auth.tokens import default_token_generator
    from django.core.exceptions import ValidationError
    from django.utils.http import urlsafe_base64_decode

    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uid).decode(), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise ValidationError({"token": INVALID_LINK_MESSAGE}) from exc
    if not default_token_generator.check_token(user, token):
        raise ValidationError({"token": INVALID_LINK_MESSAGE})
    validate_password(password, user=user)
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    audit_logger.info("password_reset_done user=%s", user.pk)
    return user


def change_password(user: User, *, current_password: str, new_password: str) -> None:
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    if not user.check_password(current_password):
        raise ValidationError({"current_password": INCORRECT_CURRENT_MESSAGE})
    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])


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


def _fetch_google_payload(credential: str) -> dict[str, Any]:
    """Vérifie un jeton d'identité Google via l'endpoint officiel `tokeninfo`.

    Isolé pour être remplaçable en test. Lève ValidationError si le jeton est invalide.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode(
        {"id_token": credential}
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - https Google
            data: dict[str, Any] = json.loads(resp.read())
            return data
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DjangoValidationError("Jeton Google invalide.") from exc


def google_sign_in(credential: str) -> User:
    """Connexion / création de compte via Google (jeton d'identité GIS)."""
    if not settings.GOOGLE_CLIENT_ID:
        raise DjangoValidationError("Connexion Google non configurée.")
    payload = _fetch_google_payload(credential)
    if payload.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise DjangoValidationError("Jeton Google destiné à une autre application.")
    if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise DjangoValidationError("Émetteur du jeton Google inattendu.")
    if str(payload.get("email_verified")).lower() not in {"true", "1"}:
        raise DjangoValidationError("Adresse Google non vérifiée.")
    email = (payload.get("email") or "").lower().strip()
    if not email:
        raise DjangoValidationError("Jeton Google sans adresse email.")
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            password=None,
            role=Role.TRAVELER,
            first_name=payload.get("given_name", "")[:80],
            last_name=payload.get("family_name", "")[:80],
        )
    return user
