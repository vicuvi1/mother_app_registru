"""Model Qt pentru tabel registru — QAbstractTableModel peste TableDataStore."""

from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor

from ui.widgets.table.column_def import ColumnDef
from ui.widgets.table.data_store import TableDataStore

AUTO_COLOR = QColor("#dbeafe")
TOTAL_COLOR = QColor("#e2e8f0")
INVALID_COLOR = QColor("#fecaca")


class RegisterTableModel(QAbstractTableModel):
    """Model performant — fără QTableWidgetItem per celulă."""

    validation_error = pyqtSignal(str)
    edit_committed = pyqtSignal(int, int, str, str)  # row, col, old, new

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.store = TableDataStore()
        self._invalid_cells: set[tuple[int, int]] = set()

    def setup(
        self,
        columns: list[ColumnDef],
        computed_rules: dict[str, list[str]] | None = None,
        *,
        part_id: str = "",
    ) -> None:
        self.store.columns = list(columns)
        self.store.computed_rules = computed_rules or {}
        self.store.part_id = part_id

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self.store.columns)

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return self.store.row_count()

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return None
        row = section
        if self.store.is_total_row(row):
            return self.store.total_label(row)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        row, col = index.row(), index.column()
        if self.store.is_total_row(row):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        col_def = self.store.columns[col]
        if col_def.computed_from or not col_def.editable:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
        if col_def.col_type == "responsabil":
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
        if col_def.col_type in ("preset_text", "inline_text"):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        col_def = self.store.columns[col]
        if role == Qt.ItemDataRole.CheckStateRole:
            if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
                return (
                    Qt.CheckState.Checked
                    if self.store.get_cell(row, col)
                    else Qt.CheckState.Unchecked
                )
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            val = self.store.get_cell(row, col)
            if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
                return bool(val)
            if col_def.col_type == "int" or col_def.computed_from or self.store.is_total_row(row):
                return str(val)
            return str(val) if val is not None else ""
        if role == Qt.ItemDataRole.BackgroundRole:
            if (row, col) in self._invalid_cells:
                return QBrush(INVALID_COLOR)
            if self.store.is_total_row(row):
                return QBrush(TOTAL_COLOR)
            if (
                not self.store.is_total_row(row)
                and col_def.col_type == "int"
                and not col_def.computed_from
                and row < len(self.store.auto_flags)
                and self.store.auto_flags[row]
            ):
                return QBrush(AUTO_COLOR)
        if role == Qt.ItemDataRole.FontRole and col_def.col_type == "date":
            from PyQt6.QtGui import QFont

            font = QFont()
            font.setBold(True)
            return font
        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row, col = index.row(), index.column()
        if self.store.is_total_row(row):
            return False
        col_def = self.store.columns[col]
        if col_def.computed_from or not col_def.editable:
            return False

        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            old_val = bool(self.store.get_cell(row, col))
            new_val = bool(value)
            self.store.set_cell(row, col, new_val)
            if row < len(self.store.auto_flags):
                self.store.auto_flags[row] = False
            self.dataChanged.emit(index, index)
            self.edit_committed.emit(row, col, str(old_val), str(new_val))
            return True

        if col_def.col_type == "responsabil":
            old_text = str(self.store.get_cell(row, col) or "")
            new_text = str(value or "").strip()
            self.store.set_cell(row, col, new_text)
            if row < len(self.store.auto_flags):
                self.store.auto_flags[row] = False
            self.dataChanged.emit(index, index)
            self.edit_committed.emit(row, col, old_text, new_text)
            return True

        if col_def.col_type in ("preset_text", "inline_text"):
            return self.commit_widget_cell(row, col, str(value or ""))

        if col_def.col_type == "date":
            old_text = str(self.store.get_cell(row, col) or "")
            new_text = str(value or "")
            self.store.set_cell(row, col, new_text)
            if row < len(self.store.auto_flags):
                self.store.auto_flags[row] = False
            self.dataChanged.emit(index, index)
            self.edit_committed.emit(row, col, old_text, new_text)
            return True

        if col_def.col_type == "int":
            text = str(value).strip()
            old_text = str(self.store.get_cell(row, col))
            try:
                num = max(0, int(text)) if text else 0
            except ValueError:
                self._invalid_cells.add((row, col))
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.BackgroundRole])
                self.validation_error.emit("Doar numere întregi ≥ 0")
                return False
            self._invalid_cells.discard((row, col))
            self.store.set_cell(row, col, num)
            if row < len(self.store.auto_flags):
                self.store.auto_flags[row] = False
            self.store.apply_computed_row(row)
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1),
            )
            self.edit_committed.emit(row, col, old_text, str(num))
            return True

        if col_def.col_type == "text":
            old_text = str(self.store.get_cell(row, col))
            self.store.set_cell(row, col, str(value))
            if row < len(self.store.auto_flags):
                self.store.auto_flags[row] = False
            self.dataChanged.emit(index, index)
            self.edit_committed.emit(row, col, old_text, str(value))
            return True
        return False

    def load_rows(
        self,
        rows: list[dict],
        row_ids: list[int | None] | None = None,
        auto_flags: list[bool] | None = None,
    ) -> None:
        self.beginResetModel()
        self.store.total_rows.clear()
        self._invalid_cells.clear()
        self.store.set_payload(rows, row_ids, auto_flags)
        self.store.apply_computed_all()
        self.endResetModel()

    def commit_widget_cell(self, row: int, col: int, value: str) -> bool:
        """Actualizare din PresetTextCell sau alte widget-uri index."""
        if self.store.is_total_row(row):
            return False
        col_def = self.store.columns[col]
        old_text = str(self.store.get_cell(row, col) or "")
        new_text = str(value or "")
        if old_text == new_text:
            return True
        self.store.set_cell(row, col, new_text)
        if row < len(self.store.auto_flags):
            self.store.auto_flags[row] = False
        self.dataChanged.emit(
            self.index(row, col),
            self.index(row, col),
        )
        self.edit_committed.emit(row, col, old_text, new_text)
        return True

    def find_matches(self, needle: str, *, case_sensitive: bool = False) -> list[tuple[int, int]]:
        if not needle:
            return []
        hits: list[tuple[int, int]] = []
        for row in range(self.store.data_row_count()):
            for col, col_def in enumerate(self.store.columns):
                val = self.store.get_cell(row, col)
                hay = str(val if val is not None else "")
                if case_sensitive:
                    if needle in hay:
                        hits.append((row, col))
                elif needle.casefold() in hay.casefold():
                    hits.append((row, col))
        return hits

    def set_total_rows(self, totals: list[tuple[str, dict[str, int]]]) -> None:
        self.beginResetModel()
        self.store.total_rows = list(totals)
        self.endResetModel()

    def update_total(self, label: str, sums: dict[str, int]) -> None:
        for i, (lbl, _) in enumerate(self.store.total_rows):
            if lbl == label:
                self.store.total_rows[i] = (label, dict(sums))
                row = self.store.data_row_count() + i
                top_left = self.index(row, 0)
                bottom_right = self.index(row, self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right)
                return
        self.store.total_rows.append((label, dict(sums)))
        self.set_total_rows(list(self.store.total_rows))
