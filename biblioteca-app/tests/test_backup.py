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
