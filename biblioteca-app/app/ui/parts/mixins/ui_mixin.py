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
    QStackedWidget,
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
from ui.widgets.empty_state import TableEmptyState
from ui.widgets.editable_table import ColumnDef, EditableTable
from ui.widgets.range_config_dialog import RangeConfigDialog
from ui.widgets.table_factory import create_register_table
from ui.widgets.table_find_bar import TableFindBar
from ui.widgets.table_scroll_wrapper import TableScrollWrapper

logger = logging.getLogger(__name__)


class PartUiMixin:
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
            QShortcut(QKeySequence("Ctrl+Shift+M"), self, self._duplicate_from_previous_month)
        QShortcut(QKeySequence("Ctrl+F"), self, self._open_table_find)
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

        if self._has_month_bar:
            btn_copy_month = QPushButton("⎘ Copiază luna trecută")
            btn_copy_month.setObjectName("btnGhost")
            btn_copy_month.setToolTip("Copiază datele din luna anterioară (Ctrl+Shift+M)")
            btn_copy_month.clicked.connect(self._duplicate_from_previous_month)
            toolbar.addWidget(btn_copy_month)

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
            "Ctrl+F = găsește  ·  Ctrl+V = lipește din Excel  ·  "
            "Galben = ziua de azi  ·  Albastru = generat automat"
        )
        table_layout.addWidget(hint)

        self._find_bar = TableFindBar(table_card)
        self._find_bar.hide()
        table_layout.addWidget(self._find_bar)

        if self.has_copii_adulti:
            self.tabs = QTabWidget()
            self.table_adulti = self._make_table()
            self.table_copii = self._make_table()
            self._table_stack = QStackedWidget()
            self._empty_state = TableEmptyState()
            self._empty_state.regenerate_clicked.connect(self._regenerate_days)
            self._empty_state.copy_month_clicked.connect(self._duplicate_from_previous_month)
            self._empty_state.add_row_clicked.connect(self._add_empty_row)
            self._table_stack.addWidget(self.tabs)
            self._table_stack.addWidget(self._empty_state)
            self.tabs.addTab(self._scroll_for(self.table_adulti), "Adulți")
            self.tabs.addTab(self._scroll_for(self.table_copii), "Copii până la 16 ani")
            self.tabs.currentChanged.connect(self._on_tab_changed)
            table_layout.addWidget(self._table_stack)
            self.table = self.table_adulti
        else:
            self.tabs = None
            self.table = self._make_table()
            self._table_stack = QStackedWidget()
            self._empty_state = TableEmptyState()
            self._empty_state.regenerate_clicked.connect(self._regenerate_days)
            self._empty_state.copy_month_clicked.connect(self._duplicate_from_previous_month)
            self._empty_state.add_row_clicked.connect(self._add_empty_row)
            self._table_stack.addWidget(self._scroll_for(self.table))
            self._table_stack.addWidget(self._empty_state)
            table_layout.addWidget(self._table_stack)

        outer.addWidget(table_card, stretch=1)
        self._building = False
        self._update_heading()
    def _scroll_for(self, table: EditableTable) -> TableScrollWrapper:
        return TableScrollWrapper(table)
    def _make_table(self) -> EditableTable:
        table = create_register_table(self.columns)
        table.setup(self.columns, self.computed_rules, part_id=self.part_id)
        table._allow_paste_extend = self.mode == "events"
        if hasattr(table, "attach_find_bar"):
            table.attach_find_bar(self._find_bar)
        labels = [get_all_etichete(self.part_id).get(c.key, c.key) for c in self.columns]
        table.set_header_labels(labels)
        table.cell_edited.connect(self._on_cell_edited)
        table.validation_error.connect(self._show_validation_hint)
        table.header_label_changed.connect(self._on_header_label_changed)
        table.setMinimumHeight(320)
        table.setMinimumWidth(max(900, len(self.columns) * 90))
        return table
    def _open_table_find(self) -> None:
        table = self._active_table()
        if hasattr(table, "open_find"):
            table.open_find()

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
        self.table = self.table_adulti if self.tabs.currentIndex() == 0 else self.table_copii
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
    def _show_validation_hint(self, msg: str) -> None:
        self.main_window.statusBar().showMessage(msg, 3000)

    def _refresh_table_chrome(self, table: EditableTable, cached: dict | None = None) -> None:
        if not hasattr(self, "_table_stack"):
            return
        self._update_empty_state(table, cached or {})
        self._update_today_highlight(table)

    def _update_empty_state(self, table: EditableTable, cached: dict) -> None:
        db_empty = bool(cached.get("db_empty"))
        data_rows = len(table.get_data_rows()) if hasattr(table, "get_data_rows") else 0
        show_empty = False
        luna_name = LUNI_RO[self.month - 1] if self._has_month_bar else str(self.year)

        if self.mode in ("events", "crud") and data_rows == 0:
            show_empty = True
            if self.mode == "events":
                title = "Niciun eveniment înregistrat"
                subtitle = f"Adăugați activități pentru {luna_name} {self.year}."
            else:
                title = "Lista este goală"
                subtitle = "Adăugați primul rând pentru a începe evidența."
            self._empty_state.configure(
                title=title,
                subtitle=subtitle,
                show_regenerate=False,
                show_copy_month=self._has_month_bar and self.mode == "events",
                show_add_row=True,
            )
        elif self.mode == "daily" and db_empty:
            show_empty = True
            self._empty_state.configure(
                title=f"Luna {luna_name} nu are încă date",
                subtitle="Generați zilele lucrătoare sau copiați structura din luna anterioară.",
                show_regenerate=True,
                show_copy_month=self.month > 1,
                show_add_row=False,
            )

        self._table_stack.setCurrentIndex(1 if show_empty else 0)

    def _update_today_highlight(self, table: EditableTable) -> None:
        from datetime import date

        if not hasattr(table, "update_today_highlight"):
            return
        today = date.today()
        if self.mode != "daily" or self.year != today.year or self.month != today.month:
            table.update_today_highlight(self.date_field, None)
            return
        dd_mm = f"{today.day:02d}.{today.month:02d}"
        table.update_today_highlight(self.date_field, dd_mm)
