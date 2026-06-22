"""Teste persistență sesiune."""

from core import session_state as ss


def test_save_and_load_session(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(ss, "DATA_DIR", data_dir)
    monkeypatch.setattr(ss, "SESSION_PATH", data_dir / "session.json")

    ss.save_session(part_id="part_01", year=2026, month=3)
    loaded = ss.load_session()
    assert loaded == {"part_id": "part_01", "year": 2026, "month": 3}

    ss.save_session(year=2025)
    loaded = ss.load_session()
    assert loaded["part_id"] == "part_01"
    assert loaded["year"] == 2025
    assert loaded["month"] == 3


def test_load_session_missing_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(ss, "DATA_DIR", data_dir)
    monkeypatch.setattr(ss, "SESSION_PATH", data_dir / "session.json")
    assert ss.load_session() == {}
