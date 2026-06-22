"""Dropdown reutilizabil pentru Responsabil / Formator / Coordonator."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QComboBox

from core.constants_manager import ensure_personal_in_list, get_personal_names


class ResponsabilDropdown(QComboBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.refresh()

    def refresh(self) -> None:
        current = self.currentText()
        self.blockSignals(True)
        self.clear()
        for name in get_personal_names():
            self.addItem(name)
        if current:
            idx = self.findText(current)
            if idx >= 0:
                self.setCurrentIndex(idx)
            else:
                self.setEditText(current)
        self.blockSignals(False)

    def value(self) -> str:
        return self.currentText().strip()

    def set_value(self, text: str) -> None:
        text = text or ""
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setEditText(text)

    def commit_new_name(self) -> None:
        ensure_personal_in_list(self.value())

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(0, self.showPopup)

    def showPopup(self) -> None:
        self.refresh()
        super().showPopup()
