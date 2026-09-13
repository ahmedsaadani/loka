"""`manage.py backup_db` : sauvegarde chiffrée immédiate + rotation."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.backups import BackupError, create_backup, rotate_backups


class Command(BaseCommand):
    help = "Crée une sauvegarde chiffrée de la base et applique la rétention."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            name = create_backup()
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        if name is None:
            self.stdout.write(
                self.style.WARNING("Sauvegardes désactivées : BACKUP_ENCRYPTION_KEY absente.")
            )
            return
        deleted = rotate_backups()
        self.stdout.write(self.style.SUCCESS(name))
        for old in deleted:
            self.stdout.write(f"supprimé : {old}")
