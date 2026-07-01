"""Notificări toast discrete — fără dialog blocant."""

from __future__ import annotations

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class ToastHost(QWidget):
    """Overlay în colțul dreapta-jos al panoului principal."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toastHost")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel()
        self._label.setObjectName("toastLabel")
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(420)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(
        self,
        message: str,
        *,
        duration_ms: int = 3200,
        kind: str = "success",
    ) -> None:
        self._label.setProperty("toastKind", kind)
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)
        self._label.setText(message)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._timer.start(max(1200, duration_ms))

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 20
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.isVisible():
            self._reposition()
