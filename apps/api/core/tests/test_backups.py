"""Tests du sous-système de sauvegarde : chiffrement, rétention, garde-fous, commandes."""

from __future__ import annotations

import subprocess
from datetime import date, datetime
from io import StringIO
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management import CommandError, call_command

from core import backups
from core.backups import (
    BACKUP_PREFIX,
    BackupEntry,
    BackupError,
    RestoreRefused,
    create_backup,
    list_backups,
    parse_backup_name,
    restore_backup,
    rotate_backups,
    select_backups_to_delete,
)

FAKE_DUMP = b"PGDMP\x00fake-custom-format-dump"


@pytest.fixture
def key(settings):
    generated = Fernet.generate_key().decode()
    settings.BACKUP_ENCRYPTION_KEY = generated
    return generated


@pytest.fixture
def storage():
    private = storages["private"]
    yield private
    for entry in list_backups(private):
        private.delete(entry.name)


@pytest.fixture
def fake_pg_dump():
    """Remplace subprocess.run : pg_dump renvoie FAKE_DUMP, pg_restore enregistre son entrée."""
    calls: list[dict] = []

    def run(args, **kwargs):
        calls.append({"args": args, **kwargs})
        stdout = FAKE_DUMP if args[0] == "pg_dump" else b""
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=b"")

    with mock.patch.object(backups.subprocess, "run", side_effect=run):
        yield calls


def name_for(day: date, hhmmss: str = "030000") -> str:
    return f"{BACKUP_PREFIX}/{day:%Y/%m}/loka-{day:%Y%m%d}-{hhmmss}.dump.fernet"


def entry_for(day: date, hhmmss: str = "030000") -> BackupEntry:
    entry = parse_backup_name(name_for(day, hhmmss))
    assert entry is not None
    return entry


# ------------------------------------------------------------------ création


class TestCreateBackup:
    def test_dump_is_encrypted_and_decrypts_to_dump_bytes(self, key, storage, fake_pg_dump):
        name = create_backup()

        assert name is not None
        assert name.startswith(f"{BACKUP_PREFIX}/")
        assert name.endswith(".dump.fernet")
        with storage.open(name, "rb") as handle:
            stored = handle.read()
        assert stored != FAKE_DUMP
        assert FAKE_DUMP not in stored
        assert Fernet(key.encode()).decrypt(stored) == FAKE_DUMP

    def test_pg_dump_invoked_without_shell_and_password_in_env_only(
        self, key, storage, fake_pg_dump, settings
    ):
        settings.DATABASES = {"default": {**settings.DATABASES["default"], "PASSWORD": "s3cret-pw"}}
        create_backup()

        (call,) = fake_pg_dump
        assert call["args"][:2] == ["pg_dump", "-Fc"]
        assert call["check"] is True
        assert "shell" not in call
        assert call["env"]["PGPASSWORD"] == "s3cret-pw"
        assert not any("s3cret-pw" in arg for arg in call["args"])

    def test_missing_key_disables_backups(self, settings, storage, fake_pg_dump, caplog):
        settings.BACKUP_ENCRYPTION_KEY = ""

        assert create_backup() is None
        assert fake_pg_dump == []
        assert list_backups(storage) == []
        assert any("BACKUP_ENCRYPTION_KEY" in rec.message for rec in caplog.records)

    def test_invalid_key_raises(self, settings, storage, fake_pg_dump):
        settings.BACKUP_ENCRYPTION_KEY = "pas-une-cle-fernet"
        with pytest.raises(BackupError):
            create_backup()

    def test_pg_dump_failure_raises(self, key, storage):
        error = subprocess.CalledProcessError(1, ["pg_dump"], stderr=b"connection refused")
        with (
            mock.patch.object(backups.subprocess, "run", side_effect=error),
            pytest.raises(BackupError, match="connection refused"),
        ):
            create_backup()


# ------------------------------------------------------------------ nommage / listing


