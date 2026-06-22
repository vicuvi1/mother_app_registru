from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeySequence, QPageLayout, QPageSize, QShortcut
from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import and_, case, delete, func, inspect as sa_inspect, select

from core.constants_manager import get_excluded_days, LUNI_RO, get_all_etichete, set_eticheta_custom
from core.export_presets import set_export_folder, suggest_export_path
from core.date_engine import get_working_days
from core.random_engine import generate_month_data, generate_year_monthly_data
from database.db_manager import get_session
from ui.export.export_dialog import ExportDialog
from ui.export.export_errors import format_export_error, run_export_with_progress
from ui.widgets.date_picker_zile_lucratoare import DatePickerZileLucratoare
from ui.widgets.editable_table import ColumnDef, EditableTable
from ui.widgets.range_config_dialog import RangeConfigDialog
from ui.widgets.table_factory import create_register_table
from ui.widgets.table_scroll_wrapper import TableScrollWrapper

logger = logging.getLogger(__name__)


class PartExportMixin:
    def _query_rows_period(self, session, categorie, year, month):
        q = select(self.model_class)
        filters = []
        if self.mode != "crud":
            filters.append(self.model_class.an == year)
        if self.mode in ("daily", "events") and self.show_month and month:
            filters.append(self.model_class.luna == month)
        if categorie and hasattr(self.model_class, "categorie_varsta"):
            filters.append(self.model_class.categorie_varsta == categorie)
        if filters:
            q = q.where(and_(*filters))

        order_col = getattr(self.model_class, self.date_field, None)
        if self.mode == "monthly":
            q = q.order_by(self.model_class.luna)
        elif order_col is not None:
            q = q.order_by(order_col)
        elif hasattr(self.model_class, "id"):
            q = q.order_by(self.model_class.id)
        return list(session.scalars(q))
    def _skeleton_daily(self, year, month, categorie):
        rows = []
        for d in self._working_days(year, month):
            row: dict[str, Any] = {self.date_field: d}
            for col in self.columns:
                if col.key != self.date_field and col.col_type == "int":
                    row[col.key] = 0
            rows.append(row)
        return rows
    def _skeleton_monthly(self):
        rows = []
        for luna in range(1, 13):
            row: dict[str, Any] = {"luna": luna, "data": LUNI_RO[luna - 1]}
            for col in self.columns:
                if col.key not in row and col.col_type == "int":
                    row[col.key] = 0
            rows.append(row)
        return rows
    def _rows_for_page(self, year, month, categorie):
        with get_session() as session:
            recs = self._query_rows_period(session, categorie, year, month)
        rows = [self._record_to_dict(rec) for rec in recs]
        if not rows:
            if self.mode == "daily":
                rows = self._skeleton_daily(year, month, categorie)
            elif self.mode == "monthly":
                rows = self._skeleton_monthly()
        for row in rows:
            for col in self.columns:
                if col.col_type == "int" and row.get(col.key) is None:
                    row[col.key] = 0
        return rows
    def _sum_rows(self, rows) -> dict[str, int]:
        sums: dict[str, int] = {}
        for col in self.columns:
            if col.counts_checked_in_total():
                total = sum(1 for row in rows if row.get(col.key))
                sums[col.key] = total
                continue
            if col.col_type != "int" and not col.computed_from:
                continue
            total = 0
            for row in rows:
                v = row.get(col.key)
                if isinstance(v, int):
                    total += v
            sums[col.key] = total
        return sums
    def _compute_cumulative_period(self, categorie, year, month) -> dict[str, int]:
        result: dict[str, int] = {
            c.key: 0
            for c in self.columns
            if c.col_type == "int" or (c.col_type == "bool" and c.count_in_total)
        }
        with get_session() as session:
            for m in range(1, month + 1):
                filters = [self.model_class.an == year, self.model_class.luna == m]
                if categorie and hasattr(self.model_class, "categorie_varsta"):
                    filters.append(self.model_class.categorie_varsta == categorie)
                for rec in session.scalars(select(self.model_class).where(and_(*filters))).all():
                    for col in self.columns:
                        if col.col_type == "int":
                            result[col.key] += getattr(rec, col.key, 0) or 0
                        elif col.col_type == "bool" and col.count_in_total:
                            if getattr(rec, col.key, False):
                                result[col.key] += 1
        return result
    def _build_page(self, year, month, categorie) -> dict:
        from core.constants_manager import get_all_etichete, get_biblioteca_info

        labels = get_all_etichete(self.part_id)
        headers = [labels.get(c.key, c.key) for c in self.columns]
        groups = [c.group or "" for c in self.columns]
        col_keys = [c.key for c in self.columns]

        rows = self._rows_for_page(year, month, categorie)
        total_rows = [("Total", self._sum_rows(rows))]
        if self.cumulative and month and self.mode in ("daily", "events"):
            total_rows.append(
                ("Total de la început", self._compute_cumulative_period(categorie, year, month))
            )

        nume_bib, loc = get_biblioteca_info()
        luna_name = (
            LUNI_RO[month - 1]
            if (month and self.show_month and self.mode != "monthly")
            else ""
        )
        cat_suffix = f" ({'copii' if categorie == 'copii' else 'adulți'})" if categorie else ""
        meta = {
            "parte_roman": self.roman,
            "title": self.title + cat_suffix,
            "an": year,
            "luna": month or 0,
            "luna_name": luna_name,
            "nume_biblioteca": nume_bib,
            "localitate": loc,
        }
        return {
            "headers": headers,
            "groups": groups,
            "col_keys": col_keys,
            "rows": rows,
            "total_rows": total_rows,
            "meta": meta,
        }
    def _pages_for_part(self, page, year) -> list[dict]:
        cats = ["adulti", "copii"] if page.has_copii_adulti else [None]
        pages = []
        for cat in cats:
            if page.mode in ("daily", "events"):
                for m in range(1, 13):
                    pages.append(page._build_page(year, m, cat))
            else:
                pages.append(page._build_page(year, None, cat))
        return pages
    def _cover_page(self, year) -> dict:
        from core.constants_manager import get_cover_page

        data = get_cover_page()
        if not data.get("an"):
            data["an"] = str(year)
        data["type"] = "cover"
        return data
    def _collect_pages(self, scope, year, selected_keys=None) -> list[dict]:
        self.save_all(show_status=False)
        if scope == "month":
            return [self._build_page(self.year, self.month, self._active_category())]
        if scope == "year":
            return self._pages_for_part(self, year)
        # full register — toate părțile (adulți), apoi toate părțile (copii)
        from ui.export.register_pages import collect_full_register_pages_with_dialog

        return collect_full_register_pages_with_dialog(self, self.main_window, year)
    def _suggested_filename(self, ext: str, scope: str, year: int) -> str:
        if scope == "full":
            return f"Registru_complet_{year}.{ext}"
        if scope == "year":
            return f"Partea_{self.roman}_{self.title.replace(' ', '_')}_anul_{year}.{ext}"
        cat = self._active_category()
        stub = f"Partea_{self.roman}_{self.title.replace(' ', '_')}"
        if cat:
            stub += f"_{cat}"
        luna_name = LUNI_RO[self.month - 1] if (self.show_month and self.mode != "monthly") else ""
        if luna_name:
            stub += f"_{luna_name}"
        stub += f"_{self.year}.{ext}"
        return stub
    def _export(self) -> None:
        dlg = ExportDialog(self, default_year=self.year)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        fmt = dlg.selected_format()
        scope = dlg.selected_scope()
        year = dlg.selected_year()
        ext = {"excel": "xlsx", "word": "docx", "pdf": "pdf"}[fmt]
        filt = {
            "excel": "Fișier Excel (*.xlsx)",
            "word": "Document Word (*.docx)",
            "pdf": "Fișier PDF (*.pdf)",
        }[fmt]

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvează exportul",
            suggest_export_path(self._suggested_filename(ext, scope, year)),
            filt,
        )
        if not out_path:
            return

        set_export_folder(out_path)
        self.main_window.statusBar().showMessage("Se generează exportul…")
        try:
            pages = self._collect_pages(scope, year)
            if not pages:
                QMessageBox.information(self, "Export", "Nu există date de exportat.")
                return
            run_export_with_progress(
                self, fmt, out_path, pages, main_window=self.main_window
            )
        except InterruptedError:
            QMessageBox.information(self, "Export", "Exportul a fost anulat.")
            return
        except Exception as exc:
            QMessageBox.warning(self, "Eroare export", format_export_error(exc))
            return
        finally:
            self.main_window.statusBar().clearMessage()

        reply = QMessageBox.question(
            self,
            "Export reușit",
            f"Fișierul a fost salvat ({len(pages)} pagini):\n{out_path}\n\nDoriți să îl deschideți?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._open_file(out_path)
    def _open_file(self, path: str) -> None:
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:
            logger.exception("Nu s-a putut deschide fișierul: %s", path)
            QMessageBox.warning(
                self,
                "Deschidere fișier",
                f"Nu s-a putut deschide fișierul:\n{path}\n\n{exc}",
            )
    def _print_table(self) -> None:
        from ui.export.print_presets import show_print_preview

        self.save_all(show_status=False)
        pages = [self._build_page(self.year, self.month, self._active_category())]
        show_print_preview(self, pages, title="Previzualizare printare")
