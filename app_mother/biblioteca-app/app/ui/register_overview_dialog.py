"""Overview registru complet: selectează/adaugă/elimină pagini, previzualizează și exportă final."""

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from core.constants_manager import LUNI_RO, get_cover_page
from ui.export.export_errors import format_export_error, run_export_with_progress
from ui.export.export_html import build_pages_html

ROLE_DATA = Qt.UserRole


class RegisterOverviewDialog(QDialog):
    def __init__(self, main_window, default_year: int | None = None) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Registru complet — overview și export final")
        self.resize(620, 720)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Bifați paginile (luni/categorii) pe care doriți să le includeți în registrul final.\n"
            "Lunile fără date apar ca pagini goale (le puteți completa din partea respectivă)."
        ))

        top = QHBoxLayout()
        top.addWidget(QLabel("Anul:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(default_year or date.today().year)
        self._year.valueChanged.connect(self._rebuild_tree)
        top.addWidget(self._year)
        top.addStretch()
        btn_all = QPushButton("Bifează tot")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Debifează tot")
        btn_none.clicked.connect(lambda: self._set_all(False))
        top.addWidget(btn_all)
        top.addWidget(btn_none)
        layout.addLayout(top)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Registru"])
        layout.addWidget(self._tree, stretch=1)

        self._cover_cb = QCheckBox("Include pagina de titlu (coperta)")
        self._cover_cb.setChecked(True)
        layout.addWidget(self._cover_cb)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Format:"))
        self._fmt = QComboBox()
        self._fmt.addItem("Word (.docx)", "word")
        self._fmt.addItem("PDF (.pdf)", "pdf")
        self._fmt.addItem("Excel (.xlsx)", "excel")
        bottom.addWidget(self._fmt)
        bottom.addStretch()
        btn_preview = QPushButton("👁 Previzualizare")
        btn_preview.clicked.connect(self._preview)
        btn_export = QPushButton("💾 Exportă registrul final")
        btn_export.setObjectName("btnSuccess")
        btn_export.clicked.connect(self._export)
        btn_close = QPushButton("Închide")
        btn_close.clicked.connect(self.reject)
        bottom.addWidget(btn_preview)
        bottom.addWidget(btn_export)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

        self._parts = []  # (roman, title, page_obj)
        self._build_parts()
        self._rebuild_tree()

    def _build_parts(self) -> None:
        from core.parts_registry import PARTS, PART_LAYOUT

        for roman, part_id, title, _short in PARTS:
            self._parts.append((roman, title, part_id))

    def _part_obj(self, part_id: str):
        return self.main_window._get_or_load_part(part_id)

    def _rebuild_tree(self) -> None:
        from core.parts_registry import PART_LAYOUT

        self._tree.clear()
        for roman, title, part_id in self._parts:
            mode, has_copii = PART_LAYOUT.get(part_id, ("daily", False))
            top = QTreeWidgetItem([f"Partea {roman}. {title}"])
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            top.setCheckState(0, Qt.Checked)
            self._tree.addTopLevelItem(top)

            cats = ["adulti", "copii"] if has_copii else [None]
            for cat in cats:
                cat_label = {"copii": "Copii", "adulti": "Adulți"}.get(cat, "")
                if mode in ("daily", "events"):
                    for m in range(1, 13):
                        label = (f"{cat_label} — " if cat_label else "") + LUNI_RO[m - 1]
                        leaf = QTreeWidgetItem([label])
                        leaf.setFlags(leaf.flags() | Qt.ItemIsUserCheckable)
                        leaf.setCheckState(0, Qt.Checked)
                        leaf.setData(0, ROLE_DATA, (part_id, m, cat))
                        top.addChild(leaf)
                else:
                    label = (f"{cat_label} — " if cat_label else "") + "Tot anul"
                    leaf = QTreeWidgetItem([label])
                    leaf.setFlags(leaf.flags() | Qt.ItemIsUserCheckable)
                    leaf.setCheckState(0, Qt.Checked)
                    leaf.setData(0, ROLE_DATA, (part_id, None, cat))
                    top.addChild(leaf)
            top.setExpanded(False)

    def _set_all(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).setCheckState(0, state)

    def _selected_pages(self) -> list[dict]:
        from ui.export.register_pages import iter_register_slots
        from core.parts_registry import PART_LAYOUT

        year = self._year.value()
        checked: set[tuple] = set()
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            for j in range(top.childCount()):
                leaf = top.child(j)
                if leaf.checkState(0) == Qt.Checked:
                    checked.add(leaf.data(0, ROLE_DATA))

        pages = []
        if self._cover_cb.isChecked():
            cover = get_cover_page()
            if not cover.get("an"):
                cover["an"] = str(year)
            cover["type"] = "cover"
            pages.append(cover)

        for _roman, part_id, _title, _short, cat in iter_register_slots():
            obj = self._part_obj(part_id)
            if obj is None:
                continue
            mode, _ = PART_LAYOUT.get(part_id, ("daily", False))
            if mode in ("daily", "events"):
                for m in range(1, 13):
                    if (part_id, m, cat) in checked:
                        pages.append(obj._build_page(year, m, cat))
            elif (part_id, None, cat) in checked:
                pages.append(obj._build_page(year, None, cat))
        return pages

    def _preview(self) -> None:
        pages = self._selected_pages()
        table_pages = [p for p in pages if p.get("type") != "cover"]
        if not table_pages and len(pages) == 0:
            QMessageBox.information(self, "Overview", "Nu ați selectat nicio pagină.")
            return
        from ui.export.print_presets import show_print_preview

        show_print_preview(self, pages, title="Previzualizare registru complet")

    def _export(self) -> None:
        pages = self._selected_pages()
        if not pages:
            QMessageBox.information(self, "Overview", "Nu ați selectat nicio pagină.")
            return
        fmt = self._fmt.currentData()
        ext = {"pdf": "pdf", "word": "docx", "excel": "xlsx"}[fmt]
        filt = {
            "pdf": "Fișier PDF (*.pdf)",
            "word": "Document Word (*.docx)",
            "excel": "Fișier Excel (*.xlsx)",
        }[fmt]
        from core.export_presets import set_export_folder, suggest_export_path

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvează registrul final",
            suggest_export_path(f"Registru_complet_{self._year.value()}.{ext}"),
            filt,
        )
        if not out_path:
            return
        set_export_folder(out_path)
        try:
            run_export_with_progress(
                self,
                fmt,
                out_path,
                pages,
                main_window=self.main_window,
                title="Export registru complet",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Eroare export", format_export_error(exc))
            return
        QMessageBox.information(
            self, "Export reușit", f"Registrul final ({len(pages)} pagini) a fost salvat:\n{out_path}"
        )
