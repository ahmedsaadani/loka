from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from core.models import PublicIdModel, TimeStampedModel
from core.storages import generated_name, private_storage


class Role(models.TextChoices):
    TRAVELER = "traveler", "Voyageur"
    HOST = "host", "Propriétaire"
    STAFF = "staff", "Équipe"
    ADMIN = "admin", "Administrateur"


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra: Any) -> User:
        if not email:
            raise ValueError("L'email est obligatoire.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("role", Role.TRAVELER)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.update(role=Role.ADMIN, is_staff=True, is_superuser=True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, PublicIdModel, TimeStampedModel):
    """Utilisateur Loka. L'email est l'identifiant (fixé dès la première migration)."""

    email = models.EmailField("email", unique=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=24, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.TRAVELER)
    is_identity_verified = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=2, choices=settings.LANGUAGES, default="fr")
    is_active = models.BooleanField(default=True)
    # Accès à l'admin Django (outil interne). Distinct du rôle métier "staff".
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = "utilisateur"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_loka_staff(self) -> bool:
        return self.role in {Role.STAFF, Role.ADMIN}

    @property
    def is_host(self) -> bool:
        return self.role in {Role.HOST, Role.STAFF, Role.ADMIN}


class HostProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="host_profile")
    display_name = models.CharField(max_length=80)
    bio = models.TextField(blank=True)
    company_name = models.CharField(max_length=120, blank=True)
    # IBAN complet : jamais sérialisé, accès journalisé (ADR 0004).
    bank_iban_private = models.CharField(max_length=40, blank=True)
    bank_details_masked = models.CharField(max_length=40, blank=True, editable=False)

    class Meta:
        verbose_name = "profil hôte"

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args: Any, **kwargs: Any) -> None:
        iban = self.bank_iban_private.replace(" ", "")
        self.bank_details_masked = f"{iban[:4]} **** {iban[-4:]}" if len(iban) >= 8 else ""
        super().save(*args, **kwargs)


class IdentityDocumentType(models.TextChoices):
    CIN = "cin", "Carte d'identité nationale"
    PASSPORT = "passport", "Passeport"


class IdentityDocumentStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    APPROVED = "approved", "Approuvé"
    REJECTED = "rejected", "Rejeté"


def identity_upload_to(instance: IdentityDocument, filename: str) -> str:
    return generated_name(f"identity/{instance.user_id}", filename)


class IdentityDocument(PublicIdModel, TimeStampedModel):
    TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        IdentityDocumentStatus.PENDING: frozenset(
            {IdentityDocumentStatus.APPROVED, IdentityDocumentStatus.REJECTED}
        ),
        IdentityDocumentStatus.APPROVED: frozenset(),
        IdentityDocumentStatus.REJECTED: frozenset(),
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identity_documents")
    doc_type = models.CharField(max_length=16, choices=IdentityDocumentType.choices)
    file = models.FileField(upload_to=identity_upload_to, storage=private_storage)
    mime_type = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=16,
        choices=IdentityDocumentStatus.choices,
        default=IdentityDocumentStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_identities"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "document d'identité"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} de {self.user} ({self.status})"
