"""Stocare în memorie pentru rândurile tabelului (folosit de model și view)."""

from __future__ import annotations

from typing import Any

from ui.widgets.table.column_def import ColumnDef


class TableDataStore:
    """Date tabulară: rânduri date, meta, rânduri total."""

    def __init__(self) -> None:
        self.columns: list[ColumnDef] = []
        self.computed_rules: dict[str, list[str]] = {}
        self.part_id: str = ""
        self.rows: list[dict[str, Any]] = []
        self.row_ids: list[int | None] = []
        self.auto_flags: list[bool] = []
        self.row_extra: list[dict[str, Any]] = []
        self.total_rows: list[tuple[str, dict[str, int]]] = []

    def clear(self) -> None:
        self.rows.clear()
        self.row_ids.clear()
        self.auto_flags.clear()
        self.row_extra.clear()
        self.total_rows.clear()

    def data_row_count(self) -> int:
        return len(self.rows)

    def total_row_count(self) -> int:
        return len(self.total_rows)

    def row_count(self) -> int:
        return self.data_row_count() + self.total_row_count()

    def is_total_row(self, row: int) -> bool:
        return row >= self.data_row_count()

    def total_label(self, row: int) -> str:
        idx = row - self.data_row_count()
        if 0 <= idx < len(self.total_rows):
            return self.total_rows[idx][0]
        return ""

    def set_payload(
        self,
        rows: list[dict],
        row_ids: list[int | None] | None = None,
        auto_flags: list[bool] | None = None,
    ) -> None:
        col_keys = {c.key for c in self.columns}
        self.rows = []
        self.row_extra = []
        for row_data in rows:
            visible = {k: row_data.get(k) for k in col_keys if k in row_data}
            extra = {k: v for k, v in row_data.items() if k not in col_keys}
            self.rows.append(visible)
            self.row_extra.append(extra)
        self.row_ids = list(row_ids or [None] * len(self.rows))
        self.auto_flags = list(auto_flags or [False] * len(self.rows))

    def get_cell(self, row: int, col: int) -> Any:
        if self.is_total_row(row):
            label, sums = self.total_rows[row - self.data_row_count()]
            col_def = self.columns[col]
            if col == 0:
                return label
            if (
                col_def.col_type == "int"
                or col_def.computed_from
                or col_def.counts_checked_in_total()
            ):
                return sums.get(col_def.key, 0)
            return ""
        col_def = self.columns[col]
        value = self.rows[row].get(col_def.key)
        if col_def.col_type == "int":
            try:
                return max(0, int(value)) if value is not None and str(value).strip() else 0
            except (TypeError, ValueError):
                return 0
        if col_def.col_type in ("bool",) or col_def.col_type.startswith("scope_"):
            return bool(value)
        return "" if value is None else value

    def set_cell(self, row: int, col: int, value: Any) -> None:
        if self.is_total_row(row):
            return
        self.rows[row][self.columns[col].key] = value

    def get_data_rows(self) -> list[dict]:
        out: list[dict] = []
        for i, row in enumerate(self.rows):
            merged = dict(row)
            if i < len(self.row_extra):
                merged.update(self.row_extra[i])
            out.append(merged)
        return out

    def compute_column_sums(self) -> dict[str, int]:
        sums: dict[str, int] = {}
        for col in self.columns:
            if col.counts_checked_in_total():
                total = sum(1 for row in self.rows if row.get(col.key))
                sums[col.key] = total
                continue
            if col.col_type != "int" and not col.computed_from:
                continue
            total = 0
            for row in self.rows:
                val = row.get(col.key)
                if isinstance(val, int):
                    total += val
                elif col.col_type == "int":
                    try:
                        total += max(0, int(val))
                    except (TypeError, ValueError):
                        pass
            sums[col.key] = total
        return sums

    def apply_computed_row(self, row: int) -> None:
        for col_def in self.columns:
            if not col_def.computed_from:
                continue
            total = 0
            for src in col_def.computed_from:
                val = self.rows[row].get(src)
                if isinstance(val, int):
                    total += val
                else:
                    try:
                        total += max(0, int(val))
                    except (TypeError, ValueError):
                        pass
            self.rows[row][col_def.key] = total

    def apply_computed_all(self) -> None:
        for row in range(self.data_row_count()):
            self.apply_computed_row(row)
