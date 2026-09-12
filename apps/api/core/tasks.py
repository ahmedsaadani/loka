"""Mise en file de tâches Celery après commit, exécution immédiate en mode eager (tests)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import transaction


def enqueue(task: Any, *args: Any, **kwargs: Any) -> None:
    """
    Planifie `task.delay(*args)` à la validation de la transaction courante.
    En mode CELERY_TASK_ALWAYS_EAGER (tests), exécute tout de suite : les tests pytest-django
    tournent dans une transaction annulée, `on_commit` ne se déclencherait jamais.
    """
    if settings.CELERY_TASK_ALWAYS_EAGER:
        task.delay(*args, **kwargs)
        return
    transaction.on_commit(lambda: task.delay(*args, **kwargs))
