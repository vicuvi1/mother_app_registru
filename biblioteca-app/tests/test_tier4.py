"""Teste Batch H — Tier 4 calitate cod."""

from datetime import timezone

import pytest
from PyQt6.QtCore import Qt

from database import db_manager as dbm
from database.models import _utc_now
from ui.export.export_common import format_biblioteca_line_reportlab
from ui.main_window import MainWindow
from ui.widgets.register_table_view import RegisterTableView
from ui.widgets.table.column_def import ColumnDef


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "biblioteca.db"
    monkeypatch.setattr(dbm, "DATA_DIR", data)
    monkeypatch.setattr(dbm, "DB_PATH", db)
    dbm._engine = None
    dbm._SessionLocal = None
    dbm.init_database(seed=True)
    dbm.mark_setup_completed()
    yield data
    dbm._engine = None
    dbm._SessionLocal = None


def test_utc_now_is_timezone_aware():
    ts = _utc_now()
    assert ts.tzinfo is not None
    assert ts.tzinfo == timezone.utc


def test_format_biblioteca_line_reportlab():
    meta = {"nume_biblioteca": "Biblioteca „M. Eminescu”", "localitate": "Chișinău"}
    html = format_biblioteca_line_reportlab(meta)
    assert html.startswith("<b>")
    assert "Biblioteca" in html
    assert "Chișinău" in html
    assert format_biblioteca_line_reportlab({}) == ""


def test_main_window_constructs(qtbot, test_db):
    win = MainWindow(load_first_part=False)
    qtbot.addWidget(win)
    assert win.windowTitle()
    assert win._part_list.count() == 12


def test_main_window_loads_part_one(qtbot, test_db, monkeypatch):
    monkeypatch.setattr(
        "ui.main_window.load_session",
        lambda: {"part_id": "part_01", "year": 2026, "month": 6},
    )
    win = MainWindow(load_first_part=True)
    qtbot.addWidget(win)
    page = win._content_stack.currentWidget()
    assert page is not None
    assert getattr(page, "part_id", None) == "part_01"


def test_register_table_tab_moves_focus(qtbot):
    cols = [
        ColumnDef("data", "date"),
        ColumnDef("adulti", "int"),
        ColumnDef("note", "text"),
    ]
    table = RegisterTableView()
    qtbot.addWidget(table)
    table.setup(cols)
    table.load_rows([{"data": "01.03", "adulti": 1, "note": "a"}])
    table.setCurrentIndex(table.model().index(0, 1))
    table.setFocus()
    qtbot.keyClick(table, Qt.Key.Key_Tab)
    assert table.currentIndex().column() == 2


def test_register_table_undo_preset_cell(qtbot, qapp):
    cols = [ColumnDef("activitate", "preset_text")]
    table = RegisterTableView()
    qtbot.addWidget(table)
    table.setup(cols, part_id="part_06")
    table.load_rows([{"activitate": "Lectură"}])
    table.show()
    qapp.processEvents()

    model = table.model()
    index = model.index(0, 0)
    widget = table.indexWidget(index)
    if widget is None:
        pytest.skip("PresetTextCell not mounted in headless env")

    model.setData(index, "Atelier", Qt.ItemDataRole.EditRole)
    table._push_undo(0, 0, "Lectură", "Atelier")
    table.undo_last()
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Lectură"
    assert widget.value() == "Lectură"
