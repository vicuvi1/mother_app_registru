"""Selector An + Lună pentru paginile de Parte."""

from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QWidget

from core.constants_manager import LUNI_RO


class DatePickerZileLucratoare(QFrame):
    def __init__(
        self,
        show_month: bool = True,
        year_start: int = 2024,
        year_end: int = 2030,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("datePickerFrame")
        self._show_month = show_month

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        layout.addWidget(QLabel("An"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(90)
        for y in range(year_start, year_end + 1):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentText(str(2025))
        layout.addWidget(self.year_combo)

        self.month_label = QLabel("Lună")
        layout.addWidget(self.month_label)
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(130)
        for i, name in enumerate(LUNI_RO, start=1):
            self.month_combo.addItem(name, i)
        self.month_combo.setCurrentIndex(2)
        layout.addWidget(self.month_combo)

        if not show_month:
            self.month_label.hide()
            self.month_combo.hide()

    @property
    def year(self) -> int:
        return int(self.year_combo.currentData())

    @property
    def month(self) -> int:
        if not self._show_month:
            return 1
        return int(self.month_combo.currentData())

    def set_year(self, year: int) -> None:
        idx = self.year_combo.findData(year)
        if idx >= 0:
            self.year_combo.setCurrentIndex(idx)

    def set_month(self, month: int) -> None:
        idx = self.month_combo.findData(month)
        if idx >= 0:
            self.month_combo.setCurrentIndex(idx)
