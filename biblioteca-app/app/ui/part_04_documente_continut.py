"""Partea IV — Evidența documentelor (conținut CZU)."""

from database.models import DocumenteContinutCZU
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

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
    """Partea IV — total împrumuturi preluat din Partea III când există date acolo."""

    def _fetch_table_data(
        self, categorie: str | None, year: int | None = None, month: int | None = None
    ) -> dict:
        from core.part_sync import apply_part04_totals, load_part03_by_date

        result = super()._fetch_table_data(categorie, year, month)
        y = year or self.year
        m = month or self.month
        p3 = load_part03_by_date(categorie, y, m)
        apply_part04_totals(result["rows"], p3, CZU)
        return result

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)
        if key not in CZU:
            return
        table = self._active_table()
        rows = table.get_data_rows()
        if row >= len(rows) or rows[row].get("_sync_total_from_part03"):
            return
        total = sum(int(rows[row].get(k) or 0) for k in CZU)
        col_idx = next((i for i, c in enumerate(self.columns) if c.key == "total_imprumuturi"), None)
        if col_idx is None:
            return
        model = table._register_model
        model.store.set_cell(row, col_idx, total)
        model.dataChanged.emit(
            model.index(row, col_idx),
            model.index(row, col_idx),
        )


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
