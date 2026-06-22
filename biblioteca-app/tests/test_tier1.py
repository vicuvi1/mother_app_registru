"""Teste integritate DB și setări autosalvare."""

import sqlite3
from pathlib import Path

from core.autosave import DEFAULT_INTERVAL, get_autosave_interval, save_autosave_interval
from core.version import APP_VERSION, BUILD_DATE
from database.integrity import check_database_integrity


def test_version_constants():
    assert APP_VERSION
    assert BUILD_DATE


def test_integrity_check_on_memory_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.commit()

    import database.integrity as integrity_mod

    monkeypatch.setattr(integrity_mod, "DB_PATH", db_path)
    ok, msg = check_database_integrity()
    assert ok is True
    assert msg == "ok"


def test_autosave_interval_roundtrip(monkeypatch):
    settings: dict[str, str] = {}

    import core.autosave as autosave_mod

    monkeypatch.setattr(
        autosave_mod, "get_setting", lambda k, d=None: settings.get(k, d)
    )
    monkeypatch.setattr(autosave_mod, "set_setting", lambda k, v: settings.__setitem__(k, v))

    assert get_autosave_interval() == DEFAULT_INTERVAL
    save_autosave_interval(300)
    assert get_autosave_interval() == 300
    save_autosave_interval(0)
    assert get_autosave_interval() == 0
