from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest
from rest_framework.test import APIClient

from accounts.factories import AdminFactory, HostFactory, StaffFactory, TravelerFactory
from accounts.models import User


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def traveler(db: None) -> User:
    return cast(User, TravelerFactory())


@pytest.fixture
def host(db: None) -> User:
    return cast(User, HostFactory())


@pytest.fixture
def other_host(db: None) -> User:
    return cast(User, HostFactory())


@pytest.fixture
def staff(db: None) -> User:
    return cast(User, StaffFactory())


@pytest.fixture
def admin(db: None) -> User:
    return cast(User, AdminFactory())


@pytest.fixture
def as_user() -> Callable[[User], APIClient]:
    """Client authentifié pour un utilisateur donné."""

    def _make(user: User) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _make
