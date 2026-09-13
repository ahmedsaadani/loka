"""
Sauvegardes chiffrées de la base PostgreSQL vers le bucket privé.

- `create_backup` : `pg_dump -Fc` → chiffrement symétrique Fernet → upload S3 privé.
- `rotate_backups` : rétention (quotidiennes récentes + une hebdomadaire par semaine ISO).
- `restore_backup` : téléchargement → déchiffrement → `pg_restore`. DESTRUCTIF.

Le mot de passe de la base n'est jamais interpolé dans une ligne de commande : il transite
uniquement par la variable d'environnement `PGPASSWORD` du sous-processus.
Voir docs/backups.md pour la procédure complète de restauration.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess  # nosec B404 - appels pg_dump/pg_restore en liste, sans shell
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, storages
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKUP_PREFIX = "backups/db"
_NAME_RE = re.compile(r"loka-(\d{8})-(\d{6})\.dump\.fernet$")


class BackupError(Exception):
    """Erreur générique du sous-système de sauvegarde."""


class RestoreRefused(BackupError):
    """La restauration a été refusée faute de confirmation explicite."""


@dataclass(frozen=True)
class BackupEntry:
    """Une sauvegarde stockée, datée d'après son nom de fichier."""

    name: str
    timestamp: datetime

    @property
    def day(self) -> date:
        return self.timestamp.date()


# ------------------------------------------------------------------ helpers


def _fernet() -> Fernet | None:
    """Retourne le chiffreur, ou None si aucune clé n'est configurée (sauvegardes désactivées)."""
    key: str = settings.BACKUP_ENCRYPTION_KEY
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise BackupError(
            "BACKUP_ENCRYPTION_KEY invalide : générer une clé avec "
            '`python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"`'
        ) from exc


def _private_storage() -> Storage:
    return storages["private"]


def _db_env_and_args() -> tuple[dict[str, str], list[str]]:
    """Variables d'environnement et arguments de connexion communs à pg_dump / pg_restore."""
    db = settings.DATABASES["default"]
    env = {**os.environ, "PGPASSWORD": str(db.get("PASSWORD") or "")}
    args: list[str] = ["--no-password"]
    if db.get("HOST"):
        args += ["-h", str(db["HOST"])]
    if db.get("PORT"):
        args += ["-p", str(db["PORT"])]
    if db.get("USER"):
        args += ["-U", str(db["USER"])]
    args += ["-d", str(db["NAME"])]
    return env, args


def _run(args: list[str], *, env: dict[str, str], input_bytes: bytes | None = None) -> bytes:
    """Exécute un binaire PostgreSQL sans shell, lève BackupError en cas d'échec."""
    try:
        # Arguments en liste, jamais de shell : entrée non interpolée (faux positif S603/B603).
        result = subprocess.run(  # noqa: S603 # nosec B603
            args, check=True, capture_output=True, env=env, input=input_bytes
        )
    except FileNotFoundError as exc:
        raise BackupError(f"Binaire introuvable : {args[0]} (installer postgresql-client)") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip() if exc.stderr else ""
        raise BackupError(f"{args[0]} a échoué (code {exc.returncode}) : {stderr}") from exc
    return bytes(result.stdout)


