"""Fereastră principală — meniu lateral cu cele 12 Părți active."""

from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QCloseEvent, QDesktopServices, QKeySequence, QResizeEvent
from PyQt5.QtWidgets import (
    QAction,
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

from core.app_restart import restart_application
from core.autosave import AutosaveManager, get_autosave_interval
from core.ui_theme import load_stylesheet
from core.constants_manager import APP_CREDIT, get_biblioteca_info
from core.part_progress import compute_part_progress
from core.parts_registry import PARTS, PART_LAYOUT, get_part_factory
from core.session_state import load_session, save_session
from database.backup import create_backup, ensure_backup_dir, list_backups, restore_backup
from ui.excel_import.import_dialog import ImportExcelDialog
from ui.about_dialog import AboutDialog
from ui.help_dialog import HelpDialog
from ui.home_page import HomePage
from ui.incomplete_months_dialog import IncompleteMonthsDialog
from ui.setup_wizard import SetupWizard
from ui.widgets.toast import ToastHost
from ui.year_end_wizard import YearEndWizard

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
        self._register_final_page = None
        self._register_final_idx: int | None = None
        self._export_in_progress = False
        self._last_save_at: datetime | None = None
        self._part_tooltips: dict[str, str] = {}
        self._part_label_meta: dict[str, tuple[str, str]] = {}
        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._autosave = AutosaveManager(self)
        self.refresh_sidebar_badges(self._home_page.year)

        if load_first_part:
            self.show_home()

    def show_home(self) -> None:
        """Panou Acasă — vedere de ansamblu la pornire."""
        old_page = self._content_stack.currentWidget()
        if old_page is not self._home_page:
            self._autosave.save_leaving_page(old_page)
        self._home_page.refresh()
        self._content_stack.setCurrentWidget(self._home_page)
        self._part_list.blockSignals(True)
        self._part_list.clearSelection()
        self._part_list.blockSignals(False)
        if hasattr(self, "_btn_home"):
            self._btn_home.setChecked(True)
        self.statusBar().showMessage("Acasă — progres registru pe anul selectat")

    def continue_last_session(self) -> None:
        """Deschide ultima parte / an / lună salvate în sesiune."""
        session = load_session()
        part_id = session.get("part_id", PARTS[0][1])
        if not any(pid == part_id for _roman, pid, _title, _short in PARTS):
            part_id = PARTS[0][1]

        for row in range(self._part_list.count()):
            item = self._part_list.item(row)
            if item and item.data(Qt.UserRole) == part_id:
                self._part_list.blockSignals(True)
                self._part_list.setCurrentRow(row)
                self._part_list.blockSignals(False)
                break

        page = self._get_or_load_part(part_id)
        if page is None:
            return
        if hasattr(page, "apply_session_state"):
            year = session.get("year")
            month = session.get("month")
            if isinstance(year, int):
                page.apply_session_state(year, month if isinstance(month, int) else None)
        self._content_stack.setCurrentWidget(page)
        if hasattr(self, "_btn_home"):
            self._btn_home.setChecked(False)
        self.persist_session_from_page(page)
        self.statusBar().showMessage(self._part_tooltips.get(part_id, ""))

    def load_initial_part(self) -> None:
        """Compatibilitate — afișează panoul Acasă."""
        self.show_home()

    def refresh_sidebar_badges(self, year: int) -> None:
        if not hasattr(self, "_part_list"):
            return
        progress = compute_part_progress(year)
        status_labels = {
            "complete": "completă",
            "attention": "necesită atenție",
            "empty": "neîncepută",
        }
        for row in range(self._part_list.count()):
            item = self._part_list.item(row)
            if item is None:
                continue
            part_id = item.data(Qt.UserRole)
            meta = self._part_label_meta.get(part_id)
            if not meta:
                continue
            roman, short = meta
            prog = progress.get(part_id)
            badge = prog.badge if prog else "·"
            item.setText(f"  {roman}   {short:<10} {badge}")
            title = self._part_tooltips.get(part_id, "")
            if prog:
                item.setToolTip(f"{title}\nAn {year}: {status_labels.get(prog.status, '')}")
            else:
                item.setToolTip(title)

    def maybe_show_onboarding(self) -> None:
        from core.onboarding import is_onboarding_completed
        from ui.onboarding_tour import OnboardingTourDialog

        if not is_onboarding_completed():
            OnboardingTourDialog(self).exec()

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
        act_home = QAction("Acasă", self)
        act_home.setShortcut("Ctrl+H")
        act_home.triggered.connect(self.show_home)
        menu_fisier.addAction(act_home)
        menu_fisier.addSeparator()
        act_save = QAction("Salvează pagina curentă", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_current)
        menu_fisier.addAction(act_save)

        act_overview = QAction("Registru complet (overview)…", self)
        act_overview.setShortcut("Ctrl+R")
        act_overview.triggered.connect(self._open_overview)
        menu_fisier.addAction(act_overview)

        act_incomplete = QAction("Luni fără date…", self)
        act_incomplete.triggered.connect(self._open_incomplete_months)
        menu_fisier.addAction(act_incomplete)

        act_year_end = QAction("Asistent închidere an…", self)
        act_year_end.triggered.connect(self._open_year_end_wizard)
        menu_fisier.addAction(act_year_end)

        act_export = QAction("Exportă pagina curentă…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self._export_current)
        menu_fisier.addAction(act_export)

        act_import = QAction("Importă din Excel…", self)
        act_import.triggered.connect(self._import_excel)
        menu_fisier.addAction(act_import)

        menu_fisier.addSeparator()
        act_backup = QAction("Salvează copie registru (backup)…", self)
        act_backup.triggered.connect(self._backup_database)
        menu_fisier.addAction(act_backup)

        act_restore = QAction("Restaurează din copie…", self)
        act_restore.triggered.connect(self._restore_database)
        menu_fisier.addAction(act_restore)

        act_open_backups = QAction("Deschide folderul copii de rezervă…", self)
        act_open_backups.triggered.connect(self._open_backups_folder)
        menu_fisier.addAction(act_open_backups)

        menu_fisier.addSeparator()
        act_exit = QAction("Ieșire", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_fisier.addAction(act_exit)

        menu_ajutor = self.menuBar().addMenu("Ajutor")
        act_guide = QAction("Ghid rapid pentru bibliotecar…", self)
        act_guide.triggered.connect(self._open_user_guide)
        menu_ajutor.addAction(act_guide)

        act_help = QAction("Scurtături tastatură…", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(self._show_help)
        menu_ajutor.addAction(act_help)

        act_about = QAction("Despre…", self)
        act_about.triggered.connect(self._show_about)
        menu_ajutor.addAction(act_about)

    def _save_current(self) -> None:
        page = self._content_stack.currentWidget()
        if hasattr(page, "save_all"):
            page.save_all(show_status=True)

    def _show_help(self) -> None:
        HelpDialog(self).exec()

    def _open_user_guide(self) -> None:
        from core.user_guide import open_user_guide

        open_user_guide(self)

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _backup_database(self) -> None:
        try:
            path = create_backup("manual")
            self.show_toast(f"Copie de rezervă salvată\n{path.name}", duration_ms=4000)
        except OSError as exc:
            QMessageBox.warning(self, "Backup", f"Nu s-a putut crea copia:\n{exc}")

    def _import_excel(self) -> None:
        page = self._content_stack.currentWidget()
        part_id = getattr(page, "part_id", None)
        dlg = ImportExcelDialog(self, default_part_id=part_id)
        if dlg.exec() == dlg.Accepted:
            if hasattr(page, "_invalidate_caches"):
                page._invalidate_caches()
            if hasattr(page, "_load_current"):
                page._load_current()

    def _open_backups_folder(self) -> None:
        folder = ensure_backup_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

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
            "Copii registru (*.db)",
        )
        if not path:
            return
        reply = QMessageBox.warning(
            self,
            "Confirmare restaurare",
            "Restaurarea înlocuiește datele curente. Aplicația va reporni.\n\nContinuați?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            pre_restore = restore_backup(Path(path))
        except OSError as exc:
            QMessageBox.warning(self, "Restaurare", f"Restaurarea a eșuat:\n{exc}")
            return
        detail = "Datele au fost restaurate. Aplicația se repornește…"
        if pre_restore is not None:
            detail += f"\n\nCopie de siguranță a datelor curente:\n{pre_restore}"
        QMessageBox.information(self, "Restaurare reușită", detail)
        restart_application()

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
        self.clear_save_error()
        self._last_save_at = datetime.now()
        self.set_save_status(True)
        ts = self._last_save_at.strftime("%H:%M:%S")
        self._save_label.setToolTip(f"Ultima salvare: {ts}")
        self.show_toast(f"Salvat ✓  {ts}")

    def show_toast(self, message: str, *, kind: str = "success", duration_ms: int = 2800) -> None:
        if hasattr(self, "_toast"):
            self._toast.show_message(message, duration_ms=duration_ms, kind=kind)

    def show_save_error(self, message: str) -> None:
        self._save_error_banner.setText(message)
        self._save_error_banner.setVisible(True)
        self.set_save_status(False)

    def clear_save_error(self) -> None:
        self._save_error_banner.setVisible(False)

    @staticmethod
    def _resolve_page_year(page) -> int | None:
        if page is None:
            return None
        spin = getattr(page, "_year", None)
        if spin is not None and hasattr(spin, "value"):
            return int(spin.value())
        year = getattr(page, "year", None)
        if callable(year):
            year = year()
        return year if isinstance(year, int) else None

    @staticmethod
    def _resolve_page_month(page) -> int | None:
        if not getattr(page, "_has_month_bar", False):
            return None
        month = getattr(page, "month", None)
        if callable(month):
            month = month()
        return month if isinstance(month, int) else None

    @staticmethod
    def _page_year(page) -> int:
        from datetime import date

        return MainWindow._resolve_page_year(page) or date.today().year

    def persist_session_from_page(self, page) -> None:
        part_id = self._part_id_for_page(page)
        if part_id is None:
            return
        save_session(
            part_id=part_id,
            year=self._resolve_page_year(page),
            month=self._resolve_page_month(page),
        )

    def _part_id_for_page(self, page) -> str | None:
        for part_id, part_page in self._part_pages.items():
            if part_page is page:
                return part_id
        return None

    def _any_unsaved_changes(self) -> bool:
        for part_id in self._loaded_parts:
            page = self._part_pages.get(part_id)
            if page is not None and hasattr(page, "has_unsaved_changes"):
                if page.has_unsaved_changes():
                    return True
        return False

    def _save_all_dirty_pages(self) -> bool:
        ok = True
        for part_id in self._loaded_parts:
            page = self._part_pages.get(part_id)
            if page is None or not hasattr(page, "save_all"):
                continue
            if hasattr(page, "has_unsaved_changes") and page.has_unsaved_changes():
                if not page.save_all(show_status=False):
                    ok = False
        if ok:
            self.notify_saved()
        return ok

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._any_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Modificări nesalvate",
                "Există modificări care nu au fost salvate.\n\nSalvați înainte de ieșire?",
                QMessageBox.Save
                | QMessageBox.Discard
                | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.Save:
                if not self._save_all_dirty_pages():
                    QMessageBox.warning(
                        self,
                        "Salvare eșuată",
                        "Nu s-au putut salva toate modificările. Ieșirea a fost anulată.",
                    )
                    event.ignore()
                    return
        else:
            page = self._content_stack.currentWidget()
            if hasattr(page, "flush_pending_save"):
                if not page.flush_pending_save():
                    QMessageBox.warning(
                        self,
                        "Salvare eșuată",
                        "Nu s-au putut salva datele în așteptare. Ieșirea a fost anulată.",
                    )
                    event.ignore()
                    return
            self._autosave.on_page_changed()

        page = self._content_stack.currentWidget()
        if page is not None:
            self.persist_session_from_page(page)
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_toast"):
            self._toast._reposition()

    def _open_cover(self) -> None:
        from ui.cover_page_dialog import CoverPageDialog

        CoverPageDialog(self).exec()

    def _open_excluded_days(self) -> None:
        from core.date_engine import purge_excluded_days_from_registers
        from ui.excluded_days_dialog import ExcludedDaysDialog

        page = self._content_stack.currentWidget()
        year = self._page_year(page)
        month = self._resolve_page_month(page)
        dlg = ExcludedDaysDialog(self, default_year=year, default_month=month)
        if dlg.exec():
            saved_year = dlg.saved_year() or year
            purge_excluded_days_from_registers(saved_year)
            self._refresh_parts_after_excluded_days(saved_year)
            self.statusBar().showMessage(
                "Zilele nelucrătoare au fost salvate. Registrul a fost actualizat.",
                8000,
            )

    def _refresh_parts_after_excluded_days(self, year: int) -> None:
        skipped_dirty: list[str] = []
        for part_id in list(self._loaded_parts):
            page = self._part_pages.get(part_id)
            if page is None:
                continue
            if hasattr(page, "has_unsaved_changes") and page.has_unsaved_changes():
                skipped_dirty.append(part_id)
                continue
            if hasattr(page, "_invalidate_caches"):
                page._invalidate_caches()
            page_year = self._resolve_page_year(page)
            if page_year == year and hasattr(page, "_load_current"):
                page._load_current()
        current = self._content_stack.currentWidget()
        if (
            current is not None
            and hasattr(current, "_load_current")
            and not (
                hasattr(current, "has_unsaved_changes") and current.has_unsaved_changes()
            )
        ):
            current._load_current()
        if hasattr(self, "_home_page"):
            self._home_page.refresh()
        if skipped_dirty:
            self.statusBar().showMessage(
                "Zilele nelucrătoare au fost salvate. Părțile cu modificări nesalvate "
                "nu au fost reîncărcate — salvați sau reveniți după salvare.",
                12000,
            )

    def _open_incomplete_months(self) -> None:
        page = self._content_stack.currentWidget()
        IncompleteMonthsDialog(self, default_year=self._page_year(page)).exec()

    def _open_year_end_wizard(self) -> None:
        page = self._content_stack.currentWidget()
        YearEndWizard(self, default_year=self._page_year(page)).exec()

    def _open_overview(self) -> None:
        from ui.register_overview_dialog import RegisterOverviewDialog

        page = self._content_stack.currentWidget()
        RegisterOverviewDialog(self, default_year=self._page_year(page)).exec()

    def _get_or_load_register_final(self):
        if self._register_final_page is None:
            from ui.register_final_page import RegisterFinalPage

            page = RegisterFinalPage(self)
            idx = self._register_final_idx
            old = self._content_stack.widget(idx)
            self._content_stack.removeWidget(old)
            old.deleteLater()
            self._content_stack.insertWidget(idx, page)
            self._register_final_page = page
        return self._register_final_page

    def _show_register_final(self) -> None:
        page = self._content_stack.currentWidget()
        register_final = self._get_or_load_register_final()
        year = self._resolve_page_year(page)
        if year is not None:
            register_final._year.setValue(year)
        self._part_list.blockSignals(True)
        self._part_list.clearSelection()
        self._part_list.blockSignals(False)
        if page is not register_final:
            self._autosave.save_leaving_page(page)
        register_final.refresh()
        self._content_stack.setCurrentWidget(register_final)
        if hasattr(self, "_btn_home"):
            self._btn_home.setChecked(False)
        self.statusBar().showMessage(
            "Registru final — selectați pagini, previzualizați sau exportați versiunea numerotată",
            6000,
        )

    def navigate_to_part(
        self, part_id: str, month: int | None = None, category: str | None = None
    ) -> None:
        old_page = self._content_stack.currentWidget()
        for row in range(self._part_list.count()):
            item = self._part_list.item(row)
            if item and item.data(Qt.UserRole) == part_id:
                self._part_list.blockSignals(True)
                self._part_list.setCurrentRow(row)
                self._part_list.blockSignals(False)
                break
        page = self._get_or_load_part(part_id)
        if page is None:
            return
        if old_page is not page:
            self._autosave.save_leaving_page(old_page)
        self._content_stack.setCurrentWidget(page)
        if hasattr(self, "_btn_home"):
            self._btn_home.setChecked(False)
        if hasattr(page, "navigate_to"):
            page.navigate_to(month=month, category=category)
        elif hasattr(page, "_load_current"):
            page._load_current(fast=True)
        self.persist_session_from_page(page)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._content_panel = QWidget()
        panel_layout = QVBoxLayout(self._content_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self._save_error_banner = QLabel()
        self._save_error_banner.setObjectName("saveErrorBanner")
        self._save_error_banner.setWordWrap(True)
        self._save_error_banner.setVisible(False)
        panel_layout.addWidget(self._save_error_banner)

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentStack")
        panel_layout.addWidget(self._content_stack, stretch=1)
        self._toast = ToastHost(self._content_panel)

        self._home_page = HomePage(self)
        self._home_idx = self._content_stack.addWidget(self._home_page)

        placeholder = QWidget()
        self._register_final_idx = self._content_stack.addWidget(placeholder)

        for _roman, part_id, _title, _short in PARTS:
            placeholder = QWidget()
            self._part_pages[part_id] = placeholder
            idx = self._content_stack.addWidget(placeholder)
            self._part_placeholders[part_id] = idx

        root.addWidget(self._build_sidebar())
        root.addWidget(self._content_panel, stretch=1)

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

        self._btn_home = QPushButton("🏠  Acasă")
        self._btn_home.setObjectName("btnHome")
        self._btn_home.setCheckable(True)
        self._btn_home.setChecked(True)
        self._btn_home.clicked.connect(self.show_home)
        layout.addWidget(self._btn_home)

        self._part_list = QListWidget()
        self._part_list.setObjectName("partList")
        for roman, part_id, title, short in PARTS:
            self._part_tooltips[part_id] = title
            self._part_label_meta[part_id] = (roman, short)
            item = QListWidgetItem(f"  {roman}   {short}")
            item.setToolTip(title)
            item.setData(Qt.UserRole, part_id)
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
        part_id = item.data(Qt.UserRole)
        old_page = self._content_stack.currentWidget()
        page = self._get_or_load_part(part_id)
        if page is not None:
            if old_page is not page:
                self._autosave.save_leaving_page(old_page)
            self._content_stack.setCurrentWidget(page)
            if hasattr(self, "_btn_home"):
                self._btn_home.setChecked(False)
            if hasattr(page, "_load_current"):
                page._load_current(fast=True)
            self.statusBar().showMessage(item.toolTip())
            self.persist_session_from_page(page)

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
        if dlg.exec() == dlg.Accepted:
            nume, loc = get_biblioteca_info()
            lib_text = nume if nume else "Bibliotecă"
            if loc:
                lib_text += f"\n{loc}"
            self._library_label.setText(lib_text)
            self._autosave.set_interval(get_autosave_interval())
            from pathlib import Path

            from PyQt5.QtWidgets import QApplication

            app_root = Path(__file__).resolve().parent.parent
            app = QApplication.instance()
            if app is not None:
                load_stylesheet(app, app_root)

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
            if item and item.data(Qt.UserRole) == part_id:
                self._part_list.setCurrentRow(row)
                break
