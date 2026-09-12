from __future__ import annotations

from typing import Any, cast

import factory
from django.core.files.base import ContentFile

from accounts.models import HostProfile, IdentityDocument, IdentityDocumentType, Role, User

DEFAULT_PASSWORD = "loka-test-password-123"  # nosec B105 - mot de passe de test uniquement

# Plus petit PDF valide pour les tests d'upload.
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@loka.test")
    first_name = factory.Faker("first_name", locale="fr_FR")
    last_name = factory.Faker("last_name", locale="fr_FR")
    phone = factory.Sequence(lambda n: f"+2162000{n:04d}")
    role = Role.TRAVELER
    is_active = True

    @classmethod
    def _create(cls, model_class: type[User], *args: Any, **kwargs: Any) -> User:
        password = kwargs.pop("password", DEFAULT_PASSWORD)
        return User.objects.create_user(password=password, **kwargs)


class TravelerFactory(UserFactory):
    role = Role.TRAVELER


class HostFactory(UserFactory):
    role = Role.HOST
    email = factory.Sequence(lambda n: f"host{n}@loka.test")

    @factory.post_generation
    def host_profile(self, create: bool, extracted: Any, **kwargs: Any) -> None:
        if create:
            user = cast(User, self)
            HostProfile.objects.get_or_create(
                user=user, defaults={"display_name": user.full_name, **kwargs}
            )


class StaffFactory(UserFactory):
    role = Role.STAFF
    email = factory.Sequence(lambda n: f"staff{n}@loka.test")


class AdminFactory(UserFactory):
    role = Role.ADMIN
    is_staff = True
    is_superuser = True
    email = factory.Sequence(lambda n: f"admin{n}@loka.test")


class IdentityDocumentFactory(factory.django.DjangoModelFactory[IdentityDocument]):
    class Meta:
        model = IdentityDocument

    user = factory.SubFactory(UserFactory)
    doc_type = IdentityDocumentType.CIN
    mime_type = "application/pdf"
    file = factory.LazyFunction(lambda: ContentFile(MINIMAL_PDF, name="doc.pdf"))
