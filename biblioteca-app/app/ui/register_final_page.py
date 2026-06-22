"""Pagină dedicată: Registru final pe an — previzualizare, numerotare, editare, export."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import LUNI_RO, get_cover_page
from ui.export.export_errors import format_export_error, run_export_with_progress
from ui.export.export_html import build_pages_html

ROLE_META = Qt.ItemDataRole.UserRole


class RegisterFinalPage(QWidget):
    """Editor final pentru întreg registrul pe an — vizibil permanent din meniul stâng."""

    def __init__(self, main_window) -> None:
        super().__init__()
        self.main_window = main_window
        self.setObjectName("pageContainer")
        self._build_ui()

    def _get_page_obj(self, part_id: str):
        """Pagina încărcată din meniu — fără widget-uri duplicate în arbore."""
        return self.main_window._get_or_load_part(part_id)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        header = QFrame()
        header.setObjectName("pageHeaderCard")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(16, 14, 16, 14)
        t1 = QLabel("Registru final — versiunea pe an")
        t1.setObjectName("pageHeading")
        t2 = QLabel(
            "Aici vedeți toate paginile numerotate ale registrului. "
            "Bifați ce includeți, dublu-click pe o pagină pentru a o edita, "
            "apoi previzualizați sau exportați documentul final."
        )
        t2.setWordWrap(True)
        t2.setObjectName("pageSubheading")
        hl.addWidget(t1)
        hl.addWidget(t2)
        outer.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName("toolBarCard")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 10, 12, 10)
        tb.addWidget(QLabel("Anul:"))
        self._year = QSpinBox()
        self._year.setRange(2000, 2100)
        self._year.setValue(date.today().year)
        self._year.valueChanged.connect(self.refresh)
        tb.addWidget(self._year)
        tb.addStretch()
        btn_all = QPushButton("Bifează tot")
        btn_none = QPushButton("Debifează tot")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none.clicked.connect(lambda: self._set_all(False))
        tb.addWidget(btn_all)
        tb.addWidget(btn_none)
        outer.addWidget(toolbar)

        self._cover_cb = QCheckBox("Include pagina de titlu (copertă)")
        self._cover_cb.setChecked(True)
        self._cover_cb.stateChanged.connect(self._update_summary)
        outer.addWidget(self._cover_cb)

        split = QSplitter(Qt.Orientation.Horizontal)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Pag.", "Conținut pagină", "Include"])
        self._tree.setColumnWidth(0, 52)
        self._tree.setColumnWidth(1, 340)
        self._tree.itemChanged.connect(self._update_summary)
        self._tree.itemDoubleClicked.connect(self._open_page_for_edit)
        split.addWidget(self._tree)

        preview_card = QFrame()
        preview_card.setObjectName("tableCard")
        pl = QVBoxLayout(preview_card)
        pl.setContentsMargins(12, 12, 12, 12)
        pl.addWidget(QLabel("Previzualizare pagină selectată"))
        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(False)
        pl.addWidget(self._preview, stretch=1)
        split.addWidget(preview_card)
        split.setSizes([420, 560])
        outer.addWidget(split, stretch=1)

        self._summary = QLabel()
        self._summary.setObjectName("scrollHint")
        outer.addWidget(self._summary)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Format export:"))
        self._fmt = QComboBox()
        self._fmt.addItem("Word (.docx)", "word")
        self._fmt.addItem("PDF (.pdf)", "pdf")
        self._fmt.addItem("Excel (.xlsx)", "excel")
        bottom.addWidget(self._fmt)
        bottom.addStretch()
        btn_edit = QPushButton("✏️ Editează pagina selectată")
        btn_edit.clicked.connect(self._open_selected_for_edit)
        btn_preview = QPushButton("👁 Previzualizare completă")
        btn_preview.clicked.connect(self._preview_full)
        btn_export = QPushButton("💾 Exportă registrul final")
        btn_export.setObjectName("btnSuccess")
        btn_export.clicked.connect(self._export)
        bottom.addWidget(btn_edit)
        bottom.addWidget(btn_preview)
        bottom.addWidget(btn_export)
        outer.addLayout(bottom)

        self._tree.currentItemChanged.connect(self._on_selection_changed)

    def refresh(self) -> None:
        from core.parts_registry import PART_LAYOUT
        from ui.export.register_pages import iter_register_slots

        self._tree.blockSignals(True)
        self._tree.clear()
        page_no = 1
        year = self._year.value()

        if self._cover_cb.isChecked():
            item = QTreeWidgetItem([str(page_no), "Copertă — Pagina de titlu", ""])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(2, Qt.CheckState.Checked)
            item.setData(0, ROLE_META, {"type": "cover", "year": year})
            self._tree.addTopLevelItem(item)
            page_no += 1

        for roman, part_id, title, _short, cat in iter_register_slots():
            mode, _has_copii = PART_LAYOUT.get(part_id, ("daily", False))
            cat_label = {"adulti": "Adulți", "copii": "Copii"}.get(cat, "") if cat else ""
            if mode in ("daily", "events"):
                for m in range(1, 13):
                    label = f"Partea {roman}. {title}"
                    if cat_label:
                        label += f" — {cat_label}"
                    label += f" — {LUNI_RO[m - 1]} {year}"
                    item = QTreeWidgetItem([str(page_no), label, ""])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(2, Qt.CheckState.Checked)
                    item.setData(
                        0,
                        ROLE_META,
                        {
                            "type": "page",
                            "part_id": part_id,
                            "roman": roman,
                            "month": m,
                            "category": cat,
                            "year": year,
                        },
                    )
                    self._tree.addTopLevelItem(item)
                    page_no += 1
            else:
                label = f"Partea {roman}. {title}"
                if cat_label:
                    label += f" — {cat_label}"
                label += f" — anul {year}"
                item = QTreeWidgetItem([str(page_no), label, ""])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(2, Qt.CheckState.Checked)
                item.setData(
                    0,
                    ROLE_META,
                    {
                        "type": "page",
                        "part_id": part_id,
                        "roman": roman,
                        "month": None,
                        "category": cat,
                        "year": year,
                    },
                )
                self._tree.addTopLevelItem(item)
                page_no += 1

        self._tree.blockSignals(False)
        self._update_summary()
        if self._tree.topLevelItemCount() > 0:
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._tree.blockSignals(True)
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).setCheckState(2, state)
        self._tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self) -> None:
        total = self._tree.topLevelItemCount()
        selected = sum(
            1
            for i in range(total)
            if self._tree.topLevelItem(i).checkState(2) == Qt.CheckState.Checked
        )
        self._summary.setText(
            f"Registru final {self._year.value()}: {selected} pagini selectate din {total} "
            f"(numerotate 1…{total}). Ordine: toate părțile (Adulți), apoi toate părțile (Copii)."
        )

    def _selected_pages(self) -> list[dict]:
        year = self._year.value()
        pages = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.checkState(2) != Qt.CheckState.Checked:
                continue
            meta = item.data(0, ROLE_META) or {}
            if meta.get("type") == "cover":
                cover = get_cover_page()
                if not cover.get("an"):
                    cover["an"] = str(year)
                cover["type"] = "cover"
                pages.append(cover)
            else:
                part_id = meta["part_id"]
                obj = self._get_page_obj(part_id)
                if obj is None:
                    continue
                pages.append(obj._build_page(year, meta.get("month"), meta.get("category")))
        return pages

    def _on_selection_changed(self) -> None:
        item = self._tree.currentItem()
        if not item:
            return
        try:
            meta = item.data(0, ROLE_META) or {}
            if meta.get("type") == "cover":
                cover = get_cover_page()
                if not cover.get("an"):
                    cover["an"] = str(self._year.value())
                html = (
                    "<div style='text-align:center;margin-top:80px'>"
                    f"<b>{cover.get('institutie_1','')}</b><br>"
                    f"<b>{cover.get('institutie_2','')}</b><br><br>"
                    f"<span style='font-size:22px'><b>{cover.get('titlu','')}</b></span><br>"
                    f"<b>{cover.get('biblioteca','')}</b><br>"
                    f"{cover.get('localitate','')}<br><br>"
                    f"<b>{cover.get('an','')}</b></div>"
                )
                self._preview.setHtml(html)
                return
            part_id = meta["part_id"]
            obj = self._get_page_obj(part_id)
            if obj is None:
                return
            page = obj._build_page(self._year.value(), meta.get("month"), meta.get("category"))
            from ui.export.export_html import _page_html

            pag = int(item.text(0))
            total = self._tree.topLevelItemCount()
            self._preview.setHtml(_page_html(page, pag, total))
        except Exception as exc:
            self._preview.setPlainText(f"Nu s-a putut previzualiza pagina:\n{exc}")

    def _open_page_for_edit(self, item: QTreeWidgetItem, _col: int) -> None:
        self._navigate_to_item(item)

    def _open_selected_for_edit(self) -> None:
        item = self._tree.currentItem()
        if item:
            self._navigate_to_item(item)

    def _navigate_to_item(self, item: QTreeWidgetItem) -> None:
        meta = item.data(0, ROLE_META) or {}
        if meta.get("type") == "cover":
            from ui.cover_page_dialog import CoverPageDialog

            CoverPageDialog(self.main_window).exec()
            self.refresh()
            return
        part_id = meta["part_id"]
        month = meta.get("month")
        cat = meta.get("category")
        self.main_window.navigate_to_part(part_id, month=month, category=cat)
        self.main_window.statusBar().showMessage(
            f"Editare: {item.text(1)} — modificați datele, apoi reveniți la Registru final.",
            8000,
        )

    def _preview_full(self) -> None:
        pages = self._selected_pages()
        if not pages:
            QMessageBox.information(self, "Registru final", "Nu ați selectat nicio pagină.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        from PyQt6.QtGui import QPageLayout, QPageSize

        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        doc = QTextDocument()
        doc.setHtml(build_pages_html(pages))
        dlg = QPrintPreviewDialog(printer, self)
        dlg.setWindowTitle(f"Registru final {self._year.value()} — {len(pages)} pagini")
        dlg.paintRequested.connect(doc.print)
        dlg.exec()

    def _export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        pages = self._selected_pages()
        if not pages:
            QMessageBox.information(self, "Registru final", "Nu ați selectat nicio pagină.")
            return
        fmt = self._fmt.currentData()
        ext = {"pdf": "pdf", "word": "docx", "excel": "xlsx"}[fmt]
        filt = {
            "pdf": "Fișier PDF (*.pdf)",
            "word": "Document Word (*.docx)",
            "excel": "Fișier Excel (*.xlsx)",
        }[fmt]
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvează registrul final",
            f"Registru_complet_{self._year.value()}.{ext}",
            filt,
        )
        if not out_path:
            return
        try:
            run_export_with_progress(
                self,
                fmt,
                out_path,
                pages,
                main_window=self.main_window,
                title="Export registru final",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Eroare export", format_export_error(exc))
            return
        QMessageBox.information(
            self,
            "Export reușit",
            f"Registrul final ({len(pages)} pagini numerotate) a fost salvat:\n{out_path}",
        )