def parse_backup_name(name: str) -> BackupEntry | None:
    """Extrait l'horodatage depuis le nom `.../loka-YYYYMMDD-HHMMSS.dump.fernet`."""
    match = _NAME_RE.search(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return BackupEntry(name=name, timestamp=stamp)


def list_backups(storage: Storage | None = None) -> list[BackupEntry]:
    """Liste récursivement `backups/db/`, triée de la plus ancienne à la plus récente."""
    storage = storage or _private_storage()
    entries: list[BackupEntry] = []
    pending = [BACKUP_PREFIX]
    while pending:
        current = pending.pop()
        try:
            dirs, files = storage.listdir(current)
        except FileNotFoundError:
            continue
        pending.extend(f"{current}/{d}" for d in dirs)
        for filename in files:
            entry = parse_backup_name(f"{current}/{filename}")
            if entry is not None:
                entries.append(entry)
    entries.sort(key=lambda e: e.timestamp)
    return entries


# ------------------------------------------------------------------ création


def create_backup(storage: Storage | None = None) -> str | None:
    """
    Dump `-Fc` de la base par défaut, chiffré avec Fernet, stocké sous
    `backups/db/YYYY/MM/loka-YYYYMMDD-HHMMSS.dump.fernet`. Retourne le nom stocké,
    ou None si `BACKUP_ENCRYPTION_KEY` est vide (sauvegardes désactivées).
    """
    fernet = _fernet()
    if fernet is None:
        logger.warning("BACKUP_ENCRYPTION_KEY absente : sauvegarde ignorée.")
        return None
    storage = storage or _private_storage()

    env, conn_args = _db_env_and_args()
    dump = _run(["pg_dump", "-Fc", *conn_args], env=env)
    if not dump:
        raise BackupError("pg_dump a produit un dump vide.")

    now = timezone.localtime()
    name = f"{BACKUP_PREFIX}/{now:%Y/%m}/loka-{now:%Y%m%d-%H%M%S}.dump.fernet"
    stored = storage.save(name, ContentFile(fernet.encrypt(dump)))
    logger.info("Sauvegarde créée : %s (%d octets bruts)", stored, len(dump))
    return stored


# ------------------------------------------------------------------ rétention


def select_backups_to_delete(entries: list[BackupEntry], today: date) -> list[BackupEntry]:
    """
    Applique la politique de rétention (fonction pure, testable) :
    - conserve toutes les sauvegardes des `BACKUP_RETENTION_DAYS` derniers jours ;
    - conserve la plus ancienne sauvegarde de chacune des `BACKUP_RETENTION_WEEKS`
      dernières semaines ISO (semaine courante incluse) ;
    - tout le reste est à supprimer.
    """
    days: int = settings.BACKUP_RETENTION_DAYS
    weeks: int = settings.BACKUP_RETENTION_WEEKS
    kept_weeks = {(today - timedelta(weeks=i)).isocalendar()[:2] for i in range(weeks)}

    weekly_keep: dict[tuple[int, int], BackupEntry] = {}
    for entry in sorted(entries, key=lambda e: e.timestamp):
        week = entry.day.isocalendar()[:2]
        if week in kept_weeks and week not in weekly_keep:
            weekly_keep[week] = entry
    weekly_names = {e.name for e in weekly_keep.values()}

    to_delete: list[BackupEntry] = []
    for entry in entries:
        age = (today - entry.day).days
        # age négatif (horloge décalée) : traité comme récent, jamais supprimé.
        if age < days or entry.name in weekly_names:
            continue
        to_delete.append(entry)
    return to_delete


def rotate_backups(today: date | None = None, storage: Storage | None = None) -> list[str]:
    """Supprime les sauvegardes hors rétention. Retourne les noms supprimés."""
    storage = storage or _private_storage()
    today = today or timezone.localdate()
    deleted: list[str] = []
    for entry in select_backups_to_delete(list_backups(storage), today):
        storage.delete(entry.name)
        deleted.append(entry.name)
        logger.info("Sauvegarde supprimée (rétention) : %s", entry.name)
    return deleted


# ------------------------------------------------------------------ restauration


def restore_backup(name: str, *, confirm: bool, storage: Storage | None = None) -> None:
    """
    DESTRUCTIF : remplace le contenu de la base par défaut par celui de la sauvegarde
    (`pg_restore --clean --if-exists --no-owner`). Refuse de s'exécuter sans
    `confirm=True` et, hors DEBUG, sans `ALLOW_DB_RESTORE=1` dans l'environnement.
    Pour cibler une autre base (répétition à blanc), surcharger `DATABASE_URL`.
    """
    if not confirm:
        raise RestoreRefused("Restauration refusée : confirmation explicite requise (--yes).")
    if not settings.DEBUG and os.environ.get("ALLOW_DB_RESTORE") != "1":
        raise RestoreRefused("Restauration refusée : définir ALLOW_DB_RESTORE=1 hors DEBUG.")
    fernet = _fernet()
    if fernet is None:
        raise BackupError("BACKUP_ENCRYPTION_KEY absente : impossible de déchiffrer.")
    storage = storage or _private_storage()
    if not storage.exists(name):
        raise BackupError(f"Sauvegarde introuvable : {name}")

    with storage.open(name, "rb") as handle:
        token = bytes(handle.read())
    try:
        dump = fernet.decrypt(token)
    except InvalidToken as exc:
        raise BackupError("Déchiffrement impossible : clé différente ou fichier corrompu.") from exc

    env, conn_args = _db_env_and_args()
    _run(
        ["pg_restore", "--clean", "--if-exists", "--no-owner", *conn_args],
        env=env,
        input_bytes=dump,
    )
    logger.warning("Base restaurée depuis %s", name)
