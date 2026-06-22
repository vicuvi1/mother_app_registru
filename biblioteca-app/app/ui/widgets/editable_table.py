"""Tabel reutilizabil cu celule editabile, totaluri auto și highlight generat."""

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QKeyEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
)

from ui.widgets.responsabil_dropdown import ResponsabilDropdown
from ui.widgets.preset_text_cell import InlineTextEdit, PresetTextCell

AUTO_COLOR = QColor("#dbeafe")
TOTAL_COLOR = QColor("#e2e8f0")
INVALID_COLOR = QColor("#fecaca")
HEADER_BG = QColor("#eef2f7")
GROUP_BG = QColor("#dbe3ee")
HEADER_BORDER = QColor("#b6c2d4")
HEADER_TEXT = QColor("#1e293b")


@dataclass
class ColumnDef:
    key: str
    col_type: str = "int"  # int, text, date, bool, responsabil, scope_local, scope_national, scope_intl
    editable: bool = True
    computed_from: list[str] | None = None
    group: str | None = None  # antet de grup (subgrupă) deasupra coloanei
    count_in_total: bool = False  # bool/scope: numără bifele bifate în rândul Total

    def counts_checked_in_total(self) -> bool:
        return self.count_in_total and (
            self.col_type == "bool" or self.col_type.startswith("scope_")
        )


class GroupedHeaderView(QHeaderView):
    """Antet pe două niveluri: bandă de grup (subgrupă) deasupra etichetei coloanei."""

    GROUP_H = 30

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._labels: list[str] = []
        self._groups: list[str] = []
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_model_groups(self, labels: list[str], groups: list[str]) -> None:
        self._labels = list(labels)
        self._groups = list(groups)
        self.updateGeometries()
        self.viewport().update()

    def has_groups(self) -> bool:
        return any(self._groups)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        h = 54
        if self.has_groups():
            h += self.GROUP_H
        return QSize(base.width(), h)

    def _draw_cell(self, painter: QPainter, rect: QRect, text: str, bg: QColor, bold: bool) -> None:
        painter.fillRect(rect, bg)
        pen = QPen(HEADER_BORDER)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        font = QFont(self.font())
        font.setBold(bold)
        font.setPointSize(8 if not bold else 8)
        painter.setFont(font)
        painter.setPen(QPen(HEADER_TEXT))
        painter.drawText(
            rect.adjusted(4, 3, -4, -3),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            text,
        )

    def paintEvent(self, event) -> None:
        if not self.has_groups():
            super().paintEvent(event)
            return

        painter = QPainter(self.viewport())
        total_h = self.height()
        group_h = self.GROUP_H
        label_h = total_h - group_h
        count = self.count()

        i = 0
        while i < count:
            grp = self._groups[i] if i < len(self._groups) else ""
            x = self.sectionViewportPosition(i)
            w = self.sectionSize(i)
            if grp:
                j = i
                span_w = 0
                while j < count and (self._groups[j] if j < len(self._groups) else "") == grp:
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(painter, QRect(gx, 0, span_w, group_h), grp, GROUP_BG, True)
                for k in range(i, j):
                    lx = self.sectionViewportPosition(k)
                    lw = self.sectionSize(k)
                    lbl = self._labels[k] if k < len(self._labels) else ""
                    self._draw_cell(painter, QRect(lx, group_h, lw, label_h), lbl, HEADER_BG, False)
                i = j
            else:
                lbl = self._labels[i] if i < len(self._labels) else ""
                self._draw_cell(painter, QRect(x, 0, w, total_h), lbl, HEADER_BG, True)
                i += 1
        painter.end()


