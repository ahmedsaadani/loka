"""
`manage.py restore_db <name> --yes` : restauration DESTRUCTIVE de la base par défaut.
Hors DEBUG, exige aussi ALLOW_DB_RESTORE=1 dans l'environnement. Voir docs/backups.md.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.backups import BackupError, restore_backup


class Command(BaseCommand):
    help = "Restaure la base depuis une sauvegarde chiffrée (DESTRUCTIF)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("name", help="Nom stocké, ex. backups/db/2026/09/loka-....dump.fernet")
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="confirm",
            help="Confirme l'écrasement de la base courante.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            restore_backup(options["name"], confirm=bool(options["confirm"]))
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Base restaurée depuis {options['name']}"))
