"""Teste TableDataStore, factory și delegați."""

from PyQt6.QtCore import Qt

from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.data_store import TableDataStore
from ui.widgets.table.register_table_model import RegisterTableModel
from ui.widgets.table_factory import create_register_table, table_needs_legacy_widget
from ui.widgets.register_table_view import RegisterTableView


def test_table_uses_register_view_for_widget_columns(qapp):
    cols = [
        ColumnDef("flag", "bool"),
        ColumnDef("name", "preset_text"),
        ColumnDef("who", "responsabil"),
    ]
    assert table_needs_legacy_widget(cols) is False
    table = create_register_table(cols)
    assert isinstance(table, RegisterTableView)


def test_table_store_sums():
    store = TableDataStore()
    store.columns = [ColumnDef("a", "int"), ColumnDef("b", "int")]
    store.set_payload([{"a": 1, "b": 2}, {"a": 3, "b": 4}], [1, 2], [False, False])
    sums = store.compute_column_sums()
    assert sums == {"a": 4, "b": 6}


def test_bool_cell_in_store():
    store = TableDataStore()
    store.columns = [ColumnDef("x", "bool")]
    store.set_payload([{"x": True}], [1], [False])
    assert store.get_cell(0, 0) is True


def test_store_counts_checked_boxes():
    store = TableDataStore()
    store.columns = [
        ColumnDef("online", "bool", count_in_total=True),
        ColumnDef("scope_local", "scope_local", count_in_total=True),
    ]
    store.set_payload(
        [
            {"online": True, "scope_local": False},
            {"online": True, "scope_local": True},
            {"online": False, "scope_local": False},
        ],
        [1, 2, 3],
        [False, False, False],
    )
    sums = store.compute_column_sums()
    assert sums == {"online": 2, "scope_local": 1}


def test_total_row_shows_checkbox_count_as_number(qapp):
    model = RegisterTableModel()
    model.setup(
        [
            ColumnDef("titlu", "text"),
            ColumnDef("format_online", "bool", count_in_total=True),
        ]
    )
    model.load_rows(
        [
            {"titlu": "A", "format_online": True},
            {"titlu": "B", "format_online": True},
            {"titlu": "C", "format_online": False},
        ],
        [1, 2, 3],
        [False, False, False],
    )
    model.set_total_rows([("Total", {"format_online": 2})])
    total_row = 3
    idx = model.index(total_row, 1)
    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "2"
    assert model.data(idx, Qt.ItemDataRole.CheckStateRole) is None
