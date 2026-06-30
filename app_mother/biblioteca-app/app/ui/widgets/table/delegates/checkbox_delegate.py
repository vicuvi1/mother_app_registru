"""Delegate checkbox pentru coloane bool și scope_*."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionButton


class CheckBoxDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        if not index.isValid():
            return
        model = index.model()
        if hasattr(model, "store") and model.store.is_total_row(index.row()):
            super().paint(painter, option, index)
            return

        checked = bool(index.data(Qt.ItemDataRole.EditRole))
        checkbox = QStyleOptionButton()
        checkbox.state = QStyle.StateFlag.State_Enabled
        if option.state & QStyle.StateFlag.State_MouseOver:
            checkbox.state |= QStyle.StateFlag.State_MouseOver
        checkbox.state |= (
            QStyle.StateFlag.State_On if checked else QStyle.StateFlag.State_Off
        )
        checkbox.rect = self._checkbox_rect(option)

        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_CheckBox, checkbox, painter)

    def editorEvent(self, event, model, option, index) -> bool:
        if not index.isValid():
            return False
        if hasattr(model, "store") and model.store.is_total_row(index.row()):
            return False
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        if not self._checkbox_rect(option).contains(event.position().toPoint()):
            return False

        current = bool(model.data(index, Qt.ItemDataRole.EditRole))
        model.setData(index, not current, Qt.ItemDataRole.EditRole)
        return True

    def _checkbox_rect(self, option) -> QRect:
        style = option.widget.style() if option.widget else QApplication.style()
        indicator = style.subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            QStyleOptionButton(),
            option.widget,
        )
        x = option.rect.x() + (option.rect.width() - indicator.width()) // 2
        y = option.rect.y() + (option.rect.height() - indicator.height()) // 2
        return QRect(x, y, indicator.width(), indicator.height())
