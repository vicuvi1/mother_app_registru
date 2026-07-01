"""Delegate dropdown responsabil / formator."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStyledItemDelegate

from ui.widgets.responsabil_dropdown import ResponsabilDropdown


class ResponsabilDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = ResponsabilDropdown(parent)
        editor.set_value(str(index.data(Qt.ItemDataRole.DisplayRole) or ""))
        return editor

    def setEditorData(self, editor, index) -> None:
        editor.set_value(str(index.data(Qt.ItemDataRole.DisplayRole) or ""))

    def setModelData(self, editor, model, index) -> None:
        editor.commit_new_name()
        model.setData(index, editor.value(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)
