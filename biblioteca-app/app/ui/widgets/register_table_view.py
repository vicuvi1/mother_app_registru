"""Tabel registru bazat pe QTableView + QAbstractTableModel (performant)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QInputDialog,
    QTableView,
)

from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.grouped_header import GroupedHeaderView
from ui.widgets.table.register_table_model import RegisterTableModel


class RegisterTableView(QTableView):
    """Variantă rapidă fără QTableWidgetItem — pentru coloane int/date/text."""

    cell_edited = pyqtSignal(int, str, object)
    validation_error = pyqtSignal(str)
    header_label_changed = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dataTable")
        self._columns: list[ColumnDef] = []
        self._column_keys: list[str] = []
        self._groups: list[str] = []
        self._computed_rules: dict[str, list[str]] = {}
        self._part_id = ""
        self._columns_sized = False
        self._undo_stack: list[tuple[int, int, str]] = []
        self._max_undo = 10
        self._header_labels: list[str] = []

        self._register_model = RegisterTableModel(self)
        self.setModel(self._register_model)
        self._register_model.dataChanged.connect(self._on_model_changed)
        self._register_model.validation_error.connect(self.validation_error.emit)
        self._register_model.edit_committed.connect(self._on_edit_committed)

        self._grouped_header = GroupedHeaderView(self)
        self.setHorizontalHeader(self._grouped_header)

        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.verticalHeader().setDefaultSectionSize(40)
        self.horizontalHeader().setDefaultSectionSize(88)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().sectionDoubleClicked.connect(self._edit_header_label)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_last)

    @property
    def store(self):
        return self._register_model.store

    def setup(
        self,
        columns: list[ColumnDef],
        computed_rules: dict[str, list[str]] | None = None,
        *,
        part_id: str = "",
    ) -> None:
        self._columns = list(columns)
        self._column_keys = [c.key for c in columns]
        self._groups = [c.group or "" for c in columns]
        self._computed_rules = computed_rules or {}
        self._part_id = part_id
        self._register_model.setup(columns, computed_rules, part_id=part_id)

    def set_header_labels(self, labels: list[str]) -> None:
        self._header_labels = list(labels)
        self._grouped_header.set_model_groups(labels, self._groups)

    def _edit_header_label(self, section: int) -> None:
        if section < 0 or section >= len(self._column_keys):
            return
        col_key = self._column_keys[section]
        current_text = self._header_labels[section] if section < len(self._header_labels) else col_key
        new_text, ok = QInputDialog.getText(
            self,
            "Redenumește coloana",
            f"Eticheta pentru „{col_key}”:",
            text=current_text,
        )
        if ok and new_text.strip():
            self._header_labels[section] = new_text.strip()
            self._grouped_header.set_model_groups(self._header_labels, self._groups)
            self.header_label_changed.emit(col_key, new_text.strip())

    def load_rows(
        self,
        rows: list[dict],
        row_ids: list[int | None] | None = None,
        auto_flags: list[bool] | None = None,
        resize: bool = True,
        resize_rows: bool = True,
    ) -> None:
        self._register_model.load_rows(rows, row_ids, auto_flags)
        if resize and not self._columns_sized:
            self.resize_columns_to_contents()
            self._columns_sized = True
        if resize_rows:
            for r in range(self._register_model.rowCount()):
                self.setRowHeight(r, 34 if self.store.is_total_row(r) else 40)

    def resize_columns_to_contents(self) -> None:
        self.resizeColumnsToContents()
        for i, col in enumerate(self._columns):
            min_w = 72
            max_w = 200 if col.col_type in ("text", "date") else 200
            if self.columnWidth(i) < min_w:
                self.setColumnWidth(i, min_w)
            elif self.columnWidth(i) > max_w:
                self.setColumnWidth(i, max_w)

    def rowCount(self) -> int:
        return self._register_model.rowCount()

    def is_data_row(self, row: int) -> bool:
        return not self.store.is_total_row(row)

    def visual_row_to_data_index(self, row: int) -> int | None:
        if not self.is_data_row(row):
            return None
        return row

    def currentRow(self) -> int:
        return self.currentIndex().row()

    def get_data_rows(self) -> list[dict]:
        return self.store.get_data_rows()

    def get_row_ids(self) -> list[int | None]:
        return list(self.store.row_ids)

    def get_auto_flags(self) -> list[bool]:
        return list(self.store.auto_flags)

    def compute_column_sums(self) -> dict[str, int]:
        return self.store.compute_column_sums()

    def add_total_row(self, label: str, sums: dict[str, int]) -> None:
        totals = list(self.store.total_rows)
        replaced = False
        for i, (lbl, _) in enumerate(totals):
            if lbl == label:
                totals[i] = (label, dict(sums))
                replaced = True
                break
        if not replaced:
            totals.append((label, dict(sums)))
        self._register_model.set_total_rows(totals)
        for r in range(self._register_model.rowCount()):
            self.setRowHeight(r, 34 if self.store.is_total_row(r) else 40)

    def update_totals_only(self, label: str, sums: dict[str, int]) -> None:
        self.add_total_row(label, sums)

    def set_row_ids(self, ids: list[int | None]) -> None:
        self.store.row_ids = list(ids)

    def set_row_extra(self, data_row_index: int, key: str, value: Any) -> None:
        while len(self.store.row_extra) <= data_row_index:
            self.store.row_extra.append({})
        self.store.row_extra[data_row_index][key] = value

    def append_row(self, row_data: dict, row_id: int | None = None, is_auto: bool = False) -> int:
        rows = self.get_data_rows()
        rows.append(dict(row_data))
        ids = self.get_row_ids() + [row_id]
        flags = self.get_auto_flags() + [is_auto]
        self.load_rows(rows, ids, flags, resize=False, resize_rows=True)
        return len(rows) - 1

    def insert_row_after(
        self,
        visual_row: int,
        row_data: dict,
        row_id: int | None = None,
        is_auto: bool = False,
    ) -> int:
        if not self.is_data_row(visual_row):
            return -1
        rows = self.get_data_rows()
        ids = self.get_row_ids()
        flags = self.get_auto_flags()
        insert_at = visual_row + 1
        rows.insert(insert_at, dict(row_data))
        ids.insert(insert_at, row_id)
        flags.insert(insert_at, is_auto)
        self.load_rows(rows, ids, flags, resize=False, resize_rows=True)
        return insert_at

    def refresh_preset_dropdowns(self) -> None:
        pass

    def close_all_inline_edits(self, except_cell=None) -> None:
        pass

    def close_all_preset_pickers(self, except_cell=None) -> None:
        pass

    def navigate_from_widget(self, widget, direction: str) -> None:
        pass

    def undo_last(self) -> None:
        if not self._undo_stack:
            return
        row, col, old_text = self._undo_stack.pop()
        index = self._register_model.index(row, col)
        self._register_model.setData(index, old_text)
        col_def = self._columns[col]
        if col_def.col_type == "int":
            try:
                val = max(0, int(old_text)) if old_text.strip() else 0
            except ValueError:
                val = 0
        else:
            val = old_text
        self.cell_edited.emit(row, col_def.key, val)

    def _on_edit_committed(self, row: int, col: int, old_text: str, new_text: str) -> None:
        self._push_undo(row, col, old_text, new_text)
        col_def = self._columns[col]
        if col_def.col_type == "int":
            try:
                val = max(0, int(new_text)) if new_text.strip() else 0
            except ValueError:
                val = 0
        else:
            val = new_text
        self.cell_edited.emit(row, col_def.key, val)

    def _on_model_changed(self, top_left, bottom_right, roles) -> None:
        pass

    def _push_undo(self, row: int, col: int, old_text: str, new_text: str) -> None:
        if old_text == new_text:
            return
        self._undo_stack.append((row, col, old_text))
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
