"""Teste TableDataStore, factory și delegați."""

from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.data_store import TableDataStore
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
