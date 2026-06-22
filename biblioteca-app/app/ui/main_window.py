"""Fereastră principală — meniu lateral cu cele 12 Părți active."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.autosave import AutosaveManager
from core.constants_manager import APP_CREDIT, get_biblioteca_info
from ui import (
    part_01_utilizatori,
    part_02_utilizatori_copii_adulti,
    part_03_documente_inregistrate,
    part_04_documente_continut,
    part_05_cercetari_bibliografice,
    part_06_activitati_informare,
    part_07_documente_electronice,
    part_09_instruiri,
    part_11_activitati_culturale,
    part_12_activitati_online,
    part_13_parteneri,
    part_14_voluntariat,
)
from ui.setup_wizard import SetupWizard

PARTS: list[tuple[str, str, str, str]] = [
    ("I", "part_01", "Evidența utilizatorilor", "Utilizatori"),
    ("II", "part_02", "Evidența utilizatorilor (Copii / Adulți)", "Utilizatori"),
    ("III", "part_03", "Evidența documentelor înregistrate", "Documente"),
    ("IV", "part_04", "Evidența documentelor (conținut CZU)", "Documente"),
    ("V", "part_05", "Evidența cercetărilor bibliografice", "Cercetări"),
    ("VI", "part_06", "Evidența activităților de informare", "Informare"),
    ("VII", "part_07", "Evidența documentelor electronice online", "Electronice"),
    ("IX", "part_09", "Instruirea utilizatorilor bibliotecii", "Instruiri"),
    ("XI", "part_11", "Evidența activităților culturale și științifice", "Cultural"),
    ("XII", "part_12", "Evidența activităților culturale ONLINE", "Online"),
    ("XIII", "part_13", "Parteneri ai bibliotecii", "Parteneri"),
    ("XIV", "part_14", "Activități de voluntariat", "Voluntariat"),
]

PART_FACTORIES = {
    "part_01": part_01_utilizatori.create_page,
    "part_02": part_02_utilizatori_copii_adulti.create_page,
    "part_03": part_03_documente_inregistrate.create_page,
    "part_04": part_04_documente_continut.create_page,
    "part_05": part_05_cercetari_bibliografice.create_page,
    "part_06": part_06_activitati_informare.create_page,
    "part_07": part_07_documente_electronice.create_page,
    "part_09": part_09_instruiri.create_page,
    "part_11": part_11_activitati_culturale.create_page,
    "part_12": part_12_activitati_online.create_page,
    "part_13": part_13_parteneri.create_page,
    "part_14": part_14_voluntariat.create_page,
}

# mode + tab copii/adulți — pentru arborele din Registru final fără a încărca toate paginile
PART_LAYOUT: dict[str, tuple[str, bool]] = {
    "part_01": ("daily", False),
    "part_02": ("daily", True),
    "part_03": ("daily", False),
    "part_04": ("daily", False),
    "part_05": ("events", False),
    "part_06": ("events", True),
    "part_07": ("monthly", False),
    "part_09": ("events", False),
    "part_11": ("events", True),
    "part_12": ("events", True),
    "part_13": ("crud", False),
    "part_14": ("crud", False),
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Registru Digital de Evidență a Activității Bibliotecii")
        self.setMinimumSize(1200, 720)
        self.resize(1360, 860)

        self._part_pages: dict[str, QWidget] = {}
        self._part_placeholders: dict[str, int] = {}
        self._loaded_parts: set[str] = set()
        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._autosave = AutosaveManager(self)

        self._get_or_load_part(PARTS[0][1])
        self._part_list.setCurrentRow(0)

    def _build_menu(self) -> None:
        menu_setari = self.menuBar().addMenu("Setări")
        act_setup = QAction("Setup…", self)
        act_setup.setShortcut("Ctrl+,")
        act_setup.triggered.connect(self._open_setup)
        menu_setari.addAction(act_setup)

        act_cover = QAction("Pagina de titlu (copertă)…", self)
        act_cover.triggered.connect(self._open_cover)
        menu_setari.addAction(act_cover)

        act_excluded = QAction("Zile nelucrătoare (concediu)…", self)
        act_excluded.triggered.connect(self._open_excluded_days)
        menu_setari.addAction(act_excluded)

        menu_fisier = self.menuBar().addMenu("Fișier")
        act_overview = QAction("Registru complet (overview)…", self)
        act_overview.setShortcut("Ctrl+R")
        act_overview.triggered.connect(self._open_overview)
        menu_fisier.addAction(act_overview)
        act_export = QAction("Exportă pagina curentă…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self._export_current)
        menu_fisier.addAction(act_export)
        menu_fisier.addSeparator()
        act_exit = QAction("Ieșire", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_fisier.addAction(act_exit)

    def _export_current(self) -> None:
        page = self._content_stack.currentWidget()
        if hasattr(page, "_export"):
            page._export()

    def _open_cover(self) -> None:
        from ui.cover_page_dialog import CoverPageDialog

        CoverPageDialog(self).exec()

    def _open_excluded_days(self) -> None:
        from datetime import date

        from ui.excluded_days_dialog import ExcludedDaysDialog

        page = self._content_stack.currentWidget()
        year = getattr(page, "year", None) or date.today().year
        if ExcludedDaysDialog(self, default_year=year).exec():
            self.statusBar().showMessage(
                "Zilele nelucrătoare au fost salvate. Regenerați lunile afectate dacă e nevoie.",
                8000,
            )

    def _open_overview(self) -> None:
        self._show_register_final()

    def _show_register_final(self) -> None:
        page = self._content_stack.currentWidget()
        year = getattr(page, "year", None) if page != self._register_final_page else None
        if year:
            self._register_final_page._year.setValue(year)
        self._part_list.blockSignals(True)
        self._part_list.clearSelection()
        self._part_list.blockSignals(False)
        self._register_final_page.refresh()
        self._content_stack.setCurrentWidget(self._register_final_page)
        self.statusBar().showMessage(
            "Registru final — selectați pagini, previzualizați sau exportați versiunea numerotată",
            6000,
        )

    def navigate_to_part(
        self, part_id: str, month: int | None = None, category: str | None = None
    ) -> None:
        for row in range(self._part_list.count()):
            item = self._part_list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == part_id:
                self._part_list.blockSignals(True)
                self._part_list.setCurrentRow(row)
                self._part_list.blockSignals(False)
                break
        page = self._get_or_load_part(part_id)
        if page is None:
            return
        self._content_stack.setCurrentWidget(page)
        if hasattr(page, "navigate_to"):
            page.navigate_to(month=month, category=category)
        self._autosave.on_page_changed()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentStack")
        root.addWidget(self._content_stack, stretch=1)

        from ui.register_final_page import RegisterFinalPage

        self._register_final_page = RegisterFinalPage(self)
        self._content_stack.addWidget(self._register_final_page)

        for _roman, part_id, _title, _short in PARTS:
            placeholder = QWidget()
            self._part_pages[part_id] = placeholder
            idx = self._content_stack.addWidget(placeholder)
            self._part_placeholders[part_id] = idx

    def _build_sidebar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("sidebar")
        frame.setFixedWidth(268)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(6)

        logo = QLabel("📚")
        logo.setObjectName("sidebarLogo")
        layout.addWidget(logo)

        app_title = QLabel("Registru Digital")
        app_title.setObjectName("sidebarTitle")
        layout.addWidget(app_title)

        nume, loc = get_biblioteca_info()
        lib_text = nume if nume else "Bibliotecă"
        if loc:
            lib_text += f"\n{loc}"
        self._library_label = QLabel(lib_text)
        self._library_label.setObjectName("sidebarLibrary")
        self._library_label.setWordWrap(True)
        layout.addWidget(self._library_label)

        subtitle = QLabel("PĂRȚI ACTIVE")
        subtitle.setObjectName("sidebarSubtitle")
        layout.addWidget(subtitle)

        self._part_list = QListWidget()
        self._part_list.setObjectName("partList")
        for roman, part_id, title, short in PARTS:
            item = QListWidgetItem(f"  {roman}   {short}")
            item.setToolTip(title)
            item.setData(Qt.ItemDataRole.UserRole, part_id)
            self._part_list.addItem(item)

        self._part_list.currentRowChanged.connect(self._on_part_selected)
        layout.addWidget(self._part_list, stretch=1)

        btn_final = QPushButton("📋  Registru final")
        btn_final.setObjectName("btnRegisterFinal")
        btn_final.setToolTip("Editare finală pe an — toate părțile, lunile, pagini numerotate")
        btn_final.clicked.connect(self._show_register_final)
        layout.addWidget(btn_final)

        footer = QLabel(f"100% offline · date locale\n{APP_CREDIT}")
        footer.setObjectName("sidebarSubtitle")
        layout.addWidget(footer)
        return frame

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Gata — selectați o Parte din meniul stâng")
        self._credit_label = QLabel(APP_CREDIT)
        self._credit_label.setObjectName("appCredit")
        status.addPermanentWidget(self._credit_label)
        self._save_label = QLabel("Salvat ✓")
        self._save_label.setObjectName("saveIndicator")
        status.addPermanentWidget(self._save_label)

    def _on_part_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self._part_list.item(row)
        if item is None:
            return
        part_id = item.data(Qt.ItemDataRole.UserRole)
        page = self._get_or_load_part(part_id)
        if page is not None:
            self._content_stack.setCurrentWidget(page)
            self.statusBar().showMessage(item.toolTip())
            self._autosave.on_page_changed()

    def _get_or_load_part(self, part_id: str) -> QWidget | None:
        if part_id not in self._loaded_parts:
            factory = PART_FACTORIES.get(part_id)
            if factory is None:
                return None
            page = factory(self)
            idx = self._part_placeholders[part_id]
            old = self._content_stack.widget(idx)
            self._content_stack.removeWidget(old)
            old.deleteLater()
            self._content_stack.insertWidget(idx, page)
            self._part_pages[part_id] = page
            self._loaded_parts.add(part_id)
        return self._part_pages.get(part_id)

    def _open_setup(self) -> None:
        dlg = SetupWizard(first_run=False, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            nume, loc = get_biblioteca_info()
            lib_text = nume if nume else "Bibliotecă"
            if loc:
                lib_text += f"\n{loc}"
            self._library_label.setText(lib_text)

    def set_save_status(self, saved: bool) -> None:
        if saved:
            self._save_label.setText("Salvat ✓")
            self._save_label.setProperty("saving", "false")
        else:
            self._save_label.setText("Se salvează…")
            self._save_label.setProperty("saving", "true")
        self._save_label.style().unpolish(self._save_label)
        self._save_label.style().polish(self._save_label)

    def select_part(self, part_id: str) -> None:
        for row in range(self._part_list.count()):
            item = self._part_list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == part_id:
                self._part_list.setCurrentRow(row)
                break
