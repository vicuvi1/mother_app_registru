"""Generează mixin-uri din part_base.py.

NOTĂ: Script arhival (Batch D). Sursa de adevăr este app/ui/parts/mixins/.
Nu rulați din nou — part_base.py este doar re-export.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src_path = ROOT / "app" / "ui" / "part_base.py"
src = src_path.read_text(encoding="utf-8")

class_match = re.search(r"^class PartPageBase\(QWidget\):\n", src, re.M)
if not class_match:
    raise SystemExit("class not found")
body_start = class_match.end()

method_pattern = re.compile(r"^    def ([a-zA-Z_][\w]*)\(", re.M)
matches = list(method_pattern.finditer(src, body_start))
methods: dict[str, str] = {}
for i, m in enumerate(matches):
    name = m.group(1)
    start = m.start()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(src)
    methods[name] = src[start:end].rstrip() + "\n"

cache_names = {
    "_cache_key", "_snapshot_table", "_cache_current_period", "_save_if_dirty", "_invalidate_caches",
    "_prior_months_cache_key", "_numeric_total_keys", "_accumulate_record", "_get_prior_months_totals",
    "_compute_cumulative_live", "_load_current", "_fetch_table_data", "_load_table", "_schedule_preload_adjacent",
    "_deferred_persist", "_persist_cached_period", "_preload_all_months", "_warm_cumulative_cache", "_preload_adjacent_months",
}
data_names = {
    "_query_rows", "_ensure_monthly_rows", "_ensure_daily_rows", "_record_to_dict", "_update_totals",
    "_compute_cumulative", "_regenerate_days", "_generate_month", "_generate_yearly", "_add_empty_row",
    "_duplicate_selected_row", "save_all", "_save_rows_data", "_save_table", "_find_existing_id",
    "_sync_ids_after_save", "_row_to_kwargs", "_open_text_presets", "_open_ranges",
}
export_names = {
    "_query_rows_period", "_skeleton_daily", "_skeleton_monthly", "_rows_for_page", "_sum_rows",
    "_compute_cumulative_period", "_build_page", "_pages_for_part", "_cover_page", "_collect_pages",
    "_suggested_filename", "_export", "_open_file", "_print_table",
}
ui_names = set(methods) - cache_names - data_names - export_names

mixin_imports = '''from __future__ import annotations

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
'''


def write_mixin(path: Path, class_name: str, names: set[str]) -> None:
    order = list(methods.keys())
    parts = [f"{mixin_imports}\n\nclass {class_name}:\n"]
    for n in sorted(names, key=lambda x: order.index(x) if x in order else 9999):
        if n in methods:
            parts.append(methods[n])
    path.write_text("".join(parts), encoding="utf-8")


base = ROOT / "app" / "ui" / "parts"
(base / "mixins").mkdir(parents=True, exist_ok=True)
write_mixin(base / "mixins" / "cache_mixin.py", "PartCacheMixin", cache_names)
write_mixin(base / "mixins" / "data_mixin.py", "PartDataMixin", data_names)
write_mixin(base / "mixins" / "export_mixin.py", "PartExportMixin", export_names)
write_mixin(base / "mixins" / "ui_mixin.py", "PartUiMixin", ui_names)

header = '''"""Pagină de bază pentru Părțile registrului — compune mixin-urile."""

from PyQt6.QtWidgets import QWidget

from ui.parts.mixins.cache_mixin import PartCacheMixin
from ui.parts.mixins.data_mixin import PartDataMixin
from ui.parts.mixins.export_mixin import PartExportMixin
from ui.parts.mixins.ui_mixin import PartUiMixin


class PartPageBase(PartUiMixin, PartCacheMixin, PartDataMixin, PartExportMixin, QWidget):
    """Pagină reutilizabilă pentru o Parte din registru (daily | monthly | events | crud)."""
'''
(base / "part_page_base.py").write_text(header, encoding="utf-8")
print("OK", len(ui_names), "ui methods")
