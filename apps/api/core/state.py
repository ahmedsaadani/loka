"""
Machine à états générique. Voir ADR 0003.

Chaque modèle à statut déclare `TRANSITIONS: dict[str, frozenset[str]]`.
Les services appellent `transition(instance, to, actor=..., note=...)`.
Une transition non déclarée lève InvalidTransition.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.models import StatusLog

if TYPE_CHECKING:
    from accounts.models import User

audit_logger = logging.getLogger("loka.audit")


class InvalidTransition(Exception):
    def __init__(self, instance: Any, to_status: str) -> None:
        self.instance = instance
        self.from_status = getattr(instance, "status", None)
        self.to_status = to_status
        super().__init__(
            f"{type(instance).__name__}: transition interdite {self.from_status} -> {to_status}"
        )


class HasStatus(Protocol):
    TRANSITIONS: ClassVar[dict[str, frozenset[str]]]
    status: Any
    pk: Any

    def save(self, *args: Any, **kwargs: Any) -> None: ...


def can_transition(instance: HasStatus, to_status: str) -> bool:
    return to_status in instance.TRANSITIONS.get(instance.status, frozenset())


def transition(
    instance: HasStatus,
    to_status: str,
    *,
    actor: User | None = None,
    note: str = "",
    extra_fields: dict[str, Any] | None = None,
) -> None:
    """Applique la transition, sauvegarde et journalise. Lève InvalidTransition sinon."""
    if not can_transition(instance, to_status):
        raise InvalidTransition(instance, to_status)
    from_status = instance.status
    instance.status = to_status
    update_fields = ["status"]
    for field, value in (extra_fields or {}).items():
        setattr(instance, field, value)
        update_fields.append(field)
    if hasattr(instance, "updated_at"):
        update_fields.append("updated_at")
    instance.save(update_fields=update_fields)
    model_cls: type[models.Model] = type(instance)  # type: ignore[assignment]  # Protocol -> Model concret
    StatusLog.objects.create(
        content_type=ContentType.objects.get_for_model(model_cls),
        object_id=instance.pk,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note,
    )
    audit_logger.info(
        "transition model=%s pk=%s from=%s to=%s actor=%s",
        model_cls.__name__,
        instance.pk,
        from_status,
        to_status,
        getattr(actor, "pk", None),
    )
