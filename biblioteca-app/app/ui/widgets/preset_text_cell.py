"""Celulă text: click stânga = listă, click dreapta = scriere direct în celulă."""

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import get_all_etichete, get_text_presets


def _widget_alive(widget: QWidget | None) -> bool:
    if widget is None:
        return False
    try:
        widget.objectName()
        return True
    except RuntimeError:
        return False


class InlineTextEdit(QTextEdit):
    """Editor în celulă — Tab/Enter confirmă și navighează, Shift+Enter linie nouă."""

    finished = pyqtSignal()
    cancelled = pyqtSignal()
    navigate = pyqtSignal(str)

    def __init__(self, cell: "PresetTextCell | None" = None, parent=None) -> None:
        super().__init__(parent)
        self._cell = cell
        self.setObjectName("presetInlineEdit")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            "QTextEdit#presetInlineEdit {"
            "  background: #ffffff;"
            "  border: 2px solid #2563eb;"
            "  border-radius: 4px;"
            "  padding: 4px;"
            "  color: #1e293b;"
            "  font-size: 12px;"
            "}"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.finished.emit()
                event.accept()
                return
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                return
            self.finished.emit()
            self.navigate.emit("down")
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Tab:
            self.finished.emit()
            direction = "back" if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else "forward"
            self.navigate.emit(direction)
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        QTimer.singleShot(120, self._deferred_finish)

    def _deferred_finish(self) -> None:
        if self._cell is None or not self._cell.is_editing():
            return
        fw = QApplication.focusWidget()
        if fw is not None:
            widget = fw
            while widget is not None:
                if widget is self._cell:
                    return
                widget = widget.parentWidget()
        self.finished.emit()


