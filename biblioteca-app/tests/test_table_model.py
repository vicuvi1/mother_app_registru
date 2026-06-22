"""Teste TableDataStore și model tabel."""

from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.data_store import TableDataStore
from ui.widgets.table_factory import table_needs_legacy_widget


def test_table_needs_legacy_for_bool():
    cols = [ColumnDef("x", "bool")]
    assert table_needs_legacy_widget(cols) is True


def test_table_store_sums():
    store = TableDataStore()
    store.columns = [ColumnDef("a", "int"), ColumnDef("b", "int")]
    store.set_payload([{"a": 1, "b": 2}, {"a": 3, "b": 4}], [1, 2], [False, False])
    sums = store.compute_column_sums()
    assert sums == {"a": 4, "b": 6}
