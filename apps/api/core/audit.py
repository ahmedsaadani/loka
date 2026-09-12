"""Journalisation des accès aux données sensibles (ADR 0004)."""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest

from core.models import SensitiveAccessLog

audit_logger = logging.getLogger("loka.audit")


def client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return str(forwarded).split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_sensitive_access(request: HttpRequest, kind: str, target: Any) -> None:
    user = request.user if request.user.is_authenticated else None
    SensitiveAccessLog.objects.create(
        actor=user,
        kind=kind,
        target_type=type(target).__name__,
        target_id=str(getattr(target, "pk", target)),
        ip_address=client_ip(request),
        user_agent=str(request.META.get("HTTP_USER_AGENT", ""))[:256],
    )
    audit_logger.info(
        "sensitive_access kind=%s target=%s#%s actor=%s ip=%s",
        kind,
        type(target).__name__,
        getattr(target, "pk", target),
        getattr(user, "pk", None),
        client_ip(request),
    )
