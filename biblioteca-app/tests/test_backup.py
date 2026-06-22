"""Teste backup bază de date."""

import sqlite3
from pathlib import Path

from database import backup as backup_mod


def _fake_engine():
    class _Conn:
        def execute(self, *_args, **_kwargs):
            return self

        def commit(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    class _Engine:
        def dispose(self) -> None:
            pass

        def connect(self):
            return _Conn()

    return _Engine()


def _make_sqlite_db(path: Path, *, payload: str = "v1") -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT, v TEXT)")
        conn.execute("DELETE FROM meta")
        conn.execute("INSERT INTO meta(k, v) VALUES ('mark', ?)", (payload,))
        conn.commit()


def test_create_backup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    _make_sqlite_db(db, payload="sqlite-test-data")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", data / "backups")
    monkeypatch.setattr(backup_mod, "get_engine", _fake_engine)

    path = backup_mod.create_backup("test")
    assert path.exists()
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT v FROM meta WHERE k='mark'").fetchone()
    assert row[0] == "sqlite-test-data"


def test_restore_creates_prerestore_backup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    _make_sqlite_db(db, payload="current")
    backup_dir = data / "backups"
    backup_dir.mkdir()
    source = backup_dir / "biblioteca_manual_old.db"
    _make_sqlite_db(source, payload="restored")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)

    class _Engine:
        def dispose(self) -> None:
            pass

        def connect(self):
            return _fake_engine().connect()

    monkeypatch.setattr(backup_mod, "get_engine", lambda: _Engine())

    pre = backup_mod.restore_backup(source)
    assert pre is not None
    assert pre.exists()
    with sqlite3.connect(pre) as conn:
        assert conn.execute("SELECT v FROM meta WHERE k='mark'").fetchone()[0] == "current"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT v FROM meta WHERE k='mark'").fetchone()[0] == "restored"


def test_auto_backup_prunes(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    _make_sqlite_db(db, payload="x")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", data / "backups")
    monkeypatch.setattr(backup_mod, "get_engine", _fake_engine)

    for _ in range(7):
        backup_mod.create_backup("auto")
    auto_files = list((data / "backups").glob("biblioteca_auto_*.db"))
    assert len(auto_files) <= backup_mod.MAX_AUTO_BACKUPS
