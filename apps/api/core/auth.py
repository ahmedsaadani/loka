from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request

if TYPE_CHECKING:
    from accounts.models import User


def current_user(request: Request) -> User:
    """Utilisateur authentifié de la requête, typé User (jamais AnonymousUser)."""
    from accounts.models import User

    user = request.user
    if not isinstance(user, User) or not user.is_authenticated:
        raise NotAuthenticated()
    return user
