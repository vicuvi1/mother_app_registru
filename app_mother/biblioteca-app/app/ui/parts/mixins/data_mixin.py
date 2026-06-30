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


class PartDataMixin:
    def _query_rows(self, session, categorie: str | None):
        q = select(self.model_class)
        filters = []
        if self.mode != "crud":
            filters.append(self.model_class.an == self.year)
        if self.mode in ("daily", "events") and self.show_month:
            filters.append(self.model_class.luna == self.month)
        if self.mode == "monthly":
            pass  # all 12 months for year
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
        return list(session.scalars(q))
    def _ensure_monthly_rows(self, categorie: str | None):
        rows, ids, flags = [], [], []
        for luna in range(1, 13):
            row: dict[str, Any] = {"luna": luna, "data": LUNI_RO[luna - 1]}
            if categorie:
                row["categorie_varsta"] = categorie
            for col in self.columns:
                if col.key not in row and col.col_type == "int":
                    row[col.key] = 0
            rows.append(row)
            ids.append(None)
            flags.append(False)
        return rows, ids, flags
    def _ensure_daily_rows(self, categorie: str | None):
        days = self._working_days()
        rows, ids, flags = [], [], []
        for d in days:
            row: dict[str, Any] = {self.date_field: d}
            if categorie:
                row["categorie_varsta"] = categorie
            for col in self.columns:
                if col.key != self.date_field and col.col_type == "int":
                    row[col.key] = 0
                elif col.col_type in ("text", "responsabil"):
                    row[col.key] = ""
                elif col.col_type == "bool" or col.col_type.startswith("scope_"):
                    row[col.key] = False
            rows.append(row)
            ids.append(None)
            flags.append(False)
        return rows, ids, flags

    def _merge_daily_rows(
        self,
        rows_data: list[dict],
        row_ids: list[int | None],
        auto_flags: list[bool],
        categorie: str | None,
        year: int,
        month: int,
    ) -> tuple[list[dict], list[int | None], list[bool]]:
        """Completează zilele lucrătoare lipsă — același calendar în toate părțile zilnice."""
        saved_year, saved_month = self._loaded_year, self._loaded_month
        self._loaded_year, self._loaded_month = year, month
        try:
            scaffold, _, _ = self._ensure_daily_rows(categorie)
        finally:
            self._loaded_year, self._loaded_month = saved_year, saved_month

        by_date: dict[str, tuple[dict, int | None, bool]] = {}
        for i, row in enumerate(rows_data):
            d = row.get(self.date_field)
            if not d:
                continue
            by_date[d] = (
                row,
                row_ids[i] if i < len(row_ids) else None,
                auto_flags[i] if i < len(auto_flags) else False,
            )

        merged_rows: list[dict] = []
        merged_ids: list[int | None] = []
        merged_flags: list[bool] = []

        for sc in scaffold:
            d = sc[self.date_field]
            if d in by_date:
                db_row, rid, fl = by_date[d]
                merged = dict(sc)
                merged.update(db_row)
                merged[self.date_field] = d
                merged_rows.append(merged)
                merged_ids.append(rid)
                merged_flags.append(fl)
            else:
                merged_rows.append(dict(sc))
                merged_ids.append(None)
                merged_flags.append(False)

        return merged_rows, merged_ids, merged_flags

    def _record_to_dict(self, rec) -> dict:
        d = {}
        for col in self.columns:
            d[col.key] = getattr(rec, col.key, None)
        if self.mode in ("daily", "events") and hasattr(rec, self.date_field):
            if self.date_field not in d:
                d[self.date_field] = getattr(rec, self.date_field, None)
        if self.mode == "monthly" and hasattr(rec, "luna"):
            d["luna"] = rec.luna
            d["data"] = LUNI_RO[rec.luna - 1]
        return d
    def _update_totals(self, table: EditableTable, categorie: str | None, fast: bool = False) -> None:
        sums = table.compute_column_sums()
        table.add_total_row("Total", sums)
        if self.cumulative and self.mode in ("daily", "events"):
            cum = self._compute_cumulative_live(categorie, table)
            table.add_total_row("Total de la început", cum)
    def _compute_cumulative(self, categorie: str | None) -> dict[str, int]:
        key = self._cache_key(categorie=categorie)
        if key in self._cumulative_cache:
            return self._cumulative_cache[key]
        result: dict[str, int] = {
            c.key: 0
            for c in self.columns
            if c.col_type == "int" or c.counts_checked_in_total()
        }
        with get_session() as session:
            for m in range(1, self.month + 1):
                filters = [
                    self.model_class.an == self.year,
                    self.model_class.luna == m,
                ]
                if categorie and hasattr(self.model_class, "categorie_varsta"):
                    filters.append(self.model_class.categorie_varsta == categorie)
                rows = session.scalars(select(self.model_class).where(and_(*filters))).all()
                for rec in rows:
                    for col in self.columns:
                        if col.col_type == "int":
                            val = getattr(rec, col.key, 0) or 0
                            result[col.key] = result.get(col.key, 0) + val
                        elif col.counts_checked_in_total():
                            if getattr(rec, col.key, False):
                                result[col.key] = result.get(col.key, 0) + 1
        self._cumulative_cache[key] = result
        return result
    def _regenerate_days(self) -> None:
        if self.mode != "daily":
            return
        table = self._active_table()
        if table.rowCount() > 0:
            reply = QMessageBox.question(
                self,
                "Confirmare",
                "Există deja date pentru această lună. Regenerarea zilelor poate păstra "
                "valorile existente pentru zile comune. Continuați?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        days = self._working_days()
        categorie = self._active_category()

        with get_session() as session:
            for d in days:
                filters = [
                    self.model_class.an == self.year,
                    self.model_class.luna == self.month,
                    getattr(self.model_class, self.date_field) == d,
                ]
                if categorie:
                    filters.append(self.model_class.categorie_varsta == categorie)
                rec = session.scalar(select(self.model_class).where(and_(*filters)))
                if rec is None:
                    kwargs = {
                        "an": self.year,
                        "luna": self.month,
                        self.date_field: d,
                    }
                    if categorie:
                        kwargs["categorie_varsta"] = categorie
                    session.add(self.model_class(**kwargs))
            session.commit()
        self._invalidate_caches()
        self._load_current()
    def _generate_month(self) -> None:
        table = self._active_table()
        manual = sum(1 for f in table.get_auto_flags() if not f and table.rowCount() > 0)
        if manual > 0:
            reply = QMessageBox.question(
                self,
                "Atenție",
                f"{manual} rânduri au date introduse manual. Sigur doriți să le suprascrieți?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self.mode == "monthly":
            self._generate_yearly()
            return

        categorie = self._active_category()
        if self.mode == "daily":
            self._regenerate_days()

        generated = generate_month_data(self.part_id, self.year, self.month, categorie_varsta=categorie)

        with get_session() as session:
            if self.mode == "daily":
                if categorie:
                    session.execute(
                        delete(self.model_class).where(
                            and_(
                                self.model_class.an == self.year,
                                self.model_class.luna == self.month,
                                self.model_class.categorie_varsta == categorie,
                            )
                        )
                    )
                else:
                    session.execute(
                        delete(self.model_class).where(
                            and_(
                                self.model_class.an == self.year,
                                self.model_class.luna == self.month,
                            )
                        )
                    )
            elif self.mode == "events":
                flt = [self.model_class.an == self.year, self.model_class.luna == self.month]
                if categorie:
                    flt.append(self.model_class.categorie_varsta == categorie)
                session.execute(delete(self.model_class).where(and_(*flt)))

            for row in generated:
                kwargs = {"an": self.year, "luna": self.month, "is_auto_generated": True}
                if categorie:
                    kwargs["categorie_varsta"] = categorie
                for col in self.columns:
                    if col.key in row:
                        kwargs[col.key] = row[col.key]
                if self.date_field in row:
                    kwargs[self.date_field] = row[self.date_field]
                kwargs = {k: v for k, v in kwargs.items() if k in self._model_keys}
                session.add(self.model_class(**kwargs))
            session.commit()

        self._invalidate_caches()
        self._load_current()
        self._dirty = False
        self.main_window.set_save_status(True)
    def _generate_yearly(self) -> None:
        categorie = self._active_category()
        generated = generate_year_monthly_data(self.part_id, self.year, categorie_varsta=categorie)
        with get_session() as session:
            flt = [self.model_class.an == self.year]
            if categorie:
                flt.append(self.model_class.categorie_varsta == categorie)
            session.execute(delete(self.model_class).where(and_(*flt)))
            for row in generated:
                kwargs = {"an": self.year, "is_auto_generated": True}
                if categorie:
                    kwargs["categorie_varsta"] = categorie
                for col in self.columns:
                    if col.key in row:
                        kwargs[col.key] = row[col.key]
                kwargs["luna"] = row.get("luna", 1)
                kwargs = {k: v for k, v in kwargs.items() if k in self._model_keys}
                session.add(self.model_class(**kwargs))
            session.commit()
        self._invalidate_caches()
        self._load_current()
    def _add_empty_row(self) -> None:
        table = self._active_table()
        row_data: dict[str, Any] = {}
        if self.mode == "events":
            date_visible = any(c.key == self.date_field for c in self.columns)
            if date_visible:
                days = self._working_days()
                row_data[self.date_field] = days[0] if days else "01.01"
            else:
                n = len(table.get_data_rows())
                row_data[self.date_field] = f"_r{n + 1}"
        for col in self.columns:
            if col.col_type == "int":
                row_data[col.key] = 0
            elif col.col_type == "bool" or col.col_type.startswith("scope_"):
                row_data[col.key] = False
            else:
                row_data[col.key] = ""
        table.append_row(row_data, None, False)
        self._dirty = True
        self._recompute_visible_totals()
        categorie = self._active_category()
        snap = self._snapshot_table(table)
        self._data_cache[self._cache_key(categorie=categorie)] = snap
        self._refresh_table_chrome(table, snap, update_stack=True)
        self._debounce.start()
    def _duplicate_selected_row(self) -> None:
        table = self._active_table()
        row = table.currentRow()
        if row < 0 or not table.is_data_row(row):
            QMessageBox.information(
                self,
                "Duplică rând",
                "Selectați un rând din tabel (click pe el), apoi apăsați din nou.",
            )
            return
        data_idx = table.visual_row_to_data_index(row)
        if data_idx is None:
            return
        rows = table.get_data_rows()
        if data_idx >= len(rows):
            return
        copy = dict(rows[data_idx])
        if (
            self.mode == "events"
            and self.date_field in self._model_keys
            and not any(c.key == self.date_field for c in self.columns)
        ):
            copy[self.date_field] = f"_r{len(rows) + 1}"
        table.insert_row_after(row, copy, None, False)
        self._dirty = True
        self._recompute_visible_totals()
        self._debounce.start()
        self.main_window.statusBar().showMessage("Rând duplicat — modificați ce trebuie și salvați.", 4000)

    def _duplicate_from_previous_month(self) -> None:
        if not self._has_month_bar or self.month <= 1:
            QMessageBox.information(
                self,
                "Copiază luna trecută",
                "Disponibil doar de la februarie înainte (luna 2–12).",
            )
            return
        prev = self.month - 1
        reply = QMessageBox.question(
            self,
            "Copiază luna trecută",
            f"Copiați datele din {LUNI_RO[prev - 1]} în {LUNI_RO[self.month - 1]}?\n\n"
            "Valorile curente din luna afișată vor fi înlocuite (nu se salvează automat).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._cache_current_period()
        categories = ["adulti", "copii"] if self.has_copii_adulti else [None]
        for cat in categories:
            source = self._fetch_table_data(cat, self.year, prev)
            new_rows = [dict(r) for r in source["rows"]]
            if self.mode == "daily":
                days = self._working_days(self.year, self.month)
                for i, row in enumerate(new_rows):
                    if i < len(days):
                        row[self.date_field] = days[i]
            ids = [None] * len(new_rows)
            flags = [False] * len(new_rows)
            key = self._cache_key(self.year, self.month, cat)
            self._data_cache[key] = {
                "rows": new_rows,
                "ids": ids,
                "flags": flags,
                "db_empty": not any(ids),
            }

        self._dirty = True
        self.main_window.set_save_status(False)
        self._load_current(fast=True)
        self.main_window.statusBar().showMessage(
            f"Date copiate din {LUNI_RO[prev - 1]} — apăsați Salvează pentru a confirma.",
            6000,
        )

    def save_all(self, show_status: bool = True, reload: bool = False) -> bool:
        self._debounce.stop()
        if self._save_pending:
            self._dirty = True
        if not self._dirty:
            if show_status:
                self.main_window.set_save_status(True)
            return True
        if show_status:
            self.main_window.set_save_status(False)

        try:
            if self.has_copii_adulti:
                self._save_table(self.table_copii, "copii", reload=reload)
                self._save_table(self.table_adulti, "adulti", reload=reload)
            else:
                self._save_table(self.table, None, reload=reload)
        except Exception as exc:
            logger.exception(
                "Eroare salvare Partea %s (%s), %d rânduri",
                self.roman,
                self.part_id,
                len(self.table.get_data_rows()) if hasattr(self, "table") else 0,
            )
            QMessageBox.warning(self, "Eroare salvare", f"Nu s-au putut salva datele:\n{exc}")
            if hasattr(self.main_window, "show_save_error"):
                self.main_window.show_save_error(
                    f"Partea {self.roman} — salvare eșuată. Verificați spațiul pe disc și încercați din nou."
                )
            return False

        if hasattr(self.main_window, "clear_save_error"):
            self.main_window.clear_save_error()

        if show_status:
            self.main_window.set_save_status(True)
        self._dirty = False
        self._save_pending = False
        self._cumulative_cache.clear()
        self._cache_current_period()
        self.main_window.notify_saved()
        return True
    def _save_rows_data(
        self,
        rows: list[dict],
        ids: list[int | None],
        flags: list[bool],
        categorie: str | None,
        year: int,
        month: int,
    ) -> None:
        with get_session() as session:
            try:
                for i, row in enumerate(rows):
                    row_id = ids[i] if i < len(ids) else None
                    row_copy = dict(row)
                    if self.mode == "monthly" and "luna" not in row_copy:
                        row_copy["luna"] = i + 1
                    if (
                        self.mode == "events"
                        and self.date_field in self._model_keys
                        and not any(c.key == self.date_field for c in self.columns)
                        and not row_copy.get(self.date_field)
                    ):
                        row_copy[self.date_field] = f"_r{i + 1}"
                    kwargs = self._row_to_kwargs(
                        row_copy, categorie, for_update=False, row_index=i, year=year, month=month
                    )
                    if "is_auto_generated" in self._model_keys:
                        kwargs["is_auto_generated"] = flags[i] if i < len(flags) else False

                    if row_id is None:
                        row_id = self._find_existing_id(
                            session, row_copy, categorie, year=year, month=month
                        )

                    if row_id:
                        rec = session.get(self.model_class, row_id)
                        if rec:
                            update_kw = self._row_to_kwargs(
                                row_copy, categorie, for_update=True, year=year, month=month
                            )
                            if "is_auto_generated" in self._model_keys:
                                update_kw["is_auto_generated"] = kwargs.get("is_auto_generated", False)
                            if (
                                self.mode == "events"
                                and self.date_field in self._model_keys
                                and not getattr(rec, self.date_field, None)
                            ):
                                update_kw[self.date_field] = row_copy.get(self.date_field) or f"_r{i + 1}"
                            for k, v in update_kw.items():
                                setattr(rec, k, v)
                    else:
                        session.add(self.model_class(**kwargs))
                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "Tranzacție eșuată la salvare Partea %s (%s), %d rânduri",
                    self.roman,
                    self.part_id,
                    len(rows),
                )
                raise
    def _save_table(
        self, table: EditableTable, categorie: str | None, reload: bool = False
    ) -> None:
        model = getattr(table, "model", lambda: None)()
        if model is not None and hasattr(model, "store"):
            model.store.apply_computed_all()

        rows = table.get_data_rows()
        ids = table.get_row_ids()
        flags = table.get_auto_flags()

        for i, row in enumerate(rows):
            if (
                self.mode == "events"
                and self.date_field in self._model_keys
                and not any(c.key == self.date_field for c in self.columns)
                and not row.get(self.date_field)
            ):
                extra = f"_r{i + 1}"
                table.set_row_extra(i, self.date_field, extra)

        self._save_rows_data(rows, ids, flags, categorie, self.year, self.month)

        if reload:
            key = self._cache_key(categorie=categorie)
            self._data_cache.pop(key, None)
            self._load_table(table, categorie)
        else:
            self._sync_ids_after_save(table, categorie)
    def _find_existing_id(
        self,
        session,
        row: dict,
        categorie: str | None,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> int | None:
        """Găsește înregistrarea existentă pentru upsert (evită duplicate)."""
        y = year if year is not None else self.year
        m = month if month is not None else self.month
        filters = []
        if self.mode != "crud":
            filters.append(self.model_class.an == y)
        if self.mode in ("daily", "events") and self.show_month:
            filters.append(self.model_class.luna == m)
        if self.mode == "monthly":
            luna = row.get("luna")
            if luna:
                filters.append(self.model_class.luna == int(luna))
        if categorie and hasattr(self.model_class, "categorie_varsta"):
            filters.append(self.model_class.categorie_varsta == categorie)

        date_val = row.get(self.date_field) or row.get("data")
        if date_val and hasattr(self.model_class, self.date_field):
            filters.append(getattr(self.model_class, self.date_field) == date_val)

        if not filters:
            return None

        rec = session.scalar(select(self.model_class).where(and_(*filters)))
        return rec.id if rec else None
    def _sync_ids_after_save(self, table: EditableTable, categorie: str | None) -> None:
        with get_session() as session:
            rows_db = self._query_rows(session, categorie)

        if self.mode == "daily" or (self.mode == "events" and self.date_field):
            id_map = {
                getattr(r, self.date_field): r.id
                for r in rows_db
                if getattr(r, self.date_field, None)
            }
            new_ids = []
            for row in table.get_data_rows():
                key = row.get(self.date_field) or row.get("data")
                new_ids.append(id_map.get(key))
            table.set_row_ids(new_ids)
        elif self.mode == "monthly":
            id_map = {r.luna: r.id for r in rows_db}
            new_ids = []
            for i, row in enumerate(table.get_data_rows()):
                luna = row.get("luna", i + 1)
                new_ids.append(id_map.get(int(luna)))
            table.set_row_ids(new_ids)
        else:
            new_ids = [r.id for r in rows_db]
            table.set_row_ids(new_ids)

        table.update_totals_only("Total", table.compute_column_sums())
        if self.cumulative and self.mode in ("daily", "events"):
            table.update_totals_only(
                "Total de la început",
                self._compute_cumulative_live(categorie, table),
            )
    def _row_to_kwargs(
        self,
        row: dict,
        categorie: str | None,
        for_update: bool = False,
        row_index: int = 0,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {}
        y = year if year is not None else self.year
        m = month if month is not None else self.month
        if self.mode != "crud":
            kwargs["an"] = y
        if self.mode in ("daily", "events") and self.show_month:
            kwargs["luna"] = m
        if self.mode == "monthly":
            luna = row.get("luna")
            if luna:
                kwargs["luna"] = int(luna)
        if categorie:
            kwargs["categorie_varsta"] = categorie
        for col in self.columns:
            if col.key in row:
                kwargs[col.key] = row[col.key]
        kwargs = {k: v for k, v in kwargs.items() if k in self._model_keys}
        if not for_update and self.mode == "events" and self.date_field in self._model_keys:
            if not kwargs.get(self.date_field) and not row.get(self.date_field):
                kwargs[self.date_field] = f"_r{row_index + 1}"
            elif self.date_field in row and row[self.date_field]:
                kwargs[self.date_field] = row[self.date_field]
        if for_update:
            for key in (self.date_field, "data", "an", "luna", "categorie_varsta"):
                kwargs.pop(key, None)
        return kwargs
    def _open_text_presets(self) -> None:
        from ui.widgets.text_presets_dialog import TextPresetsDialog

        dlg = TextPresetsDialog(self.part_id, self.columns, self)
        if dlg.exec():
            for tbl in (self.table, getattr(self, "table_copii", None), getattr(self, "table_adulti", None)):
                if tbl is not None:
                    tbl.refresh_preset_dropdowns()
            self.main_window.statusBar().showMessage("Liste text salvate", 3000)
    def _open_ranges(self) -> None:
        cols = self._all_range_columns()
        if not cols:
            QMessageBox.information(self, "Range-uri", "Nu există coloane numerice configurabile.")
            return
        dlg = RangeConfigDialog(self.part_id, cols, self)
        if dlg.exec():
            self.main_window.statusBar().showMessage(
                f"Range-uri salvate pentru {len(cols)} coloane", 4000
            )

    # ----- Construire pagini pentru export / print -----