class EditableTable(QTableWidget):
    cell_edited = pyqtSignal(int, str, object)
    validation_error = pyqtSignal(str)
    header_label_changed = pyqtSignal(str, str)  # col_key, new_label

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dataTable")
        self._columns: list[ColumnDef] = []
        self._column_keys: list[str] = []
        self._row_ids: list[int | None] = []
        self._auto_flags: list[bool] = []
        self._row_extra: list[dict] = []
        self._computed_rules: dict[str, list[str]] = {}
        self._part_id = ""
        self._updating = False

        self._grouped_header = GroupedHeaderView(self)
        self.setHorizontalHeader(self._grouped_header)

        self.cellChanged.connect(self._on_cell_changed)
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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().installEventFilter(self)
        self.cellClicked.connect(self._on_cell_clicked)
        self.verticalHeader().setDefaultSectionSize(40)
        self.horizontalHeader().setDefaultSectionSize(88)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().sectionDoubleClicked.connect(self._edit_header_label)
        self.setWordWrap(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def is_data_row(self, row: int) -> bool:
        vh = self.verticalHeaderItem(row)
        return not (vh and vh.text() in ("Total", "Total de la început"))

    def visual_row_to_data_index(self, row: int) -> int | None:
        if not self.is_data_row(row):
            return None
        idx = 0
        for r in range(row):
            if self.is_data_row(r):
                idx += 1
        return idx

    def keyPressEvent(self, event: QKeyEvent) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, (PresetTextCell, InlineTextEdit)):
            super().keyPressEvent(event)
            return
        parent = fw.parentWidget() if fw is not None else None
        if isinstance(parent, PresetTextCell):
            super().keyPressEvent(event)
            return
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key.Key_Tab:
            self.close_all_inline_edits()
            row, col = self.currentRow(), self.currentColumn()
            direction = "back" if mods & Qt.KeyboardModifier.ShiftModifier else "forward"
            self._navigate(row, col, direction)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close_all_inline_edits()
            row, col = self.currentRow(), self.currentColumn()
            self._navigate(row, col, "down")
            event.accept()
            return
        super().keyPressEvent(event)

    def navigate_from_widget(self, widget, direction: str) -> None:
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                if self.cellWidget(r, c) is widget:
                    self._navigate(r, c, direction)
                    return

    def _is_navigable(self, row: int, col: int) -> bool:
        if col < 0 or col >= len(self._columns):
            return False
        if not self.is_data_row(row):
            return False
        col_def = self._columns[col]
        return col_def.editable and not col_def.computed_from

    def _navigable_cells(self) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        for r in range(self.rowCount()):
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
        self.setCurrentCell(row, col)
        item = self.item(row, col)
        if item is not None:
            self.scrollToItem(item)
        col_def = self._columns[col]
        w = self.cellWidget(row, col)
        if isinstance(w, PresetTextCell):
            if col_def.col_type == "inline_text":
                QTimer.singleShot(0, w.start_inline_edit)
            else:
                QTimer.singleShot(0, w.open_picker)
        elif isinstance(w, ResponsabilDropdown):
            w.setFocus()
            QTimer.singleShot(0, w.showPopup)
        elif isinstance(w, QCheckBox):
            w.setFocus()
        else:
            QTimer.singleShot(0, lambda r=row, c=col: self._edit_index(self.model().index(r, c)))

    def setup(
        self,
        columns: list[ColumnDef],
        computed_rules: dict[str, list[str]] | None = None,
        part_id: str = "",
    ) -> None:
        self._part_id = part_id
        self._columns = columns
        self._column_keys = [c.key for c in columns]
        self._groups = [c.group or "" for c in columns]
        self._computed_rules = computed_rules or {}
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([c.key for c in columns])
        self._grouped_header.set_model_groups([c.key for c in columns], self._groups)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.viewport():
            et = event.type()
            if et == QEvent.Type.MouseButtonRelease:
                pos = event.position().toPoint()
                index = self.indexAt(pos)
                if not index.isValid():
                    return False
                row, col = index.row(), index.column()
                if col < 0 or col >= len(self._columns):
                    return False
                vh = self.verticalHeaderItem(row)
                if vh and vh.text() in ("Total", "Total de la început"):
                    return False
                col_def = self._columns[col]
                w = self.cellWidget(row, col)

                if event.button() == Qt.MouseButton.LeftButton:
                    if (
                        col_def.col_type in ("preset_text", "inline_text")
                        and isinstance(w, PresetTextCell)
                    ):
                        self.close_all_inline_edits(
                            except_cell=w if col_def.col_type == "inline_text" else None
                        )
                    else:
                        self.close_all_inline_edits()

                if col_def.col_type in ("preset_text", "inline_text") and isinstance(w, PresetTextCell):
                    if event.button() == Qt.MouseButton.RightButton and col_def.col_type == "preset_text":
                        w._suppress_open = True
                        w.close_picker()
                        QTimer.singleShot(0, w.start_inline_edit)
                        QTimer.singleShot(300, lambda cell=w: setattr(cell, "_suppress_open", False))
                        return True
                    if event.button() == Qt.MouseButton.LeftButton and not w.is_editing():
                        if col_def.col_type == "inline_text":
                            QTimer.singleShot(0, w.start_inline_edit)
                        elif not w.is_editing():
                            QTimer.singleShot(0, w.open_picker)
                elif (
                    event.button() == Qt.MouseButton.LeftButton
                    and col_def.col_type == "responsabil"
                    and isinstance(w, ResponsabilDropdown)
                ):
                    QTimer.singleShot(0, w.showPopup)
                elif (
                    event.button() == Qt.MouseButton.LeftButton
                    and w is None
                    and col_def.col_type in ("int", "date", "text")
                    and col_def.editable
                    and not col_def.computed_from
                ):
                    idx = self.model().index(row, col)
                    QTimer.singleShot(0, lambda i=idx: self._edit_index(i))
        return super().eventFilter(obj, event)

    def _edit_index(self, index) -> None:
        if index.isValid():
            self.setCurrentIndex(index)
            self.edit(index)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col < 0 or col >= len(self._columns):
            return
        vh = self.verticalHeaderItem(row)
        if vh and vh.text() in ("Total", "Total de la început"):
            return
        col_def = self._columns[col]
        w = self.cellWidget(row, col)
        if w is not None:
            return
        if (
            col_def.col_type in ("int", "date", "text")
            and col_def.editable
            and not col_def.computed_from
        ):
            self.close_all_inline_edits()
            idx = self.model().index(row, col)
            QTimer.singleShot(0, lambda i=idx: self._edit_index(i))

    def close_all_inline_edits(self, except_cell: PresetTextCell | None = None) -> None:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            for c, col in enumerate(self._columns):
                if col.col_type not in ("preset_text", "inline_text"):
                    continue
                w = self.cellWidget(r, c)
                if isinstance(w, PresetTextCell) and w is not except_cell and w.is_editing():
                    w._finish_inline_edit()

    def close_all_preset_pickers(self, except_cell: PresetTextCell | None = None) -> None:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            for c, col in enumerate(self._columns):
                if col.col_type not in ("preset_text", "inline_text"):
                    continue
                w = self.cellWidget(r, c)
                if isinstance(w, PresetTextCell) and w is not except_cell:
                    w.close_picker()

    def set_header_labels(self, labels: list[str]) -> None:
        self.setHorizontalHeaderLabels(labels)
        self._grouped_header.set_model_groups(labels, getattr(self, "_groups", []))

    def _edit_header_label(self, section: int) -> None:
        if section < 0 or section >= len(self._column_keys):
            return
        col_key = self._column_keys[section]
        current = self.horizontalHeaderItem(section)
        current_text = current.text() if current else col_key
        new_text, ok = QInputDialog.getText(
            self,
            "Redenumește coloana",
            f"Eticheta pentru „{col_key}”:",
            text=current_text,
        )
        if ok and new_text.strip():
            self.setHorizontalHeaderItem(section, QTableWidgetItem(new_text.strip()))
            labels = [
                self.horizontalHeaderItem(i).text() if self.horizontalHeaderItem(i) else ""
                for i in range(self.columnCount())
            ]
            self._grouped_header.set_model_groups(labels, getattr(self, "_groups", []))
            self.header_label_changed.emit(col_key, new_text.strip())

    def resize_columns_to_contents(self) -> None:
        self.resizeColumnsToContents()
        for i, col in enumerate(self._columns):
            min_w = 100 if col.col_type in ("preset_text", "inline_text") else 72
            max_w = 260 if col.col_type in ("preset_text", "inline_text", "text") else 200
            if self.columnWidth(i) < min_w:
                self.setColumnWidth(i, min_w)
            elif self.columnWidth(i) > max_w:
                self.setColumnWidth(i, max_w)

    def _split_row_data(self, row_data: dict) -> tuple[dict, dict]:
        visible = {k: row_data.get(k) for k in self._column_keys if k in row_data}
        extra = {k: v for k, v in row_data.items() if k not in self._column_keys}
        return visible, extra

    def load_rows(
        self,
        rows: list[dict],
        row_ids: list[int | None] | None = None,
        auto_flags: list[bool] | None = None,
        resize: bool = True,
    ) -> None:
        self.setUpdatesEnabled(False)
        self._updating = True
        self.blockSignals(True)
        self.setRowCount(len(rows))
        self._row_ids = row_ids or [None] * len(rows)
        self._auto_flags = auto_flags or [False] * len(rows)
        self._row_extra = []

        for r, row_data in enumerate(rows):
            is_auto = self._auto_flags[r] if r < len(self._auto_flags) else False
            _, extra = self._split_row_data(row_data)
            self._row_extra.append(extra)
            for c, col in enumerate(self._columns):
                val = row_data.get(col.key)
                self._set_cell(r, c, col, val, is_auto)

        self.blockSignals(False)
        self._updating = False
        self._apply_computed_all()
        self._refresh_styles()
        if resize:
            self.resize_columns_to_contents()
        self._resize_content_rows()
        self.setUpdatesEnabled(True)

    def _resize_content_rows(self) -> None:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                self.setRowHeight(r, 34)
                continue
            self.resizeRowToContents(r)
            if self.rowHeight(r) < 40:
                self.setRowHeight(r, 40)

    def append_row(
        self,
        row_data: dict,
        row_id: int | None = None,
        is_auto: bool = False,
    ) -> int:
        r = self.rowCount()
        self.insertRow(r)
        self._row_ids.append(row_id)
        self._auto_flags.append(is_auto)
        _, extra = self._split_row_data(row_data)
        self._row_extra.append(extra)
        for c, col in enumerate(self._columns):
            self._set_cell(r, c, col, row_data.get(col.key), is_auto)
        self._apply_computed_row(r)
        self._resize_content_rows()
        return r

    def insert_row_after(
        self,
        visual_row: int,
        row_data: dict,
        row_id: int | None = None,
        is_auto: bool = False,
    ) -> int:
        if not self.is_data_row(visual_row):
            return -1
        data_idx = self.visual_row_to_data_index(visual_row)
        if data_idx is None:
            return -1
        insert_at = visual_row + 1
        self.insertRow(insert_at)
        self._row_ids.insert(data_idx + 1, row_id)
        self._auto_flags.insert(data_idx + 1, is_auto)
        _, extra = self._split_row_data(row_data)
        self._row_extra.insert(data_idx + 1, extra)
        for c, col in enumerate(self._columns):
            self._set_cell(insert_at, c, col, row_data.get(col.key), is_auto)
        self._apply_computed_row(insert_at)
        self._resize_content_rows()
        return insert_at

    def set_row_extra(self, data_row_index: int, key: str, value: Any) -> None:
        while len(self._row_extra) <= data_row_index:
            self._row_extra.append({})
        self._row_extra[data_row_index][key] = value

    def remove_row(self, row: int) -> None:
        if 0 <= row < self.rowCount():
            self.removeRow(row)
            if row < len(self._row_ids):
                del self._row_ids[row]
            if row < len(self._auto_flags):
                del self._auto_flags[row]
            if row < len(self._row_extra):
                del self._row_extra[row]

    def _find_total_row(self, label: str) -> int:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() == label:
                return r
        return -1

    def add_total_row(self, label: str, sums: dict[str, int]) -> None:
        """Adaugă sau actualizează rândul Total — mereu la finalul tabelului."""
        self._updating = True
        r = self._find_total_row(label)
        if r >= 0:
            self.removeRow(r)
        r = self.rowCount()
        self.insertRow(r)
        self.setVerticalHeaderItem(r, QTableWidgetItem(label))

        for c, col in enumerate(self._columns):
            if (
                col.col_type == "int"
                or col.computed_from
                or col.counts_checked_in_total()
            ):
                val = sums.get(col.key, 0)
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QBrush(TOTAL_COLOR))
                self.setItem(r, c, item)
            elif c == 0:
                item = QTableWidgetItem(label)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QBrush(TOTAL_COLOR))
                self.setItem(r, c, item)
            else:
                item = QTableWidgetItem("")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QBrush(TOTAL_COLOR))
                self.setItem(r, c, item)
        self._updating = False

    def get_data_rows(self) -> list[dict]:
        """Returnează datele fără rândurile Total."""
        rows = []
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            row = {}
            for c, col in enumerate(self._columns):
                row[col.key] = self._get_cell_value(r, c, col)
            data_idx = len(rows)
            if data_idx < len(self._row_extra):
                row.update(self._row_extra[data_idx])
            rows.append(row)
        return rows

    def get_row_ids(self) -> list[int | None]:
        result = []
        data_idx = 0
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            if data_idx < len(self._row_ids):
                result.append(self._row_ids[data_idx])
            else:
                result.append(None)
            data_idx += 1
        return result

    def get_auto_flags(self) -> list[bool]:
        result = []
        data_idx = 0
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            result.append(self._auto_flags[data_idx] if data_idx < len(self._auto_flags) else False)
            data_idx += 1
        return result

    def compute_column_sums(self) -> dict[str, int]:
        sums: dict[str, int] = {}
        for col in self._columns:
            if col.counts_checked_in_total():
                total = 0
                for r in range(self.rowCount()):
                    vh = self.verticalHeaderItem(r)
                    if vh and vh.text() in ("Total", "Total de la început"):
                        continue
                    val = self._get_cell_value(r, self._columns.index(col), col)
                    if val:
                        total += 1
                sums[col.key] = total
                continue
            if col.col_type != "int" and not col.computed_from:
                continue
            total = 0
            for r in range(self.rowCount()):
                vh = self.verticalHeaderItem(r)
                if vh and vh.text() in ("Total", "Total de la început"):
                    continue
                val = self._get_cell_value(r, self._columns.index(col), col)
                if isinstance(val, int):
                    total += val
            sums[col.key] = total
        return sums

    def update_totals_only(self, label: str, sums: dict[str, int]) -> None:
        """Actualizează rândul Total fără a reîncărca datele."""
        self.add_total_row(label, sums)

    def set_row_ids(self, ids: list[int | None]) -> None:
        self._row_ids = ids

    def mark_row_manual(self, row: int) -> None:
        if row < len(self._auto_flags):
            self._auto_flags[row] = False
            self._refresh_row_style(row)

    def _editable_item_flags(self) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def _set_cell(self, row: int, col: int, col_def: ColumnDef, val, is_auto: bool) -> None:
        if col_def.col_type == "date":
            item = QTableWidgetItem(str(val or ""))
            if not col_def.editable:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(self._editable_item_flags())
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self.setItem(row, col, item)
        elif col_def.col_type == "int":
            if col_def.computed_from:
                item = QTableWidgetItem(str(val if val is not None else 0))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QBrush(TOTAL_COLOR))
            else:
                item = QTableWidgetItem(str(val if val is not None else 0))
                if col_def.editable:
                    item.setFlags(self._editable_item_flags())
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, col, item)
        elif col_def.col_type == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(val))
            cb.stateChanged.connect(lambda _s, rw=row, k=col_def.key: self._bool_changed(rw, k))
            if not col_def.editable:
                cb.setEnabled(False)
            self.setCellWidget(row, col, cb)
        elif col_def.col_type == "responsabil":
            dd = ResponsabilDropdown()
            dd.set_value(str(val or ""))
            dd.currentTextChanged.connect(
                lambda _t, rw=row, k=col_def.key: self._widget_changed(rw, k)
            )
            self.setCellWidget(row, col, dd)
        elif col_def.col_type == "preset_text":
            cell = PresetTextCell(self._part_id, col_def.key, picker_on_click=True)
            cell.set_value(str(val or ""))
            cell.value_changed.connect(
                lambda rw=row, k=col_def.key: self._widget_changed(rw, k)
            )
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.setCellWidget(row, col, cell)
        elif col_def.col_type == "inline_text":
            cell = PresetTextCell(self._part_id, col_def.key, picker_on_click=False)
            cell.set_value(str(val or ""))
            cell.value_changed.connect(
                lambda rw=row, k=col_def.key: self._widget_changed(rw, k)
            )
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.setCellWidget(row, col, cell)
        elif col_def.col_type in ("scope_local", "scope_national", "scope_intl"):
            cb = QCheckBox()
            cb.setChecked(bool(val))
            cb.stateChanged.connect(lambda _s, rw=row, k=col_def.key: self._bool_changed(rw, k))
            self.setCellWidget(row, col, cb)
        else:
            item = QTableWidgetItem(str(val or ""))
            if col_def.editable:
                item.setFlags(self._editable_item_flags())
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col_def.col_type in ("text", "date"):
                item.setTextAlignment(
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                )
            self.setItem(row, col, item)

        if is_auto and col_def.col_type == "int" and not col_def.computed_from:
            item = self.item(row, col)
            if item:
                item.setBackground(QBrush(AUTO_COLOR))

    def _get_cell_value(self, row: int, col: int, col_def: ColumnDef):
        if col_def.col_type == "bool" or col_def.col_type.startswith("scope_"):
            w = self.cellWidget(row, col)
            if isinstance(w, QCheckBox):
                return w.isChecked()
            return False
        if col_def.col_type == "responsabil":
            w = self.cellWidget(row, col)
            if isinstance(w, ResponsabilDropdown):
                return w.value()
            return ""
        if col_def.col_type == "preset_text" or col_def.col_type == "inline_text":
            w = self.cellWidget(row, col)
            if isinstance(w, PresetTextCell):
                return w.value()
            return ""
        item = self.item(row, col)
        if item is None:
            return 0 if col_def.col_type == "int" else ""
        text = item.text().strip()
        if col_def.col_type == "int":
            try:
                return max(0, int(text))
            except ValueError:
                return 0
        return text

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._updating:
            return
        vh = self.verticalHeaderItem(row)
        if vh and vh.text() in ("Total", "Total de la început"):
            return

        col_def = self._columns[col]
        if col_def.computed_from or not col_def.editable:
            return

        item = self.item(row, col)
        if item is None:
            return

        if col_def.col_type == "int":
            text = item.text().strip()
            try:
                val = max(0, int(text)) if text else 0
                self._updating = True
                item.setText(str(val))
                item.setBackground(QBrush(Qt.GlobalColor.white))
                self._updating = False
            except ValueError:
                item.setBackground(QBrush(INVALID_COLOR))
                self.validation_error.emit("Doar numere întregi ≥ 0")
                return
        elif col_def.col_type == "text":
            val = item.text()
        else:
            return

        if row < len(self._auto_flags):
            self._auto_flags[row] = False
            item.setBackground(QBrush(Qt.GlobalColor.white))

        if col_def.col_type == "int":
            self._apply_computed_row(row)
        self.cell_edited.emit(row, col_def.key, val)

    def _bool_changed(self, row: int, key: str) -> None:
        if self._updating:
            return
        if row < len(self._auto_flags):
            self._auto_flags[row] = False
        self.cell_edited.emit(row, key, self._get_cell_value(row, self._col_index(key), self._columns[self._col_index(key)]))

    def _widget_changed(self, row: int, key: str) -> None:
        if self._updating:
            return
        idx = self._col_index(key)
        w = self.cellWidget(row, idx)
        if w is None:
            return
        try:
            if isinstance(w, ResponsabilDropdown):
                w.commit_new_name()
            elif isinstance(w, PresetTextCell):
                w.commit_new_value()
        except RuntimeError:
            return
        if row < len(self._auto_flags):
            self._auto_flags[row] = False
        self.cell_edited.emit(row, key, self._get_cell_value(row, idx, self._columns[idx]))
        QTimer.singleShot(0, self._resize_content_rows)

    def _col_index(self, key: str) -> int:
        for i, c in enumerate(self._columns):
            if c.key == key:
                return i
        return 0

    def refresh_preset_dropdowns(self) -> None:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            for c, col in enumerate(self._columns):
                if col.col_type not in ("preset_text", "inline_text"):
                    continue
                w = self.cellWidget(r, c)
                if isinstance(w, PresetTextCell):
                    w.refresh()
        self._resize_content_rows()

    def _apply_computed_all(self) -> None:
        for r in range(self.rowCount()):
            vh = self.verticalHeaderItem(r)
            if vh and vh.text() in ("Total", "Total de la început"):
                continue
            self._apply_computed_row(r)

    def _apply_computed_row(self, row: int) -> None:
        self._updating = True
        for col_def in self._columns:
            if not col_def.computed_from:
                continue
            total = 0
            for src in col_def.computed_from:
                src_idx = self._col_index(src)
                val = self._get_cell_value(row, src_idx, self._columns[src_idx])
                if isinstance(val, int):
                    total += val
            c_idx = self._col_index(col_def.key)
            item = self.item(row, c_idx)
            if item is None:
                item = QTableWidgetItem(str(total))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QBrush(TOTAL_COLOR))
                self.setItem(row, c_idx, item)
            else:
                item.setText(str(total))
        self._updating = False

    def _refresh_styles(self) -> None:
        for r in range(self.rowCount()):
            self._refresh_row_style(r)

    def _refresh_row_style(self, row: int) -> None:
        is_auto = self._auto_flags[row] if row < len(self._auto_flags) else False
        for c, col in enumerate(self._columns):
            if col.col_type != "int" or col.computed_from:
                continue
            item = self.item(row, c)
            if item and is_auto:
                item.setBackground(QBrush(AUTO_COLOR))
            elif item:
                item.setBackground(QBrush(Qt.GlobalColor.white))
