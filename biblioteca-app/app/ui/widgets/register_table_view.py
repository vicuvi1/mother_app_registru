"""Tabel registru bazat pe QTableView + QAbstractTableModel (performant)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QKeyEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QInputDialog,
    QSizePolicy,
    QTableView,
)

from ui.widgets.preset_text_cell import PresetTextCell
from ui.widgets.table_find_bar import TableFindBar
from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.delegates.checkbox_delegate import CheckBoxDelegate
from ui.widgets.table.delegates.responsabil_delegate import ResponsabilDelegate
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
        self._preset_cells: list[PresetTextCell] = []
        self._find_bar: TableFindBar | None = None
        self._find_matches: list[tuple[int, int]] = []
        self._find_pos = -1
        self._checkbox_delegate = CheckBoxDelegate(self)
        self._responsabil_delegate = ResponsabilDelegate(self)

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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_last)
        QShortcut(QKeySequence("Ctrl+F"), self, self.open_find)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_selection)
        QShortcut(QKeySequence("Ctrl+V"), self, self.paste_from_clipboard)

    def attach_find_bar(self, bar: TableFindBar) -> None:
        self._find_bar = bar
        bar.find_next.connect(self.find_next)
        bar.find_previous.connect(self.find_previous)
        bar.search_changed.connect(self._refresh_find_matches)
        bar.closed.connect(self._clear_find_highlight)

    def open_find(self) -> None:
        if self._find_bar is None:
            return
        self._find_bar.show()
        self._find_bar.focus_search()
        self._refresh_find_matches()

    def _refresh_find_matches(self, _needle: str = "", _case: bool = False) -> None:
        if self._find_bar is None:
            return
        needle = self._find_bar.needle()
        case = self._find_bar.case_sensitive()
        self._find_matches = self._register_model.find_matches(needle, case_sensitive=case)
        self._find_pos = -1
        if needle and self._find_matches:
            self.find_next()

    def find_next(self) -> None:
        if not self._find_matches:
            return
        self._find_pos = (self._find_pos + 1) % len(self._find_matches)
        self._focus_find_match()

    def find_previous(self) -> None:
        if not self._find_matches:
            return
        self._find_pos = (self._find_pos - 1) % len(self._find_matches)
        self._focus_find_match()

    def _focus_find_match(self) -> None:
        if self._find_pos < 0 or self._find_pos >= len(self._find_matches):
            return
        row, col = self._find_matches[self._find_pos]
        index = self._register_model.index(row, col)
        self.setCurrentIndex(index)
        self.scrollTo(index)

    def _clear_find_highlight(self) -> None:
        self._find_matches.clear()
        self._find_pos = -1

    def copy_selection(self) -> None:
        index = self.currentIndex()
        if not index.isValid() or not self.is_data_row(index.row()):
            return
        val = self._register_model.data(index, Qt.ItemDataRole.DisplayRole)
        QGuiApplication.clipboard().setText(str(val if val is not None else ""))

    def paste_from_clipboard(self) -> None:
        text = QGuiApplication.clipboard().text()
        if not text.strip():
            return
        start = self.currentIndex()
        if not start.isValid():
            return
        start_row = start.row() if self.is_data_row(start.row()) else 0
        start_col = max(0, start.column())
        lines = [ln for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if ln is not None]
        if not lines:
            return

        data_rows = self.get_data_rows()
        ids = self.get_row_ids()
        flags = self.get_auto_flags()
        changed = False

        for dr, line in enumerate(lines):
            row = start_row + dr
            if row >= self._register_model.store.data_row_count():
                if getattr(self, "_allow_paste_extend", False):
                    blank = {c.key: self._default_cell_value(c) for c in self._columns}
                    data_rows.append(blank)
                    ids.append(None)
                    flags.append(False)
                    row = len(data_rows) - 1
                else:
                    break
            cells = line.split("\t")
            for dc, raw in enumerate(cells):
                col = start_col + dc
                if col >= len(self._columns):
                    break
                col_def = self._columns[col]
                if not col_def.editable or col_def.computed_from:
                    continue
                parsed = self._parse_paste_value(col_def, raw)
                if parsed is None:
                    continue
                data_rows[row][col_def.key] = parsed
                changed = True

        if not changed:
            return
        self.load_rows(data_rows, ids, flags, resize=False, resize_rows=True)
        for dr, line in enumerate(lines):
            row = start_row + dr
            if row >= self._register_model.store.data_row_count():
                break
            for dc, raw in enumerate(line.split("\t")):
                col = start_col + dc
                if col >= len(self._columns):
                    break
                col_def = self._columns[col]
                if not col_def.editable or col_def.computed_from:
                    continue
                parsed = self._parse_paste_value(col_def, raw)
                if parsed is not None:
                    self.cell_edited.emit(row, col_def.key, parsed)

    def _default_cell_value(self, col_def: ColumnDef):
        if col_def.col_type == "int":
            return 0
        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            return False
        return ""

    def _parse_paste_value(self, col_def: ColumnDef, raw: str):
        text = raw.strip()
        if col_def.col_type == "int":
            try:
                return max(0, int(text)) if text else 0
            except ValueError:
                self.validation_error.emit("Lipire: doar numere întregi ≥ 0")
                return None
        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            low = text.casefold()
            if low in ("1", "da", "true", "x", "✓"):
                return True
            if low in ("0", "nu", "false", ""):
                return False
            return None
        if col_def.col_type in ("date", "text", "responsabil", "preset_text", "inline_text"):
            return text
        return text

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
        self._install_delegates()

    def _install_delegates(self) -> None:
        for c, col in enumerate(self._columns):
            if col.col_type in ("bool",) or col.col_type.startswith("scope_"):
                self.setItemDelegateForColumn(c, self._checkbox_delegate)
            elif col.col_type == "responsabil":
                self.setItemDelegateForColumn(c, self._responsabil_delegate)

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
        self._sync_preset_widgets()
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

    def _sync_preset_widgets(self) -> None:
        self._preset_cells.clear()
        for r in range(self._register_model.store.data_row_count()):
            for c, col in enumerate(self._columns):
                if col.col_type not in ("preset_text", "inline_text"):
                    continue
                idx = self._register_model.index(r, c)
                cell = PresetTextCell(
                    self._part_id,
                    col.key,
                    parent=self,
                    picker_on_click=col.col_type == "preset_text",
                )
                cell.set_value(str(self._register_model.data(idx, Qt.ItemDataRole.DisplayRole) or ""))
                cell.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
                cell.value_changed.connect(
                    lambda _v, row=r, col_idx=c: self._on_preset_changed(row, col_idx)
                )
                self.setIndexWidget(idx, cell)
                self._preset_cells.append(cell)

    def _on_preset_changed(self, row: int, col: int) -> None:
        cell = self.sender()
        if not isinstance(cell, PresetTextCell):
            return
        self._register_model.commit_widget_cell(row, col, cell.value())

    def refresh_preset_dropdowns(self) -> None:
        for cell in self._preset_cells:
            cell.refresh()

    def close_all_inline_edits(self, except_cell: PresetTextCell | None = None) -> None:
        for cell in self._preset_cells:
            if cell is not except_cell and cell.is_editing():
                cell._finish_inline_edit()

    def close_all_preset_pickers(self, except_cell: PresetTextCell | None = None) -> None:
        for cell in self._preset_cells:
            if cell is not except_cell:
                cell.close_picker()

    def navigate_from_widget(self, widget, direction: str) -> None:
        for r in range(self._register_model.store.data_row_count()):
            for c, col in enumerate(self._columns):
                if col.col_type not in ("preset_text", "inline_text"):
                    continue
                idx = self._register_model.index(r, c)
                if self.indexWidget(idx) is widget:
                    self._navigate(r, c, direction)
                    return

    def keyPressEvent(self, event: QKeyEvent) -> None:
        fw = QApplication.focusWidget()
        if fw is not None:
            parent = fw.parentWidget()
            if isinstance(fw, PresetTextCell) or isinstance(parent, PresetTextCell):
                super().keyPressEvent(event)
                return
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key.Key_Tab:
            self.close_all_inline_edits()
            row, col = self.currentIndex().row(), self.currentIndex().column()
            direction = "back" if mods & Qt.KeyboardModifier.ShiftModifier else "forward"
            self._navigate(row, col, direction)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close_all_inline_edits()
            row, col = self.currentIndex().row(), self.currentIndex().column()
            self._navigate(row, col, "down")
            event.accept()
            return
        super().keyPressEvent(event)

    def _is_navigable(self, row: int, col: int) -> bool:
        if col < 0 or col >= len(self._columns):
            return False
        if not self.is_data_row(row):
            return False
        col_def = self._columns[col]
        return col_def.editable and not col_def.computed_from

    def _navigable_cells(self) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        for r in range(self._register_model.rowCount()):
            if not self.is_data_row(r):
                continue
            for c in range(len(self._columns)):
                if self._is_navigable(r, c):
                    cells.append((r, c))
        return cells

    def _navigate(self, row: int, col: int, direction: str) -> None:
        cells = self._navigable_cells()
        if not cells:
            return
        try:
            idx = cells.index((row, col))
        except ValueError:
            idx = 0
        if direction == "forward":
            idx = min(idx + 1, len(cells) - 1)
        elif direction == "back":
            idx = max(idx - 1, 0)
        else:
            next_idx = None
            for i in range(idx + 1, len(cells)):
                if cells[i][1] == col:
                    next_idx = i
                    break
            idx = next_idx if next_idx is not None else min(idx + 1, len(cells) - 1)
        nr, nc = cells[idx]
        self._activate_cell(nr, nc)

    def _activate_cell(self, row: int, col: int) -> None:
        index = self._register_model.index(row, col)
        self.setCurrentIndex(index)
        col_def = self._columns[col]
        widget = self.indexWidget(index)
        if isinstance(widget, PresetTextCell):
            if col_def.col_type == "inline_text":
                QTimer.singleShot(0, widget.start_inline_edit)
            else:
                QTimer.singleShot(0, widget.open_picker)
        elif col_def.col_type == "responsabil":
            self.edit(index)
        elif col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            self.setFocus()
        else:
            QTimer.singleShot(0, lambda i=index: self.edit(i))

    def undo_last(self) -> None:
        if not self._undo_stack:
            return
        row, col, old_text = self._undo_stack.pop()
        index = self._register_model.index(row, col)
        col_def = self._columns[col]
        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            self._register_model.setData(
                index, old_text.lower() in ("true", "1"), Qt.ItemDataRole.EditRole
            )
        else:
            self._register_model.setData(index, old_text)
        widget = self.indexWidget(index)
        if isinstance(widget, PresetTextCell):
            widget.set_value(old_text)
        if col_def.col_type == "int":
            try:
                val = max(0, int(old_text)) if old_text.strip() else 0
            except ValueError:
                val = 0
        elif col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            val = old_text.lower() in ("true", "1")
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
        elif col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            val = new_text.lower() in ("true", "1")
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
