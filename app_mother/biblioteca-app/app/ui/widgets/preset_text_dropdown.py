"""Dropdown cu valori predefinite pentru câmpuri text — click și selectezi."""

from PyQt6.QtWidgets import QComboBox

from core.constants_manager import ensure_text_preset, get_text_presets


class PresetTextDropdown(QComboBox):
    def __init__(self, parte: str, camp: str, parent=None) -> None:
        super().__init__(parent)
        self._parte = parte
        self._camp = camp
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.refresh()

    def refresh(self) -> None:
        current = self.currentText()
        self.blockSignals(True)
        self.clear()
        for val in get_text_presets(self._parte, self._camp):
            self.addItem(val)
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

    def commit_new_value(self) -> None:
        ensure_text_preset(self._parte, self._camp, self.value())
