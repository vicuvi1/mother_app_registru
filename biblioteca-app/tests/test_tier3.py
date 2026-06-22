"""Teste Batch G — Tier 3 distribuție și date."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from core import paths
from core.backup_crypto import decrypt_file, encrypt_file, is_encrypted_backup
from core.cloud_backup import maybe_sync_backup, set_cloud_backup_enabled, set_cloud_backup_target
from core.part_import_meta import list_importable_parts
from ui.excel_import.import_excel import _coerce_value, _find_header_row
from ui.widgets.table.column_def import ColumnDef


def test_portable_data_dir_next_to_install(monkeypatch, tmp_path):
    fake_exe = tmp_path / "RegistruDigital.exe"
    fake_exe.write_bytes(b"")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(fake_exe))
    monkeypatch.delenv("BIBLIOTECA_DATA_DIR", raising=False)
    assert paths.get_data_dir() == tmp_path / "data"
    assert paths.is_portable_mode() is True


def test_data_dir_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "usb_data"
    monkeypatch.setenv("BIBLIOTECA_DATA_DIR", str(custom))
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    assert paths.get_data_dir() == custom.resolve()


def test_backup_encrypt_roundtrip(tmp_path):
    plain = tmp_path / "plain.db"
    enc = tmp_path / "backup.db.enc"
    out = tmp_path / "restored.db"
    with sqlite3.connect(plain) as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
    encrypt_file(plain, enc, "parola-test")
    assert is_encrypted_backup(enc)
    decrypt_file(enc, out, "parola-test")
    assert out.exists()
    with sqlite3.connect(out) as conn:
        conn.execute("SELECT 1 FROM t")


def test_cloud_backup_copy(tmp_path, monkeypatch):
    store: dict[str, str] = {}

    import core.cloud_backup as cb

    monkeypatch.setattr(cb, "get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(cb, "set_setting", lambda k, v: store.__setitem__(k, v))

    target = tmp_path / "cloud"
    set_cloud_backup_target(str(target))
    set_cloud_backup_enabled(True)

    src = tmp_path / "biblioteca_manual_1.db"
    src.write_bytes(b"sqlite")
    dest = maybe_sync_backup(src)
    assert dest is not None
    assert dest.exists()


def test_importable_parts_list():
    parts = list_importable_parts()
    assert any(p[0] == "part_01" for p in parts)
    assert all(p[0] != "part_13" for p in parts)


def test_find_header_row():
    headers = ["Data", "Adulți"]
    rows = [
        ["Titlu registru"],
        ["Partea I"],
        headers,
        ["2026-01-01", 5],
        ["Total", 5],
    ]
    assert _find_header_row(rows, headers) == 2


def test_coerce_int_column():
    col = ColumnDef("x", "int")
    assert _coerce_value(col, "12") == 12
    assert _coerce_value(col, "") == 0


def test_installer_files_exist():
    root = Path(__file__).resolve().parent.parent
    assert (root / "installer" / "registru.iss").is_file()
    assert (root / "build_installer.bat").is_file()