class PresetPickerPopup(QFrame):
    """Panou flotant — listă clickabilă."""

    def __init__(self, parte: str, camp: str, on_select, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("presetPickerPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._parte = parte
        self._camp = camp
        self._on_select = on_select
        self._all_values: list[str] = []
        self._picked = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        hint = QLabel("Click pe o valoare din listă")
        hint.setObjectName("presetPickerHint")
        root.addWidget(hint)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Caută…")
        self._search.textChanged.connect(self._rebuild_list)
        self._search.returnPressed.connect(self._pick_first_visible)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.setObjectName("presetPickerList")
        self._list.setMinimumWidth(360)
        self._list.setMaximumHeight(300)
        self._list.itemClicked.connect(self._pick_item)
        root.addWidget(self._list)

        self._rebuild_list()

    def dismiss(self) -> None:
        self._picked = True
        self.hide()
        self.deleteLater()

    def show_near(self, anchor: QWidget) -> None:
        self.adjustSize()
        pt = anchor.mapToGlobal(QPoint(0, anchor.height()))
        screen = anchor.screen().availableGeometry()
        if pt.x() + self.width() > screen.right():
            pt.setX(max(screen.left(), screen.right() - self.width()))
        if pt.y() + self.height() > screen.bottom():
            pt.setY(anchor.mapToGlobal(QPoint(0, 0)).y() - self.height())
        self.move(pt)
        self.show()
        self.raise_()
        self.activateWindow()
        self._search.setFocus()

    def _rebuild_list(self, filter_text: str = "") -> None:
        if not self._all_values:
            self._all_values = get_text_presets(self._parte, self._camp)
        filt = (filter_text if isinstance(filter_text, str) else self._search.text()).strip().casefold()
        self._list.clear()
        shown = [v for v in self._all_values if not filt or filt in v.casefold()]
        if not shown:
            item = QListWidgetItem("— Lista goală. Click dreapta în celulă pentru scriere directă. —")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return
        for val in shown:
            self._list.addItem(val)

    def _pick_first_visible(self) -> None:
        if self._list.count() > 0:
            item = self._list.item(0)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self._pick_item(item)

    def _pick_item(self, item: QListWidgetItem) -> None:
        if self._picked or item is None:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return
        text = item.text().strip()
        if not text:
            return

        self._picked = True
        self._list.blockSignals(True)
        self._search.blockSignals(True)
        callback = self._on_select
        self.hide()

        def _deliver() -> None:
            try:
                callback(text)
            finally:
                if _widget_alive(self):
                    self.deleteLater()

        QTimer.singleShot(0, _deliver)

    def refresh(self) -> None:
        self._all_values = get_text_presets(self._parte, self._camp)
        self._rebuild_list()


class PresetTextCell(QWidget):
    """picker_on_click=True: stânga=listă, dreapta=scrie  |  False: stânga=scrie direct."""

    value_changed = pyqtSignal()

    def __init__(
        self, parte: str, camp: str, parent=None, picker_on_click: bool = True
    ) -> None:
        super().__init__(parent)
        self._parte = parte
        self._camp = camp
        self._picker_on_click = picker_on_click
        self._value = ""
        self._popup: PresetPickerPopup | None = None
        self._suppress_open = False
        self._editing = False
        self._edit_snapshot = ""
        self._field_label = get_all_etichete(parte).get(camp, camp)

        self.setObjectName("presetTextCell")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._update_tooltips()

        self._label = QLabel()
        self._label.setObjectName("presetTextLabel")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._editor = InlineTextEdit(cell=self)
        self._editor.setMinimumHeight(36)
        self._editor.finished.connect(self._finish_inline_edit)
        self._editor.cancelled.connect(self._cancel_inline_edit)
        self._editor.navigate.connect(self._on_editor_navigate)

        self._stack = QStackedWidget()
        self._stack.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._stack.addWidget(self._label)
        self._stack.addWidget(self._editor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._stack)

        self.set_value("")

    def _update_tooltips(self) -> None:
        if self._picker_on_click:
            self.setToolTip(
                f"{self._field_label}\n"
                "• Click stânga = listă  ·  Click dreapta = scrie în celulă\n"
                "• Tab / Enter = următoarea celulă"
            )
        else:
            self.setToolTip(
                f"{self._field_label}\n"
                "• Click = scrie direct în celulă\n"
                "• Tab / Enter = următoarea celulă  ·  Shift+Enter = linie nouă"
            )

    def is_editing(self) -> bool:
        return self._editing

    def value(self) -> str:
        if self._editing:
            return self._editor.toPlainText().strip()
        return self._value.strip()

    def set_value(self, text: str) -> None:
        self._value = text or ""
        if self._value:
            self._label.setText(self._value)
            self._label.setStyleSheet("color: #1e293b;")
        else:
            if self._picker_on_click:
                self._label.setText("▾  Stânga: listă  ·  Dreapta: scrie aici")
            else:
                self._label.setText("✎  Click pentru a scrie")
            self._label.setStyleSheet("color: #64748b; font-style: italic;")
        if not self._editing:
            self._stack.setCurrentWidget(self._label)

    def refresh(self) -> None:
        if self._popup_visible():
            self._popup.refresh()

    def commit_new_value(self) -> None:
        pass

    def close_picker(self) -> None:
        popup = self._popup
        self._popup = None
        if popup is not None and _widget_alive(popup):
            popup.dismiss()

    def open_picker(self) -> None:
        if not self._picker_on_click or self._suppress_open or self._editing:
            return

        table = self.parent()
        while table is not None and not hasattr(table, "close_all_preset_pickers"):
            table = table.parent()
        if table is not None:
            table.close_all_preset_pickers(except_cell=self)

        if self._popup_visible():
            self._popup.raise_()
            self._popup.activateWindow()
            self._popup._search.setFocus()
            return

        self.close_picker()
        popup = PresetPickerPopup(self._parte, self._camp, self._on_picked, parent=None)
        self._popup = popup
        popup.show_near(self)

    def start_inline_edit(self) -> None:
        if self._editing:
            self._editor.setFocus()
            return
        self.close_picker()
        self._suppress_open = True
        self._editing = True
        self._edit_snapshot = self._value
        self._editor.setPlainText(self._value)
        self._stack.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._stack.setCurrentWidget(self._editor)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self._editor.setFocus()
        if self._value:
            cursor = self._editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
        else:
            self._editor.selectAll()

    def _on_editor_navigate(self, direction: str) -> None:
        table = self._find_table()
        if table is not None:
            QTimer.singleShot(0, lambda: table.navigate_from_widget(self, direction))

    def _finish_inline_edit(self) -> None:
        if not self._editing:
            return
        new_val = self._editor.toPlainText().strip()
        self._editing = False
        self._suppress_open = False
        self._stack.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.set_value(new_val)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if new_val != self._edit_snapshot:
            self._emit_value_changed()

    def _cancel_inline_edit(self) -> None:
        if not self._editing:
            return
        self._editing = False
        self._suppress_open = False
        self._stack.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.set_value(self._edit_snapshot)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def contextMenuEvent(self, event) -> None:
        self.start_inline_edit()
        event.accept()

    def _find_table(self):
        table = self.parent()
        while table is not None and not hasattr(table, "close_all_inline_edits"):
            table = table.parent()
        return table

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._handle_click(event)
        super().mouseReleaseEvent(event)

    def _handle_click(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._picker_on_click:
                if not self._editing and not self._suppress_open:
                    table = self._find_table()
                    if table is not None:
                        table.close_all_inline_edits()
                        table.close_all_preset_pickers(except_cell=self)
                    QTimer.singleShot(0, self.open_picker)
            else:
                table = self._find_table()
                if table is not None:
                    table.close_all_inline_edits(except_cell=self)
                if not self._editing:
                    QTimer.singleShot(0, self.start_inline_edit)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton and self._picker_on_click:
            self._suppress_open = True
            self.close_picker()
            QTimer.singleShot(0, self.start_inline_edit)
            QTimer.singleShot(300, lambda: setattr(self, "_suppress_open", False))
            event.accept()

    def _on_picked(self, value: str) -> None:
        self._clear_popup_ref()
        self.set_value(value)
        QTimer.singleShot(0, self._emit_value_changed)

    def _clear_popup_ref(self) -> None:
        self._popup = None

    def _popup_visible(self) -> bool:
        if not _widget_alive(self._popup):
            self._popup = None
            return False
        try:
            return self._popup.isVisible()
        except RuntimeError:
            self._popup = None
            return False

    def _emit_value_changed(self) -> None:
        if not _widget_alive(self):
            return
        self.value_changed.emit()

    def open_cell_editor(self) -> None:
        """Compatibilitate — editare direct în celulă."""
        self.start_inline_edit()

    def open_custom_editor(self) -> None:
        self.start_inline_edit()