class TestListing:
    def test_parse_backup_name(self):
        entry = parse_backup_name("backups/db/2026/09/loka-20260913-031500.dump.fernet")
        assert entry == BackupEntry(
            name="backups/db/2026/09/loka-20260913-031500.dump.fernet",
            timestamp=datetime(2026, 9, 13, 3, 15, 0),
        )
        assert parse_backup_name("backups/db/2026/09/notes.txt") is None
        assert parse_backup_name("backups/db/2026/13/loka-20261399-000000.dump.fernet") is None

    def test_list_is_recursive_sorted_and_ignores_foreign_files(self, storage):
        storage.save(name_for(date(2026, 9, 1)), ContentFile(b"x"))
        storage.save(name_for(date(2026, 8, 30)), ContentFile(b"x"))
        storage.save(f"{BACKUP_PREFIX}/2026/08/README.txt", ContentFile(b"x"))

        names = [e.name for e in list_backups(storage)]
        assert names == [name_for(date(2026, 8, 30)), name_for(date(2026, 9, 1))]
        storage.delete(f"{BACKUP_PREFIX}/2026/08/README.txt")

    def test_empty_storage(self, storage):
        assert list_backups(storage) == []


# ------------------------------------------------------------------ rétention


class TestRetention:
    TODAY = date(2026, 9, 13)  # dimanche, semaine ISO 37

    def test_keeps_last_7_days_and_one_weekly_for_4_weeks(self, settings):
        settings.BACKUP_RETENTION_DAYS = 7
        settings.BACKUP_RETENTION_WEEKS = 4
        # Une sauvegarde par jour sur 40 jours.
        days = [date.fromordinal(self.TODAY.toordinal() - i) for i in range(40)]
        entries = [entry_for(d) for d in days]

        deleted = {e.day for e in select_backups_to_delete(entries, self.TODAY)}
        kept = {d for d in days if d not in deleted}

        # Les 7 derniers jours (7 au 13 septembre) sont tous conservés.
        assert all(date.fromordinal(self.TODAY.toordinal() - i) in kept for i in range(7))
        # Hebdomadaires : le lundi (plus ancienne de la semaine) des semaines ISO 34..37.
        assert date(2026, 8, 17) in kept  # S34
        assert date(2026, 8, 24) in kept  # S35
        assert date(2026, 8, 31) in kept  # S36
        assert date(2026, 9, 7) in kept  # S37 (déjà dans les 7 jours)
        assert kept == {date.fromordinal(self.TODAY.toordinal() - i) for i in range(7)} | {
            date(2026, 8, 17),
            date(2026, 8, 24),
            date(2026, 8, 31),
        }
        # Le reste (semaine 33 et avant, jours intermédiaires) est supprimé.
        assert date(2026, 8, 10) in deleted
        assert date(2026, 8, 18) in deleted
        assert date(2026, 8, 5) in deleted

    def test_weekly_keeps_oldest_of_the_week_by_timestamp(self, settings):
        settings.BACKUP_RETENTION_DAYS = 7
        settings.BACKUP_RETENTION_WEEKS = 4
        # Semaine ISO 35 : deux sauvegardes le même jour + une plus tard dans la semaine.
        oldest = entry_for(date(2026, 8, 26), "020000")
        later_same_day = entry_for(date(2026, 8, 26), "150000")
        later_in_week = entry_for(date(2026, 8, 28))

        deleted = select_backups_to_delete([later_in_week, later_same_day, oldest], self.TODAY)
        assert [e.name for e in deleted] == [later_in_week.name, later_same_day.name]

    def test_future_dated_backups_are_never_deleted(self, settings):
        settings.BACKUP_RETENTION_DAYS = 7
        future = entry_for(date(2026, 9, 20))
        assert select_backups_to_delete([future], self.TODAY) == []

    def test_rotate_deletes_from_storage_with_injected_today(self, storage, settings):
        settings.BACKUP_RETENTION_DAYS = 7
        settings.BACKUP_RETENTION_WEEKS = 4
        recent = name_for(date(2026, 9, 12))
        weekly = name_for(date(2026, 8, 24))
        stale = name_for(date(2026, 8, 25))
        very_old = name_for(date(2026, 7, 1))
        for name in (recent, weekly, stale, very_old):
            storage.save(name, ContentFile(b"x"))

        deleted = rotate_backups(today=self.TODAY, storage=storage)

        assert sorted(deleted) == sorted([stale, very_old])
        assert storage.exists(recent) and storage.exists(weekly)
        assert not storage.exists(stale) and not storage.exists(very_old)


# ------------------------------------------------------------------ restauration


