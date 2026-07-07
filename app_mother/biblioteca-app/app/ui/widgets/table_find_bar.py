"""Bară căutare în tabel (Ctrl+F)."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QShortcut,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)


class TableFindBar(QFrame):
    """Widget compact pentru găsire text în tabel."""

    search_changed = pyqtSignal(str, bool)
    find_next = pyqtSignal()
    find_previous = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tableFindBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Găsește:"))
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Text în celule…")
        self._edit.setClearButtonEnabled(True)
        self._edit.returnPressed.connect(self.find_next.emit)
        layout.addWidget(self._edit, stretch=1)

        self._case = QCheckBox("Aa")
        self._case.setToolTip("Potrivire exactă (majuscule/minuscule)")
        layout.addWidget(self._case)

        btn_prev = QPushButton("◀")
        btn_prev.setToolTip("Anterior (Shift+Enter)")
        btn_prev.clicked.connect(self.find_previous.emit)
        layout.addWidget(btn_prev)

        btn_next = QPushButton("▶")
        btn_next.setToolTip("Următorul (Enter)")
        btn_next.clicked.connect(self.find_next.emit)
        layout.addWidget(btn_next)

        btn_close = QPushButton("✕")
        btn_close.setToolTip("Închide (Esc)")
        btn_close.clicked.connect(self.close_bar)
        layout.addWidget(btn_close)

        self._edit.textChanged.connect(self._emit_search)
        self._case.toggled.connect(self._emit_search)

        QShortcut(QKeySequence("Escape"), self, self.close_bar)

    def focus_search(self) -> None:
        self._edit.setFocus()
        self._edit.selectAll()

    def needle(self) -> str:
        return self._edit.text().strip()

    def case_sensitive(self) -> bool:
        return self._case.isChecked()

    def close_bar(self) -> None:
        self.hide()
        self.closed.emit()

    def _emit_search(self) -> None:
        self.search_changed.emit(self.needle(), self.case_sensitive())
