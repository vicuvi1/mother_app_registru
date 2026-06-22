"""Dialog import date din Excel."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.constants_manager import LUNI_RO
from core.part_import_meta import list_importable_parts
from ui.excel_import.import_excel import import_rows_to_database, parse_excel_rows


class ImportExcelDialog(QDialog):
    def __init__(self, parent=None, default_part_id: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Importă din Excel")
        self.setMinimumWidth(480)
        self._path = QLineEdit()
        self._path.setReadOnly(True)
        btn_browse = QPushButton("Alege fișier…")
        btn_browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self._path, stretch=1)
        path_row.addWidget(btn_browse)

        self._parts = list_importable_parts()
        self._part = QComboBox()
        for part_id, roman, title in self._parts:
            self._part.addItem(f"Partea {roman}. {title}", part_id)
        if default_part_id:
            idx = self._part.findData(default_part_id)
            if idx >= 0:
                self._part.setCurrentIndex(idx)

        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(date.today().year)

        self._month = QSpinBox()
        self._month.setRange(1, 12)
        self._month.setValue(date.today().month)

        self._category = QComboBox()
        self._category.addItem("—", None)
        self._category.addItem("Adulți", "adulti")
        self._category.addItem("Copii", "copii")

        self._replace = QCheckBox("Înlocuiește datele existente pentru perioada selectată")
        self._replace.setChecked(True)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Importă rânduri dintr-un fișier Excel exportat anterior din această aplicație "
                "(aceeași structură de coloane)."
            )
        )
        layout.addLayout(path_row)

        form = QFormLayout()
        form.addRow("Partea:", self._part)
        form.addRow("Anul:", self._year)
        form.addRow("Luna:", self._month)
        form.addRow("Categorie:", self._category)
        layout.addLayout(form)
        layout.addWidget(self._replace)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._run_import)
        buttons.rejected.connect(self.reject)
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.setText("Importă")
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selectați fișierul Excel",
            "",
            "Fișier Excel (*.xlsx)",
        )
        if path:
            self._path.setText(path)

    def _run_import(self) -> None:
        path = self._path.text().strip()
        if not path or not Path(path).is_file():
            QMessageBox.warning(self, "Import", "Selectați un fișier Excel valid.")
            return
        part_id = self._part.currentData()
        year = self._year.value()
        month = self._month.value()
        category = self._category.currentData()

        try:
            rows = parse_excel_rows(Path(path), part_id)
            if not rows:
                QMessageBox.information(self, "Import", "Nu s-au găsit rânduri de importat.")
                return
            count = import_rows_to_database(
                part_id,
                year,
                month,
                category,
                rows,
                replace=self._replace.isChecked(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Import eșuat", str(exc))
            return

        QMessageBox.information(
            self,
            "Import reușit",
            f"Au fost importate {count} rânduri pentru {LUNI_RO[month - 1]} {year}.",
        )
        self.accept()
