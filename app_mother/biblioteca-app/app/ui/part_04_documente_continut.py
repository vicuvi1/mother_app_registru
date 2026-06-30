"""Partea IV — Evidența documentelor (conținut CZU)."""

from database.models import DocumenteContinutCZU
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef, EditableTable

CZU = [
    "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie", "czu_3_stiinte_sociale",
    "czu_5_matematica", "czu_6_stiinte_aplicate", "czu_7_arte", "czu_8_limbi", "czu_9_geografie",
]

G_CZU = "După conținut (CZU)"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("total_imprumuturi", "int", editable=False),
    *[ColumnDef(k, "int", group=G_CZU) for k in CZU],
]


class Part04Page(PartPageBase):
    """Partea IV — total din P. III sau suma CZU dacă P. III e necompletată."""

    def _category_for_table(self, table: EditableTable) -> str | None:
        return getattr(self, "_part04_table_categorie", {}).get(id(table))

    def _apply_row_to_table(
        self,
        table: EditableTable,
        data_row: int,
        row_dict: dict,
        *,
        total_only: bool = False,
    ) -> None:
        from core.part_sync import PART04_CZU_KEYS

        table.set_data_cell_silent(
            data_row, "total_imprumuturi", int(row_dict.get("total_imprumuturi") or 0)
        )
        if total_only:
            return
        for key in PART04_CZU_KEYS:
            table.set_data_cell_silent(data_row, key, int(row_dict.get(key) or 0))

    def _part03_total_for_row(
        self, table: EditableTable, categorie: str | None, data_row: int
    ) -> int:
        from core.part_sync import part04_total_for_date

        rows = table.get_data_rows()
        if data_row < 0 or data_row >= len(rows):
            return 0
        date = rows[data_row].get("data")
        if not date:
            return 0
        return part04_total_for_date(
            self.main_window, categorie, self.year, self.month, date
        )

    def _sync_part04_row_display_total(
        self, table: EditableTable, categorie: str | None, data_row: int
    ) -> int:
        """Actualizează total: P. III dacă > 0, altfel suma CZU."""
        from core.part_sync import (
            part04_czu_sum,
            part04_row_total,
            rebalance_part04_czu_to_total,
            sync_part04_row_total_and_align,
        )

        rows = table.get_data_rows()
        if data_row < 0 or data_row >= len(rows):
            return 0

        live_p3 = self._part03_total_for_row(table, categorie, data_row)
        row_dict = dict(rows[data_row])

        if live_p3 > 0:
            sync_part04_row_total_and_align(row_dict, live_p3)
            self._apply_row_to_table(table, data_row, row_dict)
            return live_p3

        display = part04_row_total(row_dict, 0)
        if int(row_dict.get("total_imprumuturi") or 0) != display:
            table.set_data_cell_silent(data_row, "total_imprumuturi", display)
        return display

    def _refresh_part04_row_total(
        self, table: EditableTable, categorie: str | None, data_row: int
    ) -> int:
        return self._sync_part04_row_display_total(table, categorie, data_row)

    def _refresh_part04_row_total_on_focus(
        self, table: EditableTable, categorie: str | None, data_row: int
    ) -> int:
        from core.part_sync import part04_czu_sum, rebalance_part04_czu_to_total

        live_p3 = self._part03_total_for_row(table, categorie, data_row)
        display = self._sync_part04_row_display_total(table, categorie, data_row)
        if live_p3 > 0:
            rows = table.get_data_rows()
            row_dict = dict(rows[data_row])
            if part04_czu_sum(row_dict) > live_p3 and rebalance_part04_czu_to_total(row_dict):
                self._apply_row_to_table(table, data_row, row_dict)
        return display if live_p3 <= 0 else live_p3

    def _refresh_part04_table_totals(
        self, table: EditableTable, categorie: str | None
    ) -> None:
        for i in range(len(table.get_data_rows())):
            self._sync_part04_row_display_total(table, categorie, i)
        key = self._cache_key(categorie=categorie)
        if key in self._data_cache:
            self._data_cache[key] = self._snapshot_table(table)

    def _bind_part04_validator(self, table: EditableTable, categorie: str | None) -> None:
        from core.part_sync import (
            PART04_CZU_KEYS,
            part04_czu_sum,
            part04_row_total,
            rebalance_part04_czu_to_total,
            validate_part04_czu_value,
        )

        page = self

        def validator(data_row: int, column_key: str, new_value) -> tuple[bool, str]:
            if column_key not in PART04_CZU_KEYS:
                return True, ""
            rows = table.get_data_rows()
            if data_row < 0 or data_row >= len(rows):
                return True, ""
            live_p3 = page._part03_total_for_row(table, categorie, data_row)
            trial = dict(rows[data_row])
            trial[column_key] = new_value
            effective = part04_row_total(trial, live_p3)
            trial["total_imprumuturi"] = effective
            if live_p3 <= 0:
                return True, ""
            if part04_czu_sum(trial) > live_p3:
                rebalance_part04_czu_to_total(trial)
                page._apply_row_to_table(table, data_row, trial)
                trial[column_key] = new_value
            return validate_part04_czu_value(trial, column_key, new_value)

        table._register_model.set_cell_validator(validator)

        def _on_cell_focused(current, _previous) -> None:
            if not current.isValid() or not table.is_data_row(current.row()):
                return
            col = current.column()
            if col < 0 or col >= len(page.columns):
                return
            if page.columns[col].key not in PART04_CZU_KEYS:
                return
            live_p3 = page._part03_total_for_row(table, categorie, current.row())
            display = page._sync_part04_row_display_total(
                table, categorie, current.row()
            )
            if live_p3 > 0:
                page.main_window.statusBar().showMessage(
                    f"Total împrumuturi = {live_p3} (din Partea III). "
                    f"Suma CZU poate fi ≤ {live_p3}.",
                    6000,
                )
            else:
                page.main_window.statusBar().showMessage(
                    f"Total împrumuturi = {display} (suma CZU). "
                    f"Se actualizează automat la fiecare editare.",
                    6000,
                )

        table.selectionModel().currentChanged.connect(_on_cell_focused)

    def _make_table(self) -> EditableTable:
        table = super()._make_table()
        setup_count = getattr(self, "_part04_tables_setup", 0)
        if self.has_copii_adulti:
            categorie: str | None = "adulti" if setup_count == 0 else "copii"
        else:
            categorie = None
        self._part04_tables_setup = setup_count + 1
        if not hasattr(self, "_part04_table_categorie"):
            self._part04_table_categorie = {}
        self._part04_table_categorie[id(table)] = categorie
        self._bind_part04_validator(table, categorie)
        return table

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        from core.part_sync import PART04_CZU_KEYS

        super()._on_cell_edited(row, key, value)
        if key not in PART04_CZU_KEYS:
            return
        table = self.sender()
        if table is None:
            return
        categorie = self._category_for_table(table)
        self._sync_part04_row_display_total(table, categorie, row)

    def _prepare_part04_cache(self, categorie: str | None) -> None:
        from core.part_sync import sync_part04_rows_from_part03

        key = self._cache_key(categorie=categorie)
        if key not in self._data_cache:
            self._data_cache[key] = self._fetch_table_data(categorie)
        cached = self._data_cache[key]
        rows = [dict(r) for r in cached["rows"]]
        sync_part04_rows_from_part03(
            rows, self.main_window, categorie, self.year, self.month
        )
        self._data_cache[key] = {**cached, "rows": rows}

    def refresh_totals_from_part03(self) -> None:
        """Actualizează totalurile și aliniază CZU dacă depășesc totalul."""
        if self.has_copii_adulti:
            self._refresh_part04_table_totals(self.table_adulti, "adulti")
            self._refresh_part04_table_totals(self.table_copii, "copii")
        else:
            self._refresh_part04_table_totals(self.table, None)

    def _sync_part04_table_from_part03(
        self, table: EditableTable, categorie: str | None
    ) -> int:
        from core.part_sync import sync_part04_rows_from_part03

        rows = table.get_data_rows()
        changed = sync_part04_rows_from_part03(
            rows, self.main_window, categorie, self.year, self.month
        )
        for i, row in enumerate(rows):
            self._apply_row_to_table(table, i, row)
        return changed

    def _load_table(
        self, table: EditableTable, categorie: str | None, fast: bool = False
    ) -> None:
        self._prepare_part04_cache(categorie)
        super()._load_table(table, categorie, fast=fast)
        self._refresh_part04_table_totals(table, categorie)

    def _generate_month(self) -> None:
        super()._generate_month()
        if self.has_copii_adulti:
            self._sync_part04_table_from_part03(self.table_adulti, "adulti")
            self._sync_part04_table_from_part03(self.table_copii, "copii")
        else:
            self._sync_part04_table_from_part03(self.table, None)
        self._cache_current_period()

    def save_all(self, show_status: bool = True, reload: bool = False) -> bool:
        tables: list[tuple[EditableTable, str | None]] = (
            [(self.table_copii, "copii"), (self.table_adulti, "adulti")]
            if self.has_copii_adulti
            else [(self.table, None)]
        )
        for table, categorie in tables:
            for i in range(len(table.get_data_rows())):
                self._sync_part04_row_display_total(table, categorie, i)
        rebalanced = 0
        for table, categorie in tables:
            rebalanced += self._sync_part04_table_from_part03(table, categorie)
        if rebalanced:
            self.main_window.statusBar().showMessage(
                f"Repartizarea CZU a fost ajustată automat pe {rebalanced} "
                f"{'zi' if rebalanced == 1 else 'zile'} — totalul din Partea III a scăzut.",
                10000,
            )
        return super().save_all(show_status=show_status, reload=reload)

    def _on_debounced_save(self) -> None:
        if self._is_any_table_editing():
            self._debounce.start()
            return
        self.save_all(show_status=False)


def create_page(main_window) -> PartPageBase:
    return Part04Page(
        roman="IV",
        part_id="part_04",
        title="Evidența documentelor (conținut CZU)",
        model_class=DocumenteContinutCZU,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
    )
