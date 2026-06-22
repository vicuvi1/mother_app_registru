"""Clasă de bază pentru toate paginile de Parte."""

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
from ui.widgets.table_scroll_wrapper import TableScrollWrapper

logger = logging.getLogger(__name__)


class PartPageBase(QWidget):
    """
    Pagină reutilizabilă pentru o Parte din registru.
    mode: daily | monthly | events | crud
    """

    def __init__(
        self,
        roman: str,
        part_id: str,
        title: str,
        model_class: type,
        columns: list[ColumnDef],
        main_window,
        mode: str = "daily",
        has_copii_adulti: bool = False,
        show_month: bool = True,
        cumulative: bool | None = None,
        computed_rules: dict[str, list[str]] | None = None,
        numeric_columns: list[str] | None = None,
        date_field: str = "data",
        extra_filter: Callable[[dict], dict] | None = None,
    ) -> None:
        super().__init__()
        self.roman = roman
        self.part_id = part_id
        self.title = title
        self.model_class = model_class
        self.columns = columns
        self.main_window = main_window
        self.mode = mode
        self.has_copii_adulti = has_copii_adulti
        self.show_month = show_month
        self.cumulative = cumulative if cumulative is not None else mode in ("daily", "events")
        self.computed_rules = computed_rules or {}
        self.numeric_columns = numeric_columns or self._all_range_columns()
        self.date_field = date_field
        self.extra_filter = extra_filter
        self._model_keys = set(sa_inspect(model_class).columns.keys())

        from datetime import date

        self._has_month_bar = self.show_month and self.mode in ("daily", "events")
        today = date.today()
        self._loaded_year = today.year
        self._loaded_month = today.month
        self._building = True
        # Cache în memorie: (an, lună, categorie) → snapshot tabel (evită DB la revenire)
        self._data_cache: dict[tuple, dict] = {}
        self._cumulative_cache: dict[tuple, dict] = {}
        self._save_pending = False

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(1500)
        self._debounce.timeout.connect(lambda: self.save_all(show_status=True))

        self._dirty = False
        self._build_ui()
        if self.mode == "events":
            QShortcut(QKeySequence("Ctrl+D"), self, self._duplicate_selected_row)
        if self._has_month_bar:
            QShortcut(QKeySequence("Ctrl+Left"), self, lambda: self._go_month(-1))
            QShortcut(QKeySequence("Ctrl+Right"), self, lambda: self._go_month(1))
        QTimer.singleShot(0, self._load_current)

    def _working_days(self, year: int | None = None, month: int | None = None) -> list[str]:
        y, m = year or self.year, month or self.month
        return get_working_days(y, m, get_excluded_days(y, m))

    def _all_range_columns(self) -> list[str]:
        """Toate coloanele numerice editabile (pentru range-uri individuale)."""
        return [
            c.key
            for c in self.columns
            if c.col_type == "int" and not c.computed_from and c.editable
        ]

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)
        outer.setObjectName("pageContainer")

        # --- Header card ---
        header_card = QFrame()
        header_card.setObjectName("pageHeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)

        badge = QLabel(self.roman)
        badge.setObjectName("partRomanBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        registru = QLabel("Registru de evidență a activității bibliotecii")
        registru.setObjectName("pageRegistru")
        self._heading_label = QLabel()
        self._heading_label.setObjectName("pageHeading")
        self._heading_label.setWordWrap(True)
        title_col.addWidget(registru)
        title_col.addWidget(self._heading_label)
        header_layout.addLayout(title_col, stretch=1)
        outer.addWidget(header_card)

        # --- Toolbar card ---
        tool_card = QFrame()
        tool_card.setObjectName("toolBarCard")
        toolbar = QHBoxLayout(tool_card)
        toolbar.setContentsMargins(12, 10, 12, 10)
        toolbar.setSpacing(8)

        if self.mode != "crud":
            self.date_picker = DatePickerZileLucratoare(show_month=False)
            self._loaded_year = self.date_picker.year
            self.date_picker.year_combo.currentIndexChanged.connect(self._on_year_changed)
            toolbar.addWidget(self.date_picker)
        else:
            self.date_picker = None

        toolbar.addStretch()

        if self.mode == "daily":
            btn_days = QPushButton("📅 Regenerează zilele")
            btn_days.setObjectName("btnGhost")
            btn_days.clicked.connect(self._regenerate_days)
            toolbar.addWidget(btn_days)

        btn_gen = QPushButton("Generează automat")
        btn_gen.setObjectName("btnPrimary")
        btn_gen.clicked.connect(self._generate_month)
        toolbar.addWidget(btn_gen)

        btn_range = QPushButton("Range-uri")
        btn_range.clicked.connect(self._open_ranges)
        toolbar.addWidget(btn_range)

        if any(c.col_type == "preset_text" for c in self.columns):
            btn_lists = QPushButton("Liste text")
            btn_lists.setToolTip("Configurați listele de valori — select rapid în celule")
            btn_lists.clicked.connect(self._open_text_presets)
            toolbar.addWidget(btn_lists)

        btn_save = QPushButton("Salvează")
        btn_save.setObjectName("btnSuccess")
        btn_save.clicked.connect(lambda: self.save_all(show_status=True, reload=True))
        toolbar.addWidget(btn_save)

        btn_print = QPushButton("Printează")
        btn_print.clicked.connect(self._print_table)
        toolbar.addWidget(btn_print)

        btn_export = QPushButton("Exportă")
        btn_export.clicked.connect(self._export)
        toolbar.addWidget(btn_export)

        outer.addWidget(tool_card)

        if self.mode in ("events", "crud"):
            row_btns = QHBoxLayout()
            row_btns.setContentsMargins(0, 0, 0, 0)
            row_btns.setSpacing(8)
            btn_add = QPushButton("+ Adaugă rând")
            btn_add.setObjectName("btnAddRow")
            btn_add.clicked.connect(self._add_empty_row)
            row_btns.addWidget(btn_add)
            if self.mode == "events":
                btn_dup = QPushButton("⧉ Duplică rând")
                btn_dup.setObjectName("btnGhost")
                btn_dup.setToolTip("Copiază rândul selectat (Ctrl+D)")
                btn_dup.clicked.connect(self._duplicate_selected_row)
                row_btns.addWidget(btn_dup)
            row_btns.addStretch()
            row_bar = QWidget()
            row_bar.setLayout(row_btns)
            outer.addWidget(row_bar)

        # --- Bara de luni (navigare ca foile Excel) ---
        self._month_bar = None
        if self._has_month_bar:
            self._month_bar = QTabBar()
            self._month_bar.setObjectName("monthBar")
            self._month_bar.setExpanding(False)
            self._month_bar.setDrawBase(False)
            for name in LUNI_RO:
                self._month_bar.addTab(name)
            self._month_bar.setCurrentIndex(self._loaded_month - 1)
            self._month_bar.currentChanged.connect(self._on_month_tab_changed)
            outer.addWidget(self._month_bar)

        # --- Table card ---
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        hint = QLabel(
            "Click pe celulă + tastați  ·  Tab / Enter = următoarea celulă  ·  "
            "Dublu-click pe antet = redenumire  ·  Albastru = generat automat"
        )
        table_layout.addWidget(hint)

        if self.has_copii_adulti:
            self.tabs = QTabWidget()
            self.table_adulti = self._make_table()
            self.table_copii = self._make_table()
            self.tabs.addTab(self._scroll_for(self.table_adulti), "Adulți")
            self.tabs.addTab(self._scroll_for(self.table_copii), "Copii până la 16 ani")
            self.tabs.currentChanged.connect(self._on_tab_changed)
            table_layout.addWidget(self.tabs)
            self.table = self.table_adulti
        else:
            self.tabs = None
            self.table = self._make_table()
            table_layout.addWidget(self._scroll_for(self.table))

        outer.addWidget(table_card, stretch=1)
        self._building = False
        self._update_heading()

    def _scroll_for(self, table: EditableTable) -> TableScrollWrapper:
        return TableScrollWrapper(table)

    def _make_table(self) -> EditableTable:
        table = EditableTable()
        table.setup(self.columns, self.computed_rules, part_id=self.part_id)
        labels = [get_all_etichete(self.part_id).get(c.key, c.key) for c in self.columns]
        table.set_header_labels(labels)
        table.cell_edited.connect(self._on_cell_edited)
        table.validation_error.connect(self._show_validation_hint)
        table.header_label_changed.connect(self._on_header_label_changed)
        table.setMinimumHeight(320)
        table.setMinimumWidth(max(900, len(self.columns) * 90))
        return table

    def _heading_text(self) -> str:
        if self.mode == "crud":
            return f"Partea {self.roman}. {self.title}"
        if self.mode == "monthly" or not self.show_month:
            return f"Partea {self.roman}. {self.title} — anul {self.year}"
        luna_name = LUNI_RO[self.month - 1]
        return f"Partea {self.roman}. {self.title} în luna {luna_name} anul {self.year}"

    def _update_heading(self) -> None:
        if hasattr(self, "_heading_label"):
            self._heading_label.setText(self._heading_text())

    def apply_session_state(self, year: int | None, month: int | None) -> None:
        """Restaurează anul/luna salvate la pornire."""
        if year and self.date_picker:
            self.date_picker.set_year(year)
            self._loaded_year = year
        if month and self._has_month_bar and self._month_bar:
            month = max(1, min(12, month))
            self._loaded_month = month
            self._month_bar.blockSignals(True)
            self._month_bar.setCurrentIndex(month - 1)
            self._month_bar.blockSignals(False)
        self._update_heading()

    def has_unsaved_changes(self) -> bool:
        return bool(self._dirty or self._debounce.isActive() or self._save_pending)

    def _go_month(self, delta: int) -> None:
        if not self._has_month_bar or not self._month_bar:
            return
        new_index = self._month_bar.currentIndex() + delta
        if 0 <= new_index < self._month_bar.count():
            self._month_bar.setCurrentIndex(new_index)

    def _notify_session_changed(self) -> None:
        if hasattr(self.main_window, "persist_session_from_page"):
            self.main_window.persist_session_from_page(self)

    def navigate_to(self, month: int | None = None, category: str | None = None) -> None:
        """Sari la o lună/categorie (apelat din Registru final)."""
        self._cache_current_period()
        self._save_if_dirty()
        if month and self._has_month_bar:
            self._loaded_month = month
            if self._month_bar:
                self._month_bar.blockSignals(True)
                self._month_bar.setCurrentIndex(month - 1)
                self._month_bar.blockSignals(False)
        if category and self.tabs:
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(0 if category == "adulti" else 1)
            self.tabs.blockSignals(False)
        self._update_heading()
        self._load_current(fast=True)

    def _on_header_label_changed(self, col_key: str, new_label: str) -> None:
        set_eticheta_custom(self.part_id, col_key, new_label)
        self.main_window.statusBar().showMessage(f"Coloană redenumită: {new_label}", 3000)

    def _active_table(self) -> EditableTable:
        if self.tabs is not None:
            return self.table_adulti if self.tabs.currentIndex() == 0 else self.table_copii
        return self.table

    def _active_category(self) -> str | None:
        if not self.has_copii_adulti:
            return None
        return "adulti" if self.tabs.currentIndex() == 0 else "copii"

    @property
    def year(self) -> int:
        return self._loaded_year

    @property
    def month(self) -> int:
        if self._has_month_bar:
            return self._loaded_month
        return 1

    def _cache_key(self, year: int | None = None, month: int | None = None, categorie: str | None = None) -> tuple:
        return (year or self._loaded_year, month or self._loaded_month, categorie)

    def _snapshot_table(self, table: EditableTable) -> dict:
        return {
            "rows": table.get_data_rows(),
            "ids": table.get_row_ids(),
            "flags": table.get_auto_flags(),
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

    def _on_year_changed(self) -> None:
        if self._building:
            return
        self._cache_current_period()
        self._save_if_dirty()
        if self.date_picker:
            self._loaded_year = self.date_picker.year
        self._invalidate_caches()
        self._update_heading()
        self._load_current()
        self._notify_session_changed()

    def _on_month_tab_changed(self, index: int) -> None:
        if self._building:
            return
        old_year, old_month = self._loaded_year, self._loaded_month
        self._cache_current_period()
        pending_save = self._dirty
        if pending_save:
            self._dirty = False
        self._loaded_month = index + 1
        self._update_heading()
        self._load_current(fast=True)
        if pending_save:
            self.main_window.set_save_status(False)
            QTimer.singleShot(0, lambda: self._deferred_persist(old_year, old_month))
        self._notify_session_changed()

    def flush_pending_save(self) -> bool:
        """Salvare sincronă la ieșire — pentru date în așteptare."""
        self._debounce.stop()
        if self._save_pending:
            self._dirty = True
        if self._dirty:
            return self.save_all(show_status=False)
        return True

    def _on_tab_changed(self) -> None:
        if self._building:
            return
        self._save_if_dirty()
        self._load_table(self._active_table(), self._active_category(), fast=True)

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        self._dirty = True
        self.main_window.set_save_status(False)
        self._recompute_visible_totals()
        self._debounce.start()

    def _recompute_visible_totals(self) -> None:
        """Recalcul live al rândurilor Total (ca în Excel) la fiecare editare."""
        table = self._active_table()
        categorie = self._active_category()
        table.update_totals_only("Total", table.compute_column_sums())
        if self.cumulative and self.mode in ("daily", "events"):
            table.update_totals_only(
                "Total de la început", self._compute_cumulative_live(categorie, table)
            )

    def _prior_months_cache_key(self, categorie: str | None, month: int | None = None) -> tuple:
        return (self.year, month or self.month, categorie, "prior")

    def _numeric_total_keys(self) -> dict[str, int]:
        return {
            c.key: 0
            for c in self.columns
            if c.col_type == "int" or (c.col_type == "bool" and c.count_in_total)
        }

    def _accumulate_record(self, result: dict[str, int], rec) -> None:
        for col in self.columns:
            if col.col_type == "int":
                result[col.key] += getattr(rec, col.key, 0) or 0
            elif col.col_type == "bool" and col.count_in_total:
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
            elif col.col_type == "bool" and col.count_in_total:
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

    def _show_validation_hint(self, msg: str) -> None:
        self.main_window.statusBar().showMessage(msg, 3000)

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

        if self.mode == "monthly" and not rows_data:
            rows_data, row_ids, auto_flags = self._ensure_monthly_rows(categorie)
        elif self.mode == "daily" and not rows_data:
            saved_year, saved_month = self._loaded_year, self._loaded_month
            self._loaded_year, self._loaded_month = y, m
            try:
                rows_data, row_ids, auto_flags = self._ensure_daily_rows(categorie)
            finally:
                self._loaded_year, self._loaded_month = saved_year, saved_month

        return {"rows": rows_data, "ids": row_ids, "flags": auto_flags}

    def _load_table(self, table: EditableTable, categorie: str | None, fast: bool = False) -> None:
        key = self._cache_key(categorie=categorie)
        if key in self._data_cache:
            cached = self._data_cache[key]
            table.load_rows(
                cached["rows"],
                cached["ids"],
                cached["flags"],
                resize=not fast,
                resize_rows=not fast,
            )
            self._update_totals(table, categorie, fast=fast)
            return

        cached = self._fetch_table_data(categorie)
        table.load_rows(
            cached["rows"],
            cached["ids"],
            cached["flags"],
            resize=not fast,
            resize_rows=not fast,
        )
        self._update_totals(table, categorie, fast=fast)
        self._data_cache[key] = cached

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
            if c.col_type == "int" or (c.col_type == "bool" and c.count_in_total)
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
                        elif col.col_type == "bool" and col.count_in_total:
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
        existing = {self._active_table().item(r, 0).text(): r for r in range(self._active_table().rowCount()) if self._active_table().item(r, 0)}

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
            self, "Salvează exportul", self._suggested_filename(ext, scope, year), filt
        )
        if not out_path:
            return

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
        from PyQt6.QtGui import QTextDocument

        from ui.export.export_html import build_pages_html

        self.save_all(show_status=False)
        pages = [self._build_page(self.year, self.month, self._active_category())]

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        self._print_document = QTextDocument()
        self._print_document.setHtml(build_pages_html(pages))

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Previzualizare printare")
        preview.paintRequested.connect(lambda p: self._print_document.print(p))
        preview.exec()
