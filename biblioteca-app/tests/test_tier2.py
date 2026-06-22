"""Teste Batch F — Tier 2 UX."""

from pathlib import Path

from core.export_presets import (
    get_export_folder,
    get_print_orientation,
    set_export_folder,
    set_print_orientation,
    suggest_export_path,
)
from core.ui_theme import get_ui_theme, set_ui_theme
from ui.widgets.table.register_table_model import RegisterTableModel
from ui.widgets.table.column_def import ColumnDef


def test_export_folder_preset(monkeypatch):
    store: dict[str, str] = {}

    import core.export_presets as ep

    monkeypatch.setattr(ep, "get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(ep, "set_setting", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr("database.db_manager.get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("database.db_manager.set_setting", lambda k, v: store.__setitem__(k, v))

    set_export_folder(r"C:\Exports\registru.docx")
    assert "Exports" in get_export_folder()
    path = suggest_export_path("Partea_I.pdf")
    assert path.endswith("Partea_I.pdf")
    assert "Exports" in path


def test_print_orientation(monkeypatch):
    store: dict[str, str] = {}

    import core.export_presets as ep

    monkeypatch.setattr(ep, "get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(ep, "set_setting", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr("database.db_manager.get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("database.db_manager.set_setting", lambda k, v: store.__setitem__(k, v))

    assert get_print_orientation() == "landscape"
    set_print_orientation("portrait")
    assert get_print_orientation() == "portrait"


def test_ui_theme(monkeypatch):
    store: dict[str, str] = {}

    import core.ui_theme as ut

    monkeypatch.setattr(ut, "get_setting", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(ut, "set_setting", lambda k, v: store.__setitem__(k, v))

    assert get_ui_theme() == "light"
    set_ui_theme("dark")
    assert get_ui_theme() == "dark"


def test_table_find_matches():
    model = RegisterTableModel()
    model.setup(
        [ColumnDef("nume", "text"), ColumnDef("val", "int")],
        part_id="part_test",
    )
    model.load_rows(
        [{"nume": "Bibliotecă", "val": 1}, {"nume": "altceva", "val": 0}],
        [1, 2],
        [False, False],
    )
    hits = model.find_matches("biblio")
    assert hits == [(0, 0)]


def test_pdf_romanian_diacritics(tmp_path):
    from ui.export.export_pdf import export_to_pdf

    page = {
        "headers": ["Descriere"],
        "groups": [""],
        "col_keys": ["descriere"],
        "rows": [{"descriere": "Înregistrări — Chișinău"}],
        "total_rows": [("Total", {"descriere": 0})],
        "meta": {
            "parte_roman": "I",
            "title": "Evidența utilizatorilor",
            "an": 2026,
            "nume_biblioteca": "Biblioteca Bărbuță",
            "localitate": "București",
        },
    }
    out = tmp_path / "ro.pdf"
    export_to_pdf(out, [page])
    assert out.stat().st_size > 500
