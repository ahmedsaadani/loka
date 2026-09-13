"""`manage.py list_backups` : liste les sauvegardes présentes dans le bucket privé."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from core.backups import list_backups


class Command(BaseCommand):
    help = "Liste les sauvegardes chiffrées disponibles (de la plus ancienne à la plus récente)."

    def handle(self, *args: Any, **options: Any) -> None:
        entries = list_backups()
        if not entries:
            self.stdout.write("Aucune sauvegarde.")
            return
        for entry in entries:
            self.stdout.write(f"{entry.timestamp:%Y-%m-%d %H:%M:%S}  {entry.name}")
