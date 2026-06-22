"""Factory — alege QTableView (rapid) sau QTableWidget (celule widget)."""

from __future__ import annotations

from ui.widgets.table.column_def import ColumnDef


def table_needs_legacy_widget(columns: list[ColumnDef]) -> bool:
    return any(c.uses_cell_widget() for c in columns)


def create_register_table(columns: list[ColumnDef]):
    if table_needs_legacy_widget(columns):
        from ui.widgets.editable_table import EditableTable

        return EditableTable()
    from ui.widgets.register_table_view import RegisterTableView

    return RegisterTableView()
