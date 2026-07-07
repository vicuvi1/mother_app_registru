"""Asistent închidere an — verificări, backup, export."""

from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import get_cover_page
from core.register_audit import find_incomplete_months
from database.backup import create_backup


class YearEndWizard(QDialog):
    def __init__(self, main_window, default_year: int | None = None) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Asistent închidere an")
        self.resize(700, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Verificați registrul înainte de arhivare: luni incomplete, copertă, backup și export."
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

        self._checks: list[QCheckBox] = []
        for text in [
            "Am verificat lunile fără date / cu zerouri",
            "Pagina de titlu (copertă) este completă",
            "Am creat o copie de rezervă (backup)",
            "Am exportat registrul pentru arhivă",
        ]:
            cb = QCheckBox(text)
            self._checks.append(cb)
            layout.addWidget(cb)

        layout.addWidget(QLabel("Luni de completat (dublu-click pentru deschidere):"))
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._open_slot)
        layout.addWidget(self._list, stretch=1)

        actions = QHBoxLayout()
        btn_incomplete = QPushButton("Raport luni…")
        btn_incomplete.clicked.connect(self._open_incomplete_dialog)
        actions.addWidget(btn_incomplete)
        btn_cover = QPushButton("Copertă…")
        btn_cover.clicked.connect(self.main_window._open_cover)
        actions.addWidget(btn_cover)
        btn_backup = QPushButton("Backup acum")
        btn_backup.clicked.connect(self._do_backup)
        actions.addWidget(btn_backup)
        btn_export = QPushButton("Registru final…")
        btn_export.clicked.connect(self._open_register_final)
        actions.addWidget(btn_export)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn:
            close_btn.setText("Închide")
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        year = self._year.value()
        slots = find_incomplete_months(year)
        cover = get_cover_page()
        cover_ok = bool(
            (cover.get("biblioteca") or "").strip()
            and (cover.get("an") or str(year)).strip()
        )

        self._summary.setText(
            f"<b>Anul {year}</b> — {len(slots)} sloturi de verificat  ·  "
            f"Copertă: {'OK' if cover_ok else 'incompletă'}"
        )

        self._list.clear()
        if not slots:
            item = QListWidgetItem("✓ Toate lunile au date înregistrate.")
            item.setFlags(Qt.ItemIsEnabled)
            self._list.addItem(item)
        else:
            for slot in slots[:80]:
                item = QListWidgetItem(slot.label)
                item.setData(Qt.UserRole, slot)
                self._list.addItem(item)
            if len(slots) > 80:
                self._list.addItem(QListWidgetItem(f"… și încă {len(slots) - 80}"))

    def _open_slot(self, item: QListWidgetItem) -> None:
        slot = item.data(Qt.UserRole)
        if slot is None:
            return
        self.main_window.navigate_to_part(
            slot.part_id,
            month=slot.month,
            category=slot.category,
        )
        self.accept()

    def _open_incomplete_dialog(self) -> None:
        from ui.incomplete_months_dialog import IncompleteMonthsDialog

        IncompleteMonthsDialog(self.main_window, default_year=self._year.value()).exec()
        self._refresh()

    def _do_backup(self) -> None:
        try:
            path = create_backup("year_end")
            self._checks[2].setChecked(True)
            QMessageBox.information(
                self,
                "Backup reușit",
                f"Copia a fost salvată:\n{path}",
            )
        except OSError as exc:
            QMessageBox.warning(self, "Backup", f"Nu s-a putut crea copia:\n{exc}")

    def _open_register_final(self) -> None:
        self.main_window._show_register_final()
        self._checks[3].setChecked(True)
