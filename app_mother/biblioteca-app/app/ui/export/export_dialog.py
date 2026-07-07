"""Dialog alegere format + scope export."""

from datetime import date

from core.constants_manager import DEFAULT_EXPORT_FORMAT
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(self, parent=None, default_year: int | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportă")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        # --- format ---
        fmt_box = QGroupBox("Format")
        fmt_layout = QVBoxLayout(fmt_box)
        self._fmt_group = QButtonGroup(self)
        self._formats = [
            ("word", "Word (.docx) — recomandat pentru arhivare și printare"),
            ("pdf", "PDF (.pdf) — pentru prezentare"),
            ("excel", "Excel (.xlsx) — pentru editare în foi de calcul"),
        ]
        self._fmt_buttons = {}
        for key, label in self._formats:
            rb = QRadioButton(label)
            if key == DEFAULT_EXPORT_FORMAT:
                rb.setChecked(True)
            self._fmt_group.addButton(rb)
            self._fmt_buttons[key] = rb
            fmt_layout.addWidget(rb)
        layout.addWidget(fmt_box)

        # --- scope ---
        scope_box = QGroupBox("Ce exportăm")
        scope_layout = QVBoxLayout(scope_box)
        self._scope_group = QButtonGroup(self)
        self._scopes = [
            ("month", "Doar luna afișată (1 pagină)"),
            ("year", "Tot anul – partea curentă (12 luni × categorii)"),
            ("full", "Registru complet (toate părțile, toate lunile) — pagini numerotate"),
        ]
        self._scope_buttons = {}
        for i, (key, label) in enumerate(self._scopes):
            rb = QRadioButton(label)
            if i == 0:
                rb.setChecked(True)
            self._scope_group.addButton(rb)
            self._scope_buttons[key] = rb
            scope_layout.addWidget(rb)

        form = QFormLayout()
        self._year_spin = QSpinBox()
        self._year_spin.setRange(2000, 2100)
        self._year_spin.setValue(default_year or date.today().year)
        form.addRow("Anul (pentru an/registru complet):", self._year_spin)
        scope_layout.addLayout(form)
        layout.addWidget(scope_box)

        layout.addWidget(QLabel("Veți alege locația de salvare în pasul următor."))

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("Continuă")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_format(self) -> str:
        for key, rb in self._fmt_buttons.items():
            if rb.isChecked():
                return key
        return "word"

    def selected_scope(self) -> str:
        for key, rb in self._scope_buttons.items():
            if rb.isChecked():
                return key
        return "month"

    def selected_year(self) -> int:
        return self._year_spin.value()
