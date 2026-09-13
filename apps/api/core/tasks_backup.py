"""Tâche Celery de sauvegarde quotidienne (planifiée dans CELERY_BEAT_SCHEDULE)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.tasks.backup_database")
def backup_database() -> str | None:
    """Crée une sauvegarde chiffrée puis applique la rétention. Retourne le nom stocké."""
    from core.backups import create_backup, rotate_backups

    name = create_backup()
    if name is None:
        return None
    deleted = rotate_backups()
    logger.info("Sauvegarde %s ; %d supprimée(s) par rétention", name, len(deleted))
    return name
