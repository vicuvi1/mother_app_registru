"""Editor pentru pagina de titlu (coperta registrului)."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.constants_manager import get_cover_page, set_cover_page


class CoverPageDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pagina de titlu (coperta registrului)")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Aceste rânduri apar pe prima pagină a registrului complet la export.\n"
            "Toate sunt editabile."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        data = get_cover_page()
        self._fields: dict[str, QLineEdit] = {}
        labels = {
            "institutie_1": "Instituție (rândul 1)",
            "institutie_2": "Instituție (rândul 2)",
            "titlu": "Titlu registru",
            "biblioteca": "Denumire bibliotecă",
            "localitate": "Localitate",
            "an": "Anul",
        }
        for key, label in labels.items():
            edit = QLineEdit(data.get(key, ""))
            self._fields[key] = edit
            form.addRow(label + ":", edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Salvează")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        set_cover_page({key: edit.text() for key, edit in self._fields.items()})
        self.accept()
