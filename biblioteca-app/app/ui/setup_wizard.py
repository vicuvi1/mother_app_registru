"""Ecran inițial: Personal, range-uri default, date bibliotecă."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import (
    add_personal,
    apply_global_ranges,
    delete_personal,
    get_biblioteca_info,
    get_personal_names,
    set_biblioteca_info,
    update_personal,
)
from core.export_presets import get_print_orientation, set_print_orientation
from core.ui_theme import get_ui_theme, set_ui_theme
from database.db_manager import mark_setup_completed
from core.autosave import get_autosave_interval, save_autosave_interval


class SetupWizard(QDialog):
    def __init__(self, first_run: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.first_run = first_run
        self.setObjectName("setupDialog")
        self.setWindowTitle("Configurare inițială")
        self.setMinimumSize(580, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        welcome = QLabel("Bine ați venit!")
        welcome.setObjectName("setupWelcome")
        layout.addWidget(welcome)

        hint = QLabel(
            "Completați datele de mai jos o singură dată. "
            "Le puteți modifica oricând din Setări → Setup."
        )
        hint.setObjectName("setupHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        tabs = QTabWidget()
        tabs.addTab(self._build_personal_tab(), "👤 Personal")
        tabs.addTab(self._build_ranges_tab(), "📊 Range-uri")
        tabs.addTab(self._build_biblioteca_tab(), "🏛 Bibliotecă")
        tabs.addTab(self._build_app_tab(), "⚙ Aplicație")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Salvează și continuă")
            save_btn.setObjectName("btnPrimary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_personal_table()

    def _build_personal_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(
            QLabel("Numele apar în dropdown-urile Responsabil / Formator din toate Părțile:")
        )

        self.personal_table = QTableWidget(0, 1)
        self.personal_table.setObjectName("dataTable")
        self.personal_table.setHorizontalHeaderLabels(["Nume, prenume"])
        self.personal_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.personal_table)

        btns = QHBoxLayout()
        for text, slot, name in [
            ("+ Adaugă", self._add_personal, "btnAddRow"),
            ("Editează", self._edit_personal, ""),
            ("Șterge", self._delete_personal, ""),
        ]:
            btn = QPushButton(text)
            if name:
                btn.setObjectName(name)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        btns.addStretch()
        layout.addLayout(btns)
        return w

    def _build_ranges_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.addRow(QLabel("Valori maxime pentru generarea automată:"))

        self.spin_persoane = QSpinBox()
        self.spin_persoane.setRange(1, 999)
        self.spin_persoane.setValue(30)
        form.addRow("Persoane / zi (max):", self.spin_persoane)

        self.spin_activitati = QSpinBox()
        self.spin_activitati.setRange(1, 999)
        self.spin_activitati.setValue(5)
        form.addRow("Activități / zi (max):", self.spin_activitati)

        form.addRow(
            QLabel(
                "Aceste valori se aplică tuturor Părților ca punct de plecare.\n"
                "Le puteți ajusta individual din fiecare Parte → Range-uri."
            )
        )
        return w

    def _build_biblioteca_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        self.edit_nume = QLineEdit()
        self.edit_nume.setPlaceholderText("ex. Biblioteca Publică...")
        self.edit_localitate = QLineEdit()
        self.edit_localitate.setPlaceholderText("ex. Chișinău")
        nume, loc = get_biblioteca_info()
        self.edit_nume.setText(nume)
        self.edit_localitate.setText(loc)
        form.addRow("Nume bibliotecă:", self.edit_nume)
        form.addRow("Localitate:", self.edit_localitate)
        form.addRow(
            QLabel("Apare opțional în antetul exporturilor PDF / Word / Excel.")
        )
        return w

    def _build_app_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.addRow(QLabel("Comportament aplicație:"))

        self.combo_autosave = QComboBox()
        self._autosave_options = [
            ("Dezactivat", 0),
            ("La 30 secunde", 30),
            ("La 1 minut (implicit)", 60),
            ("La 5 minute", 300),
        ]
        for label, _sec in self._autosave_options:
            self.combo_autosave.addItem(label)
        current = get_autosave_interval()
        for i, (_label, sec) in enumerate(self._autosave_options):
            if sec == current:
                self.combo_autosave.setCurrentIndex(i)
                break
        form.addRow("Autosalvare:", self.combo_autosave)
        form.addRow(
            QLabel(
                "Salvează automat pagina curentă la intervalul ales și la schimbarea părții."
            )
        )

        self.combo_theme = QComboBox()
        self._theme_options = [("Deschis (implicit)", "light"), ("Întunecat", "dark")]
        for label, _val in self._theme_options:
            self.combo_theme.addItem(label)
        current_theme = get_ui_theme()
        for i, (_label, val) in enumerate(self._theme_options):
            if val == current_theme:
                self.combo_theme.setCurrentIndex(i)
                break
        form.addRow("Temă interfață:", self.combo_theme)

        self.combo_print = QComboBox()
        self._print_options = [("Peisaj (implicit)", "landscape"), ("Portret", "portrait")]
        for label, _val in self._print_options:
            self.combo_print.addItem(label)
        orient = get_print_orientation()
        for i, (_label, val) in enumerate(self._print_options):
            if val == orient:
                self.combo_print.setCurrentIndex(i)
                break
        form.addRow("Orientare printare:", self.combo_print)
        form.addRow(QLabel("Se aplică la previzualizarea de printare din toate părțile."))
        return w

    def _refresh_personal_table(self) -> None:
        names = get_personal_names()
        self.personal_table.setRowCount(len(names))
        for i, n in enumerate(names):
            self.personal_table.setItem(i, 0, QTableWidgetItem(n))

    def _add_personal(self) -> None:
        text, ok = QInputDialog.getText(self, "Adaugă", "Nume, prenume:")
        if ok and text.strip():
            add_personal(text.strip())
            self._refresh_personal_table()

    def _edit_personal(self) -> None:
        row = self.personal_table.currentRow()
        if row < 0:
            return
        item = self.personal_table.item(row, 0)
        if not item:
            return
        text, ok = QInputDialog.getText(self, "Editează", "Nume:", text=item.text())
        if ok and text.strip():
            update_personal(item.text(), text.strip())
            self._refresh_personal_table()

    def _delete_personal(self) -> None:
        row = self.personal_table.currentRow()
        if row < 0:
            return
        item = self.personal_table.item(row, 0)
        if item:
            delete_personal(item.text())
            self._refresh_personal_table()

    def _save(self) -> None:
        apply_global_ranges(self.spin_persoane.value(), self.spin_activitati.value())
        set_biblioteca_info(self.edit_nume.text(), self.edit_localitate.text())
        idx = self.combo_autosave.currentIndex()
        if 0 <= idx < len(self._autosave_options):
            save_autosave_interval(self._autosave_options[idx][1])
        tidx = self.combo_theme.currentIndex()
        if 0 <= tidx < len(self._theme_options):
            set_ui_theme(self._theme_options[tidx][1])
        pidx = self.combo_print.currentIndex()
        if 0 <= pidx < len(self._print_options):
            set_print_orientation(self._print_options[pidx][1])
        if self.first_run:
            mark_setup_completed()
        self.accept()
