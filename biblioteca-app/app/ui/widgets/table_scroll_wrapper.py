"""Înveliș pentru tabele late: bară orizontală sus + jos, butoane stânga/dreapta."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)


class TableScrollWrapper(QWidget):
    """Derulare orizontală ușoară — bară dublă (sus+jos) și butoane de navigare."""

    STEP = 220

    def __init__(self, table, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self._btn_left = QPushButton("◀  Stânga")
        self._btn_right = QPushButton("Dreapta  ▶")
        self._btn_left.setObjectName("btnGhost")
        self._btn_right.setObjectName("btnGhost")
        self._btn_left.setToolTip("Derulează tabelul spre stânga")
        self._btn_right.setToolTip("Derulează tabelul spre dreapta")
        hint = QLabel("Tabel lat — folosiți butoanele sau barele de derulare")
        hint.setObjectName("scrollHint")
        nav.addWidget(self._btn_left)
        nav.addWidget(self._btn_right)
        nav.addWidget(hint, stretch=1)
        layout.addLayout(nav)

        self._top_bar = QScrollBar(Qt.Orientation.Horizontal)
        self._top_bar.setObjectName("tableHScrollTop")
        layout.addWidget(self._top_bar)

        self._area = QScrollArea()
        self._area.setObjectName("tableScrollArea")
        self._area.setWidgetResizable(True)
        self._area.setWidget(table)
        self._area.setFrameShape(QFrame.Shape.NoFrame)
        self._area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._area, stretch=1)

        hbar = self._area.horizontalScrollBar()
        self._top_bar.valueChanged.connect(hbar.setValue)
        hbar.valueChanged.connect(self._top_bar.setValue)
        hbar.rangeChanged.connect(self._sync_top_bar)

        self._btn_left.clicked.connect(lambda: hbar.setValue(max(hbar.minimum(), hbar.value() - self.STEP)))
        self._btn_right.clicked.connect(lambda: hbar.setValue(min(hbar.maximum(), hbar.value() + self.STEP)))

    def _sync_top_bar(self, minimum: int, maximum: int) -> None:
        hbar = self._area.horizontalScrollBar()
        self._top_bar.setRange(minimum, maximum)
        self._top_bar.setPageStep(hbar.pageStep())
        self._top_bar.setSingleStep(hbar.singleStep())
