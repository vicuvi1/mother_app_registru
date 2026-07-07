"""Dialog configurare liste text rapide (o dată, apoi select din celulă)."""

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from core.constants_manager import get_all_etichete, get_text_presets, set_text_presets
from ui.widgets.editable_table import ColumnDef


class TextPresetsDialog(QDialog):
    def __init__(
        self,
        part_id: str,
        columns: list[ColumnDef],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._part_id = part_id
        self._columns = [c for c in columns if c.col_type == "preset_text"]
        self.setWindowTitle("Liste text rapide")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Introduceți valorile câte una pe rând (nume, teme, statuturi etc.).\n"
            "În tabel: click stânga → listă  •  click dreapta → scrie direct în celulă."
        ))

        tabs = QTabWidget()
        self._edits: dict[str, QTextEdit] = {}
        labels = get_all_etichete(part_id)
        for col in self._columns:
            edit = QTextEdit()
            edit.setPlaceholderText("Exemplu:\nStudent\nProfesor\nCercetător")
            existing = get_text_presets(part_id, col.key)
            if existing:
                edit.setPlainText("\n".join(existing))
            self._edits[col.key] = edit
            tabs.addTab(edit, labels.get(col.key, col.key))
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn:
            save_btn.setText("Salvează listele")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        for col in self._columns:
            text = self._edits[col.key].toPlainText()
            values = [ln.strip() for ln in text.splitlines() if ln.strip()]
            set_text_presets(self._part_id, col.key, values)
        self.accept()
