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


def test_preset_text_display_role_hidden_from_cell_paint(qapp):
    from ui.widgets.table.column_def import ColumnDef
    from ui.widgets.table.register_table_model import RegisterTableModel

    cols = [ColumnDef("tema_instruirii", "preset_text")]
    model = RegisterTableModel()
    model.setup(cols)
    model.load_rows([{"tema_instruirii": "Clubul de dame"}])
    idx = model.index(0, 0)
    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == ""
    assert model.data(idx, Qt.ItemDataRole.EditRole) == "Clubul de dame"


def test_part04_total_stays_fixed_when_czu_edited(qapp):
    from ui.part_04_documente_continut import COLUMNS, CZU

    model = RegisterTableModel()
    model.setup(COLUMNS)
    row = {"data": "25.06", "total_imprumuturi": 17}
    for key in CZU:
        row[key] = 0
    model.load_rows([row])

    czu_col = next(i for i, c in enumerate(COLUMNS) if c.key == "czu_1_filozofie")
    total_col = next(i for i, c in enumerate(COLUMNS) if c.key == "total_imprumuturi")

    assert model.setData(model.index(0, czu_col), 7, Qt.ItemDataRole.EditRole)
    assert model.data(model.index(0, total_col), Qt.ItemDataRole.DisplayRole) == "17"
    assert model.store.get_data_rows()[0]["czu_1_filozofie"] == 7


def test_part04_czu_editable_when_total_zero(qapp):
    from core.part_sync import part04_row_total, validate_part04_czu_value
    from ui.part_04_documente_continut import COLUMNS, CZU

    model = RegisterTableModel()
    model.setup(COLUMNS)

    def validator(row, key, val):
        trial = {"total_imprumuturi": 0, **{k: 0 for k in CZU}, key: val}
        return validate_part04_czu_value(trial, key, val)

    model.set_cell_validator(validator)
    row = {"data": "05.02", "total_imprumuturi": 0}
    for key in CZU:
        row[key] = 0
    model.load_rows([row])

    czu_col = next(i for i, c in enumerate(COLUMNS) if c.key == "czu_1_filozofie")
    assert model.setData(model.index(0, czu_col), 7, Qt.ItemDataRole.EditRole)
    data = model.store.get_data_rows()[0]
    assert data["czu_1_filozofie"] == 7
    assert part04_row_total(data, 0) == 7


def test_part04_total_column_is_not_directly_editable(qapp):
    from ui.part_04_documente_continut import COLUMNS, CZU

    model = RegisterTableModel()
    model.setup(COLUMNS)
    row = {"data": "25.06", "total_imprumuturi": 17, "czu_0_generalitati": 4}
    for key in CZU:
        row.setdefault(key, 0)
    model.load_rows([row])

    total_col = next(i for i, c in enumerate(COLUMNS) if c.key == "total_imprumuturi")
    assert not model.setData(model.index(0, total_col), 99, Qt.ItemDataRole.EditRole)
    assert model.data(model.index(0, total_col), Qt.ItemDataRole.DisplayRole) == "17"
