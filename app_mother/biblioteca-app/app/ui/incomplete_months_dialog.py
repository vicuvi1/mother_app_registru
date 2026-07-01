"""Raport luni fără date înregistrate în baza de date."""

from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.register_audit import IncompleteSlot, find_incomplete_months

ROLE_SLOT = Qt.ItemDataRole.UserRole


class IncompleteMonthsDialog(QDialog):
    def __init__(self, main_window, default_year: int | None = None) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Luni fără date")
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Lista de mai jos arată lunile (și categoriile) fără date reale: "
                "fie lipsesc rândurile, fie toate valorile numerice sunt 0 și câmpurile text sunt goale.\n"
                "Dublu-click pe un element pentru a deschide partea respectivă."
            )
        )

        top = QHBoxLayout()
        top.addWidget(QLabel("Anul:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(default_year or date.today().year)
        self._year.valueChanged.connect(self._refresh)
        top.addWidget(self._year)
        top.addStretch()
        btn_refresh = QPushButton("Reîmprospătează")
        btn_refresh.clicked.connect(self._refresh)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._open_slot)
        layout.addWidget(self._list, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Închide")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

        self._refresh()

    def _refresh(self) -> None:
        year = self._year.value()
        slots = find_incomplete_months(year)
        self._list.clear()
        for slot in slots:
            item = QListWidgetItem(slot.label)
            item.setData(ROLE_SLOT, slot)
            self._list.addItem(item)

        if slots:
            self._summary.setText(
                f"Anul {year}: {len(slots)} perioadă/perioade fără date salvate."
            )
        else:
            self._summary.setText(
                f"Anul {year}: toate lunile au cel puțin un rând salvat în registru."
            )

    def _open_slot(self, item: QListWidgetItem) -> None:
        slot: IncompleteSlot | None = item.data(ROLE_SLOT)
        if slot is None:
            return
        self.main_window.navigate_to_part(slot.part_id, month=slot.month, category=slot.category)
        self.accept()
