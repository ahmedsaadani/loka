from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

STAFF_ROLES = frozenset({"staff", "admin"})
HOST_ROLES = frozenset({"host", "staff", "admin"})


def role_of(request: Request) -> str:
    user = request.user
    if not user or not user.is_authenticated:
        return ""
    return str(getattr(user, "role", ""))


def is_staff_user(user: Any) -> bool:
    return bool(user and user.is_authenticated and getattr(user, "role", "") in STAFF_ROLES)


class IsHost(BasePermission):
    """Hôte, staff ou admin."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return role_of(request) in HOST_ROLES


class IsStaff(BasePermission):
    """Équipe Loka (staff ou admin)."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return role_of(request) in STAFF_ROLES


class IsAdmin(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return role_of(request) == "admin"


class IsOwnerOrStaff(BasePermission):
    """
    Permission objet : l'objet expose `owner_id` (ou `host_id` / `traveler_id` / `user_id`).
    Le staff passe toujours.
    """

    owner_attrs = ("owner_id", "host_id", "traveler_id", "user_id")

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if role_of(request) in STAFF_ROLES:
            return True
        user_id = request.user.pk
        return any(getattr(obj, attr, None) == user_id for attr in self.owner_attrs)


class ReadOnly(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in SAFE_METHODS
