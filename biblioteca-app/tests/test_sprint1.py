"""Teste Sprint I — toast, empty state, evidențiere zi curentă."""

from datetime import date

from PyQt6.QtCore import Qt

from ui.parts.mixins.cache_mixin import PartCacheMixin
from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.register_table_model import RegisterTableModel, TODAY_COLOR
from ui.widgets.toast import ToastHost


def test_today_row_highlight(qapp):
    cols = [ColumnDef("data", "date"), ColumnDef("adulti", "int")]
    model = RegisterTableModel()
    model.setup(cols)
    today = date.today()
    dd_mm = f"{today.day:02d}.{today.month:02d}"
    model.load_rows([{"data": dd_mm, "adulti": 3}, {"data": "01.01", "adulti": 1}])
    model.set_highlight_date("data", dd_mm)
    brush = model.data(model.index(0, 0), Qt.ItemDataRole.BackgroundRole)
    assert brush is not None
    assert brush.color() == TODAY_COLOR
    brush_other = model.data(model.index(1, 0), Qt.ItemDataRole.BackgroundRole)
    assert brush_other is None or brush_other.color() != TODAY_COLOR


def test_toast_host_shows(qtbot, qapp):
    from PyQt6.QtWidgets import QWidget

    host = QWidget()
    host.resize(640, 480)
    qtbot.addWidget(host)
    host.show()
    toast = ToastHost(host)
    toast.show_message("Test toast", duration_ms=5000)
    qapp.processEvents()
    assert toast.isVisible()
    assert "Test toast" in toast._label.text()


class _FakeTable:
    def __init__(self, ids):
        self._ids = ids

    def get_data_rows(self):
        return [{"data": "01.06"}] if self._ids else []

    def get_row_ids(self):
        return self._ids

    def get_auto_flags(self):
        return [False] * len(self._ids)


def test_snapshot_marks_unsaved_daily_month():
    class Stub(PartCacheMixin):
        mode = "daily"

    stub = Stub()
    snap = stub._snapshot_table(_FakeTable([None, None]))
    assert snap["db_empty"] is True
    snap_saved = stub._snapshot_table(_FakeTable([1, 2]))
    assert snap_saved["db_empty"] is False
