"""Teste backup bază de date."""

from pathlib import Path

from database import backup as backup_mod


def test_create_backup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    db.write_bytes(b"sqlite-test-data")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", data / "backups")

    path = backup_mod.create_backup("test")
    assert path.exists()
    assert path.read_bytes() == b"sqlite-test-data"


def test_restore_creates_prerestore_backup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    db.write_bytes(b"current")
    backup_dir = data / "backups"
    backup_dir.mkdir()
    source = backup_dir / "biblioteca_manual_old.db"
    source.write_bytes(b"restored")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)

    class _Engine:
        def dispose(self) -> None:
            pass

    monkeypatch.setattr(backup_mod, "get_engine", lambda: _Engine())

    pre = backup_mod.restore_backup(source)
    assert pre is not None
    assert pre.exists()
    assert pre.read_bytes() == b"current"
    assert db.read_bytes() == b"restored"


def test_auto_backup_prunes(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    db.write_bytes(b"x")
    monkeypatch.setattr(backup_mod, "DATA_DIR", data)
    monkeypatch.setattr(backup_mod, "DB_PATH", db)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", data / "backups")

    for _ in range(7):
        backup_mod.create_backup("auto")
    auto_files = list((data / "backups").glob("biblioteca_auto_*.db"))
    assert len(auto_files) <= backup_mod.MAX_AUTO_BACKUPS
