"""Zile nelucrătoare — selectare din calendar; zilele marcate nu intră în tabele / generare."""

from __future__ import annotations

import calendar
from datetime import date

from PyQt5.QtCore import QDate, QLocale, Qt
from PyQt5.QtGui import QColor, QFont, QTextCharFormat
from PyQt5.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.constants_manager import get_excluded_days_for_year, set_excluded_days_for_year


class ExcludedDaysDialog(QDialog):
    def __init__(
        self,
        parent=None,
        default_year: int | None = None,
        default_month: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Zile nelucrătoare (concediu)")
        self.setMinimumSize(520, 480)

        self._initial_month = default_month
        self._saved_year: int | None = None
        self._excluded: set[str] = set()
        self._fmt_excluded = self._make_excluded_format()
        self._fmt_weekend = self._make_weekend_format()

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Sâmbăta și duminica sunt <b>automat excluse</b> din registru (nu trebuie marcate).\n"
                "Click pe zilele <b>luni–vineri</b> pentru concediu/sărbători — marcate cu roșu.\n"
                "Zilele marcate nu apar în tabele și nu sunt incluse la „Generează automat”."
            )
        )
        self._context_label = QLabel()
        self._context_label.setStyleSheet("color: #0f766e; font-weight: 600;")
        if default_month and 1 <= default_month <= 12:
            from core.constants_manager import LUNI_RO

            layout.addWidget(
                self._context_label,
            )
            self._context_label.setText(
                f"Registrul afișează: {LUNI_RO[default_month - 1]} {default_year or date.today().year} "
                f"— marcați zilele nelucrătoare pentru această lună."
            )
        else:
            self._context_label.hide()
            layout.addWidget(self._context_label)

        top = QHBoxLayout()
        top.addWidget(QLabel("Anul:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(default_year or date.today().year)
        self._year.valueChanged.connect(self._load_year)
        top.addWidget(self._year)
        top.addStretch()
        self._summary = QLabel()
        self._summary.setStyleSheet("color: #64748b;")
        top.addWidget(self._summary)
        layout.addLayout(top)

        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.ISOWeekNumbers)
        self._calendar.setHorizontalHeaderFormat(
            QCalendarWidget.ShortDayNames
        )
        self._calendar.setFirstDayOfWeek(Qt.Monday)
        self._calendar.setLocale(QLocale(QLocale.Romanian, QLocale.Romania))
        self._calendar.clicked.connect(self._toggle_day)
        self._calendar.currentPageChanged.connect(self._on_month_changed)
        layout.addWidget(self._calendar)

        self._month_list = QLabel()
        self._month_list.setWordWrap(True)
        self._month_list.setStyleSheet(
            "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(self._month_list)

        actions = QHBoxLayout()
        btn_clear_month = QPushButton("Golește luna afișată")
        btn_clear_month.clicked.connect(self._clear_shown_month)
        btn_clear_year = QPushButton("Golește tot anul")
        btn_clear_year.clicked.connect(self._clear_year)
        actions.addWidget(btn_clear_month)
        actions.addWidget(btn_clear_year)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn:
            save_btn.setText("Salvează")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_year()

    @staticmethod
    def _make_excluded_format() -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#fecaca"))
        fmt.setForeground(QColor("#991b1b"))
        fmt.setFontWeight(QFont.Bold)
        return fmt

    @staticmethod
    def _make_weekend_format() -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#94a3b8"))
        return fmt

    def _load_year(self) -> None:
        year = self._year.value()
        by_month = get_excluded_days_for_year(year)
        self._excluded = set()
        for dates in by_month.values():
            self._excluded.update(dates)

        self._calendar.setDateRange(QDate(year, 1, 1), QDate(year, 12, 31))
        today = date.today()
        if self._initial_month and 1 <= self._initial_month <= 12:
            month = self._initial_month
            self._initial_month = None
        elif today.year == year:
            month = today.month
        else:
            month = 1
        day = today.day if today.year == year and month == today.month else 1
        self._calendar.setSelectedDate(QDate(year, month, day))

        self._paint_calendar()
        self._update_labels()

    def _clear_all_formats(self) -> None:
        year = self._year.value()
        empty = QTextCharFormat()
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                self._calendar.setDateTextFormat(QDate(year, month, day), empty)

    def _paint_calendar(self) -> None:
        year = self._year.value()
        self._clear_all_formats()
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                qd = QDate(year, month, day)
                dow = qd.dayOfWeek()
                if dow in (Qt.Saturday, Qt.Sunday):
                    self._calendar.setDateTextFormat(qd, self._fmt_weekend)
        for dd_mm in self._excluded:
            day_s, month_s = dd_mm.split(".")
            qd = QDate(year, int(month_s), int(day_s))
            if qd.isValid():
                self._calendar.setDateTextFormat(qd, self._fmt_excluded)
        self._calendar.updateCells()

    def _toggle_day(self, qdate: QDate) -> None:
        if qdate.year() != self._year.value():
            return
        if qdate.dayOfWeek() in (Qt.Saturday, Qt.Sunday):
            return
        dd_mm = f"{qdate.day():02d}.{qdate.month():02d}"
        if dd_mm in self._excluded:
            self._excluded.remove(dd_mm)
            dow = qdate.dayOfWeek()
            if dow in (Qt.Saturday, Qt.Sunday):
                self._calendar.setDateTextFormat(qdate, self._fmt_weekend)
            else:
                self._calendar.setDateTextFormat(qdate, QTextCharFormat())
        else:
            self._excluded.add(dd_mm)
            self._calendar.setDateTextFormat(qdate, self._fmt_excluded)
        self._calendar.updateCell(qdate)
        self._update_labels()

    def _on_month_changed(self, _year: int, _month: int) -> None:
        self._update_labels()

    def _update_labels(self) -> None:
        year = self._year.value()
        n = len(self._excluded)
        word = "zi" if n == 1 else "zile"
        self._summary.setText(f"{n} {word} nelucrătoare în {year}")

        month = self._calendar.monthShown()
        month_days = sorted(
            d for d in self._excluded if d.endswith(f".{month:02d}")
        )
        from core.constants_manager import LUNI_RO

        month_name = LUNI_RO[month - 1]
        if month_days:
            self._month_list.setText(
                f"<b>{month_name} {year}:</b> " + ", ".join(month_days)
            )
        else:
            self._month_list.setText(
                f"<b>{month_name} {year}:</b> nicio zi marcată — click pe calendar pentru a selecta."
            )

    def _clear_shown_month(self) -> None:
        month = self._calendar.monthShown()
        suffix = f".{month:02d}"
        to_remove = {d for d in self._excluded if d.endswith(suffix)}
        self._excluded -= to_remove
        self._paint_calendar()
        self._update_labels()

    def _clear_year(self) -> None:
        self._excluded.clear()
        self._paint_calendar()
        self._update_labels()

    def saved_year(self) -> int | None:
        """Anul pentru care s-au salvat zilele (după accept)."""
        return self._saved_year

    def _save(self) -> None:
        year = self._year.value()
        by_month: dict[int, list[str]] = {m: [] for m in range(1, 13)}
        for dd_mm in self._excluded:
            _day, mon = dd_mm.split(".")
            by_month[int(mon)].append(dd_mm)
        set_excluded_days_for_year(year, by_month)
        self._saved_year = year
        self.accept()
