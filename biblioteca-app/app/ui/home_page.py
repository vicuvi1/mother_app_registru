"""Panou Acasă — vedere de ansamblu la pornire."""

from __future__ import annotations

from datetime import date, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import LUNI_RO, get_biblioteca_info
from core.part_progress import compute_part_progress, count_summary
from core.register_audit import IncompleteSlot, find_incomplete_months
from core.session_state import load_session
from database.backup import list_backups

ROLE_SLOT = Qt.ItemDataRole.UserRole


class HomePage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.main_window = main_window
        self.setObjectName("homePage")
        self._build_ui()

    def year(self) -> int:
        return self._year.value()

    def refresh(self) -> None:
        year = self._year.value()
        progress = compute_part_progress(year)
        complete, attention, empty = count_summary(progress)
        total = complete + attention + empty
        pct = int(100 * complete / total) if total else 0

        self._progress.setValue(pct)
        self._progress_label.setText(
            f"{complete} părți complete · {attention} cu atenție · {empty} neîncepute"
        )

        incomplete = find_incomplete_months(year)
        if incomplete:
            self._incomplete_summary.setText(
                f"{len(incomplete)} perioade fără date complete în {year}."
            )
        else:
            self._incomplete_summary.setText(
                f"Anul {year} arată complet pe toate părțile cu calendar."
            )

        self._issues.clear()
        for slot in incomplete[:8]:
            item = QListWidgetItem(slot.label)
            item.setData(ROLE_SLOT, slot)
            self._issues.addItem(item)
        if len(incomplete) > 8:
            self._issues.addItem(
                QListWidgetItem(f"… și încă {len(incomplete) - 8} perioade")
            )

        backups = list_backups()
        if backups:
            latest = backups[0]
            when = datetime.fromtimestamp(latest.stat().st_mtime)
            self._backup_label.setText(
                f"Ultima copie: {latest.name}\n({when.strftime('%d.%m.%Y %H:%M')})"
            )
        else:
            self._backup_label.setText("Nu există încă copii de rezervă.")

        session = load_session()
        part_id = session.get("part_id", "")
        month = session.get("month")
        year_s = session.get("year")
        hint = "Partea I"
        if part_id:
            from core.parts_registry import PARTS

            for roman, pid, title, _short in PARTS:
                if pid == part_id:
                    hint = f"Partea {roman}"
                    if isinstance(month, int) and 1 <= month <= 12:
                        hint += f", {LUNI_RO[month - 1]}"
                    if isinstance(year_s, int):
                        hint += f" {year_s}"
                    break
        self._session_hint.setText(f"Ultima sesiune: {hint}")

        if hasattr(self.main_window, "_part_list"):
            self.main_window.refresh_sidebar_badges(year)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QFrame()
        header.setObjectName("homeHeaderCard")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 18, 20, 18)
        nume, loc = get_biblioteca_info()
        title = QLabel("Bun venit")
        title.setObjectName("homeTitle")
        hl.addWidget(title)
        lib = QLabel(nume or "Biblioteca dvs.")
        lib.setObjectName("homeLibrary")
        hl.addWidget(lib)
        if loc:
            sub = QLabel(loc)
            sub.setObjectName("homeSubtitle")
            hl.addWidget(sub)
        outer.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(16)

        left = QFrame()
        left.setObjectName("homeCard")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(18, 16, 18, 16)
        ll.setSpacing(10)

        year_row = QHBoxLayout()
        year_row.addWidget(QLabel("An registru:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(date.today().year)
        self._year.valueChanged.connect(self.refresh)
        year_row.addWidget(self._year)
        year_row.addStretch()
        ll.addLayout(year_row)

        self._progress_label = QLabel()
        self._progress_label.setObjectName("homeStat")
        ll.addWidget(self._progress_label)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p% părți complete")
        ll.addWidget(self._progress)

        self._session_hint = QLabel()
        self._session_hint.setObjectName("homeSubtitle")
        ll.addWidget(self._session_hint)

        btn_continue = QPushButton("Continuă unde am rămas")
        btn_continue.setObjectName("btnPrimary")
        btn_continue.clicked.connect(self.main_window.continue_last_session)
        ll.addWidget(btn_continue)

        btn_year = QPushButton("Asistent închidere an…")
        btn_year.setObjectName("btnGhost")
        btn_year.clicked.connect(self.main_window._open_year_end_wizard)
        ll.addWidget(btn_year)

        row.addWidget(left, stretch=1)

        right = QFrame()
        right.setObjectName("homeCard")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 16, 18, 16)
        rl.setSpacing(8)
        rl.addWidget(QLabel("Backup"))
        self._backup_label = QLabel()
        self._backup_label.setObjectName("homeSubtitle")
        self._backup_label.setWordWrap(True)
        rl.addWidget(self._backup_label)
        btn_backup = QPushButton("Salvează copie acum")
        btn_backup.clicked.connect(self.main_window._backup_database)
        rl.addWidget(btn_backup)
        btn_folder = QPushButton("Deschide folder backup")
        btn_folder.setObjectName("btnGhost")
        btn_folder.clicked.connect(self.main_window._open_backups_folder)
        rl.addWidget(btn_folder)
        rl.addStretch()
        row.addWidget(right, stretch=1)
        outer.addLayout(row)

        issues_card = QFrame()
        issues_card.setObjectName("homeCard")
        il = QVBoxLayout(issues_card)
        il.setContentsMargins(18, 16, 18, 16)
        il.addWidget(QLabel("De completat (prioritar)"))
        self._incomplete_summary = QLabel()
        self._incomplete_summary.setObjectName("homeSubtitle")
        self._incomplete_summary.setWordWrap(True)
        il.addWidget(self._incomplete_summary)
        self._issues = QListWidget()
        self._issues.setObjectName("homeIssuesList")
        self._issues.itemDoubleClicked.connect(self._open_slot)
        il.addWidget(self._issues, stretch=1)
        btn_all = QPushButton("Raport complet luni fără date…")
        btn_all.setObjectName("btnGhost")
        btn_all.clicked.connect(self.main_window._open_incomplete_months)
        il.addWidget(btn_all)
        outer.addWidget(issues_card, stretch=1)

        legend = QLabel("Sidebar: ✓ complet  ·  ⚠ parțial  ·  · neînceput")
        legend.setObjectName("homeLegend")
        outer.addWidget(legend)

    def _open_slot(self, item: QListWidgetItem) -> None:
        slot: IncompleteSlot | None = item.data(ROLE_SLOT)
        if slot is None:
            return
        self.main_window.navigate_to_part(slot.part_id, month=slot.month, category=slot.category)
