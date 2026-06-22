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


class PartCacheMixin:
    def _cache_key(self, year: int | None = None, month: int | None = None, categorie: str | None = None) -> tuple:
        return (year or self._loaded_year, month or self._loaded_month, categorie)
    def _snapshot_table(self, table: EditableTable) -> dict:
        ids = table.get_row_ids()
        return {
            "rows": table.get_data_rows(),
            "ids": ids,
            "flags": table.get_auto_flags(),
            "db_empty": self.mode == "daily" and bool(ids) and all(i is None for i in ids),
        }
    def _cache_current_period(self) -> None:
        """Memorează starea tabelelor pentru perioada curentă (înainte de navigare)."""
        y, m = self._loaded_year, self._loaded_month
        if self.has_copii_adulti:
            self._data_cache[self._cache_key(y, m, "copii")] = self._snapshot_table(self.table_copii)
            self._data_cache[self._cache_key(y, m, "adulti")] = self._snapshot_table(self.table_adulti)
        else:
            self._data_cache[self._cache_key(y, m, None)] = self._snapshot_table(self.table)
    def _save_if_dirty(self) -> None:
        if self._dirty:
            self.save_all(show_status=False)
    def _invalidate_caches(self) -> None:
        self._data_cache.clear()
        self._cumulative_cache.clear()
    def _prior_months_cache_key(self, categorie: str | None, month: int | None = None) -> tuple:
        return (self.year, month or self.month, categorie, "prior")
    def _numeric_total_keys(self) -> dict[str, int]:
        return {
            c.key: 0
            for c in self.columns
            if c.col_type == "int" or c.counts_checked_in_total()
        }
    def _accumulate_record(self, result: dict[str, int], rec) -> None:
        for col in self.columns:
            if col.col_type == "int":
                result[col.key] += getattr(rec, col.key, 0) or 0
            elif col.counts_checked_in_total():
                if getattr(rec, col.key, False):
                    result[col.key] += 1
    def _get_prior_months_totals(self, categorie: str | None, month: int | None = None) -> dict[str, int]:
        """Sume lunile 1..(luna-1) — agregare SQL, cu cache."""
        m = month or self.month
        if m <= 1:
            return self._numeric_total_keys()

        key = self._prior_months_cache_key(categorie, m)
        if key in self._cumulative_cache:
            return dict(self._cumulative_cache[key])

        result = self._numeric_total_keys()
        sum_exprs = []
        labels: list[str] = []
        for col in self.columns:
            if col.col_type == "int":
                sum_exprs.append(
                    func.coalesce(func.sum(getattr(self.model_class, col.key)), 0).label(col.key)
                )
                labels.append(col.key)
            elif col.counts_checked_in_total():
                sum_exprs.append(
                    func.coalesce(
                        func.sum(
                            case(
                                (getattr(self.model_class, col.key).is_(True), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ).label(col.key)
                )
                labels.append(col.key)
        if not sum_exprs:
            return result

        with get_session() as session:
            filters = [
                self.model_class.an == self.year,
                self.model_class.luna < m,
            ]
            if categorie and hasattr(self.model_class, "categorie_varsta"):
                filters.append(self.model_class.categorie_varsta == categorie)
            row = session.execute(select(*sum_exprs).where(and_(*filters))).one()
            for label in labels:
                result[label] = int(row._mapping[label] or 0)

        self._cumulative_cache[key] = dict(result)
        return result
    def _compute_cumulative_live(self, categorie: str | None, table: EditableTable) -> dict[str, int]:
        """Cumulativ = lunile anterioare (cache/DB) + luna curentă (din tabel, live)."""
        result = self._get_prior_months_totals(categorie)
        current = table.compute_column_sums()
        for k, v in current.items():
            result[k] = result.get(k, 0) + v
        return result
    def _load_current(self, fast: bool = False) -> None:
        if fast and self.has_copii_adulti:
            self._load_table(self._active_table(), self._active_category(), fast=True)
            self._schedule_preload_adjacent()
            return
        if self.has_copii_adulti:
            self._load_table(self.table_copii, "copii", fast=fast)
            self._load_table(self.table_adulti, "adulti", fast=fast)
        else:
            self._load_table(self.table, None, fast=fast)
        self._schedule_preload_adjacent()
    def _fetch_table_data(
        self, categorie: str | None, year: int | None = None, month: int | None = None
    ) -> dict:
        """Citește datele unei luni din DB (fără actualizare UI)."""
        y = year or self.year
        m = month or self.month
        with get_session() as session:
            q = select(self.model_class)
            filters = []
            if self.mode != "crud":
                filters.append(self.model_class.an == y)
            if self.mode in ("daily", "events") and self.show_month and m:
                filters.append(self.model_class.luna == m)
            if categorie and hasattr(self.model_class, "categorie_varsta"):
                filters.append(self.model_class.categorie_varsta == categorie)
            if filters:
                q = q.where(and_(*filters))
            order_col = getattr(self.model_class, self.date_field, None)
            if order_col is not None and self.mode == "monthly":
                q = q.order_by(self.model_class.luna)
            elif order_col is not None:
                q = q.order_by(order_col)
            elif hasattr(self.model_class, "id"):
                q = q.order_by(self.model_class.id)
            rows_db = list(session.scalars(q))

        rows_data = []
        row_ids = []
        auto_flags = []
        for rec in rows_db:
            rows_data.append(self._record_to_dict(rec))
            row_ids.append(rec.id)
            auto_flags.append(getattr(rec, "is_auto_generated", False))

        db_empty = len(rows_db) == 0

        if self.mode == "monthly" and not rows_data:
            rows_data, row_ids, auto_flags = self._ensure_monthly_rows(categorie)
        elif self.mode == "daily" and not rows_data:
            saved_year, saved_month = self._loaded_year, self._loaded_month
            self._loaded_year, self._loaded_month = y, m
            try:
                rows_data, row_ids, auto_flags = self._ensure_daily_rows(categorie)
            finally:
                self._loaded_year, self._loaded_month = saved_year, saved_month

        return {"rows": rows_data, "ids": row_ids, "flags": auto_flags, "db_empty": db_empty}
    def _load_table(self, table: EditableTable, categorie: str | None, fast: bool = False) -> None:
        key = self._cache_key(categorie=categorie)
        if key in self._data_cache:
            cached = self._data_cache[key]
        else:
            cached = self._fetch_table_data(categorie)
            self._data_cache[key] = cached

        table.load_rows(
            cached["rows"],
            cached["ids"],
            cached["flags"],
            resize=not fast,
            resize_rows=not fast,
        )
        self._update_totals(table, categorie, fast=fast)
        is_active = table is self._active_table()
        self._refresh_table_chrome(table, cached, update_stack=is_active)
    def _schedule_preload_adjacent(self) -> None:
        if not self._has_month_bar:
            return
        QTimer.singleShot(80, self._preload_adjacent_months)
        QTimer.singleShot(2000, self._preload_all_months)
    def _deferred_persist(self, year: int, month: int) -> None:
        if self._save_pending:
            return
        self._save_pending = True
        try:
            self._persist_cached_period(year, month)
            self._cumulative_cache.clear()
            self.main_window.notify_saved()
        except Exception as exc:
            self._dirty = True
            self.main_window.set_save_status(False)
            logger.exception("Salvare amânată eșuată Partea %s", self.roman)
            QMessageBox.warning(self, "Eroare salvare", f"Nu s-au putut salva datele:\n{exc}")
        finally:
            self._save_pending = False
    def _persist_cached_period(self, year: int, month: int) -> None:
        categories: list[str | None] = (
            ["copii", "adulti"] if self.has_copii_adulti else [None]
        )
        for cat in categories:
            key = self._cache_key(year, month, cat)
            if key not in self._data_cache:
                continue
            cached = self._data_cache[key]
            self._save_rows_data(
                cached["rows"], cached["ids"], cached["flags"], cat, year, month
            )
    def _preload_all_months(self) -> None:
        if not self._has_month_bar:
            return
        year = self._loaded_year
        categories: list[str | None] = (
            ["copii", "adulti"] if self.has_copii_adulti else [None]
        )
        for month in range(1, 13):
            for cat in categories:
                key = self._cache_key(year, month, cat)
                if key not in self._data_cache:
                    self._data_cache[key] = self._fetch_table_data(cat, year, month)
        self._warm_cumulative_cache()
    def _warm_cumulative_cache(self) -> None:
        if not self.cumulative or self.mode not in ("daily", "events"):
            return
        categories: list[str | None] = (
            ["copii", "adulti"] if self.has_copii_adulti else [None]
        )
        for month in range(2, 13):
            for cat in categories:
                self._get_prior_months_totals(cat, month=month)
    def _preload_adjacent_months(self) -> None:
        """Încarcă în cache lunile vecine fără a bloca UI-ul."""
        if not self._has_month_bar:
            return
        year = self._loaded_year
        current = self._loaded_month
        categories: list[str | None] = (
            ["copii", "adulti"] if self.has_copii_adulti else [None]
        )
        for delta in (-1, 1):
            month = current + delta
            if month < 1 or month > 12:
                continue
            for cat in categories:
                key = self._cache_key(year, month, cat)
                if key in self._data_cache:
                    continue
                self._data_cache[key] = self._fetch_table_data(cat, year, month)
