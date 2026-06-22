"""Fereastră principală — meniu lateral cu cele 12 Părți active."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.autosave import AutosaveManager
from core.constants_manager import APP_CREDIT, get_biblioteca_info
from core.parts_registry import PARTS, PART_LAYOUT, get_part_factory
from database.backup import create_backup, list_backups, restore_backup
from ui.help_dialog import HelpDialog
from ui.setup_wizard import SetupWizard

# Re-export pentru module care importă din main_window
__all__ = ["MainWindow", "PARTS", "PART_LAYOUT"]


class MainWindow(QMainWindow):
    def __init__(self, *, load_first_part: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("Registru Digital de Evidență a Activității Bibliotecii")
        self.setMinimumSize(1200, 720)
        self.resize(1360, 860)

        self._part_pages: dict[str, QWidget] = {}
        self._part_placeholders: dict[str, int] = {}
        self._loaded_parts: set[str] = set()
        self._export_in_progress = False
        self._last_save_at: datetime | None = None
        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._autosave = AutosaveManager(self)

        if load_first_part:
            self.load_initial_part()

    def load_initial_part(self) -> None:
        self._part_list.blockSignals(True)
        self._get_or_load_part(PARTS[0][1])
        self._part_list.setCurrentRow(0)
        self._part_list.blockSignals(False)
        page = self._part_pages.get(PARTS[0][1])
        if page is not None:
            self._content_stack.setCurrentWidget(page)

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
        act_save = QAction("Salvează pagina curentă", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_current)
        menu_fisier.addAction(act_save)

        act_overview = QAction("Registru complet (overview)…", self)
        act_overview.setShortcut("Ctrl+R")
        act_overview.triggered.connect(self._open_overview)
        menu_fisier.addAction(act_overview)

        act_export = QAction("Exportă pagina curentă…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self._export_current)
        menu_fisier.addAction(act_export)

        menu_fisier.addSeparator()
        act_backup = QAction("Salvează copie registru (backup)…", self)
        act_backup.triggered.connect(self._backup_database)
        menu_fisier.addAction(act_backup)

        act_restore = QAction("Restaurează din copie…", self)
        act_restore.triggered.connect(self._restore_database)
        menu_fisier.addAction(act_restore)

        menu_fisier.addSeparator()
        act_exit = QAction("Ieșire", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_fisier.addAction(act_exit)

        menu_ajutor = self.menuBar().addMenu("Ajutor")
        act_help = QAction("Scurtături tastatură…", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(self._show_help)
        menu_ajutor.addAction(act_help)

    def _save_current(self) -> None:
        page = self._content_stack.currentWidget()
        if hasattr(page, "save_all"):
            page.save_all(show_status=True)

    def _show_help(self) -> None:
        HelpDialog(self).exec()

    def _backup_database(self) -> None:
        try:
            path = create_backup("manual")
            QMessageBox.information(
                self,
                "Backup reușit",
                f"Copia registrului a fost salvată:\n{path}",
            )
        except OSError as exc:
            QMessageBox.warning(self, "Backup", f"Nu s-a putut crea copia:\n{exc}")

    def _restore_database(self) -> None:
        backups = list_backups()
        if not backups:
            QMessageBox.information(
                self,
                "Restaurare",
                "Nu există copii de rezervă în folderul backups.",
            )
            return
        default = str(backups[0])
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selectați copia de restaurat",
            default,
            "Bază de date (*.db)",
        )
        if not path:
            return
        reply = QMessageBox.warning(
            self,
            "Confirmare restaurare",
            "Restaurarea înlocuiește datele curente. Aplicația va reporni.\n\nContinuați?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            restore_backup(Path(path))
        except OSError as exc:
            QMessageBox.warning(self, "Restaurare", f"Restaurarea a eșuat:\n{exc}")
            return
        QMessageBox.information(
            self,
            "Restaurare reușită",
            "Datele au fost restaurate. Reporniți aplicația.",
        )

    def _export_current(self) -> None:
        page = self._content_stack.currentWidget()
        if hasattr(page, "_export"):
            page._export()
            return
        QMessageBox.information(
            self,
            "Export",
            "Selectați o parte din registru pentru export.",
        )

    def notify_saved(self) -> None:
        self._last_save_at = datetime.now()
        self.set_save_status(True)
        ts = self._last_save_at.strftime("%H:%M:%S")
        self._save_label.setToolTip(f"Ultima salvare: {ts}")

    def closeEvent(self, event: QCloseEvent) -> None:
        page = self._content_stack.currentWidget()
        if hasattr(page, "flush_pending_save"):
            page.flush_pending_save()
        self._autosave.on_page_changed()
        super().closeEvent(event)

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
            factory = get_part_factory(part_id)
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
            text = "Salvat ✓"
            if self._last_save_at:
                text = f"Salvat ✓ {self._last_save_at.strftime('%H:%M')}"
            self._save_label.setText(text)
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
