from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.state import InvalidTransition


class DomainError(APIException):
    """Erreur métier renvoyée en 400 avec un code stable exploitable par le front."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail = "Requête invalide."
    default_code = "domain_error"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflit."
    default_code = "conflict"


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Format unique : {"detail": str, "code": str, "errors": {...}?}."""
    if isinstance(exc, InvalidTransition):
        exc = ConflictError(str(exc), code="invalid_transition")
    elif isinstance(exc, DjangoValidationError):
        payload: dict[str, Any] = {"detail": "Données invalides.", "code": "validation_error"}
        if hasattr(exc, "message_dict"):
            payload["errors"] = exc.message_dict
        else:
            payload["errors"] = {"non_field_errors": exc.messages}
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, Http404):
        response.data = {"detail": "Introuvable.", "code": "not_found"}
    elif isinstance(exc, PermissionDenied):
        response.data = {"detail": "Accès refusé.", "code": "permission_denied"}
    elif isinstance(exc, APIException):
        data = response.data
        if isinstance(data, dict) and "detail" in data and len(data) == 1:
            detail = data["detail"]
            response.data = {
                "detail": str(detail),
                "code": getattr(detail, "code", exc.default_code),
            }
        else:
            response.data = {
                "detail": "Données invalides.",
                "code": "validation_error",
                "errors": data,
            }
    return response
