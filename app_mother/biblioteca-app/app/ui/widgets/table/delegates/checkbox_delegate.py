"""Delegate checkbox pentru coloane bool și scope_*."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QRect, Qt
from PyQt5.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionButton


class CheckBoxDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        if not index.isValid():
            return
        model = index.model()
        if hasattr(model, "store") and model.store.is_total_row(index.row()):
            super().paint(painter, option, index)
            return

        checked = bool(index.data(Qt.EditRole))
        checkbox = QStyleOptionButton()
        checkbox.state = QStyle.State_Enabled
        if option.state & QStyle.State_MouseOver:
            checkbox.state |= QStyle.State_MouseOver
        checkbox.state |= (
            QStyle.State_On if checked else QStyle.State_Off
        )
        checkbox.rect = self._checkbox_rect(option)

        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_CheckBox, checkbox, painter)

    def editorEvent(self, event, model, option, index) -> bool:
        if not index.isValid():
            return False
        if hasattr(model, "store") and model.store.is_total_row(index.row()):
            return False
        if event.type() != QEvent.MouseButtonRelease:
            return False
        if event.button() != Qt.LeftButton:
            return False
        if not self._checkbox_rect(option).contains(event.pos()):
            return False

        current = bool(model.data(index, Qt.EditRole))
        model.setData(index, not current, Qt.EditRole)
        return True

    def _checkbox_rect(self, option) -> QRect:
        style = option.widget.style() if option.widget else QApplication.style()
        indicator = style.subElementRect(
            QStyle.SE_CheckBoxIndicator,
            QStyleOptionButton(),
            option.widget,
        )
        x = option.rect.x() + (option.rect.width() - indicator.width()) // 2
        y = option.rect.y() + (option.rect.height() - indicator.height()) // 2
        return QRect(x, y, indicator.width(), indicator.height())