class TestRestore:
    def test_refuses_without_confirm(self, key, storage, fake_pg_dump):
        with pytest.raises(RestoreRefused):
            restore_backup("backups/db/x.dump.fernet", confirm=False)
        assert fake_pg_dump == []

    def test_refuses_without_env_flag_outside_debug(
        self, key, storage, fake_pg_dump, settings, monkeypatch
    ):
        settings.DEBUG = False
        monkeypatch.delenv("ALLOW_DB_RESTORE", raising=False)
        with pytest.raises(RestoreRefused, match="ALLOW_DB_RESTORE"):
            restore_backup("backups/db/x.dump.fernet", confirm=True)
        assert fake_pg_dump == []

    def test_restores_decrypted_dump_via_pg_restore(
        self, key, storage, fake_pg_dump, settings, monkeypatch
    ):
        settings.DEBUG = False
        monkeypatch.setenv("ALLOW_DB_RESTORE", "1")
        name = create_backup()
        assert name is not None

        restore_backup(name, confirm=True)

        restore_call = fake_pg_dump[-1]
        assert restore_call["args"][0] == "pg_restore"
        assert {"--clean", "--if-exists", "--no-owner"} <= set(restore_call["args"])
        assert restore_call["input"] == FAKE_DUMP
        assert restore_call["check"] is True

    def test_debug_mode_does_not_require_env_flag(
        self, key, storage, fake_pg_dump, settings, monkeypatch
    ):
        settings.DEBUG = True
        monkeypatch.delenv("ALLOW_DB_RESTORE", raising=False)
        name = create_backup()
        assert name is not None
        restore_backup(name, confirm=True)
        assert fake_pg_dump[-1]["args"][0] == "pg_restore"

    def test_missing_file(self, key, storage, fake_pg_dump, settings):
        settings.DEBUG = True
        with pytest.raises(BackupError, match="introuvable"):
            restore_backup("backups/db/nope.dump.fernet", confirm=True)

    def test_wrong_key_cannot_decrypt(self, key, storage, fake_pg_dump, settings):
        settings.DEBUG = True
        name = create_backup()
        assert name is not None
        settings.BACKUP_ENCRYPTION_KEY = Fernet.generate_key().decode()
        with pytest.raises(BackupError, match="Déchiffrement"):
            restore_backup(name, confirm=True)


# ------------------------------------------------------------------ commandes


class TestCommands:
    def test_backup_db_prints_stored_name(self, key, storage, fake_pg_dump):
        out = StringIO()
        call_command("backup_db", stdout=out)
        (entry,) = list_backups(storage)
        assert entry.name in out.getvalue()

    def test_backup_db_disabled_without_key(self, settings, storage, fake_pg_dump):
        settings.BACKUP_ENCRYPTION_KEY = ""
        out = StringIO()
        call_command("backup_db", stdout=out)
        assert "désactivées" in out.getvalue()
        assert list_backups(storage) == []

    def test_list_backups(self, key, storage, fake_pg_dump):
        out = StringIO()
        call_command("list_backups", stdout=out)
        assert "Aucune sauvegarde." in out.getvalue()

        name = create_backup()
        assert name is not None
        out = StringIO()
        call_command("list_backups", stdout=out)
        assert name in out.getvalue()

    def test_restore_db_requires_yes(self, key, storage, fake_pg_dump, settings):
        settings.DEBUG = True
        name = create_backup()
        with pytest.raises(CommandError, match="confirmation"):
            call_command("restore_db", name)
        assert all(c["args"][0] != "pg_restore" for c in fake_pg_dump)

    def test_restore_db_with_yes(self, key, storage, fake_pg_dump, settings):
        settings.DEBUG = True
        name = create_backup()
        out = StringIO()
        call_command("restore_db", name, "--yes", stdout=out)
        assert fake_pg_dump[-1]["args"][0] == "pg_restore"
        assert "restaurée" in out.getvalue()


# ------------------------------------------------------------------ tâche celery


def test_celery_task_creates_and_rotates(key, storage, fake_pg_dump):
    from core.tasks_backup import backup_database

    with mock.patch.object(backups, "rotate_backups", return_value=[]) as rotate:
        name = backup_database.delay().get()
    assert name is not None
    assert storage.exists(name)
    rotate.assert_called_once()
