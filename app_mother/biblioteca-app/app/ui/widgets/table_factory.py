"""Factory — tabel registru bazat pe QTableView (toate tipurile de coloane)."""

from __future__ import annotations

from ui.widgets.table.column_def import ColumnDef


def table_needs_legacy_widget(columns: list[ColumnDef]) -> bool:
    """Păstrat pentru compatibilitate teste — delegații acoperă toate tipurile."""
    return False


def create_register_table(columns: list[ColumnDef]):
    from ui.widgets.register_table_view import RegisterTableView

    return RegisterTableView()
