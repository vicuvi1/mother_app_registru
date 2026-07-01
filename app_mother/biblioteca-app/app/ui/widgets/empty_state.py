"""Panou prietenos când o lună / listă nu are date."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class TableEmptyState(QWidget):
    regenerate_clicked = pyqtSignal()
    copy_month_clicked = pyqtSignal()
    add_row_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tableEmptyState")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 48, 32, 48)

        self._icon = QLabel("📋")
        self._icon.setObjectName("emptyStateIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)

        self._title = QLabel()
        self._title.setObjectName("emptyStateTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("emptyStateSubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        layout.addWidget(self._subtitle)

        layout.addSpacing(8)

        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(8)

        self._btn_regenerate = QPushButton("📅 Regenerează zilele lunii")
        self._btn_regenerate.setObjectName("btnPrimary")
        self._btn_regenerate.clicked.connect(lambda: self.regenerate_clicked.emit())
        btn_layout.addWidget(self._btn_regenerate)

        self._btn_copy = QPushButton("⎘ Copiază din luna trecută")
        self._btn_copy.setObjectName("btnGhost")
        self._btn_copy.clicked.connect(lambda: self.copy_month_clicked.emit())
        btn_layout.addWidget(self._btn_copy)

        self._btn_add = QPushButton("+ Adaugă primul rând")
        self._btn_add.setObjectName("btnPrimary")
        self._btn_add.clicked.connect(lambda: self.add_row_clicked.emit())
        btn_layout.addWidget(self._btn_add)

        layout.addWidget(btn_row)

    def configure(
        self,
        *,
        title: str,
        subtitle: str,
        show_regenerate: bool = False,
        show_copy_month: bool = False,
        show_add_row: bool = False,
    ) -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._btn_regenerate.setVisible(show_regenerate)
        self._btn_copy.setVisible(show_copy_month)
        self._btn_add.setVisible(show_add_row)
