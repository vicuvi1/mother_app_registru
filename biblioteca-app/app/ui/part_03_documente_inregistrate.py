"""Partea III — Evidența documentelor înregistrate."""

from core.part_sync import (
    PART03_DIN_CARE,
    PART03_IMPRUMUT_KEYS,
    PART03_MIRROR_OVERRIDE,
    apply_part03_mirrors,
    invalidate_part04_cache_if_loaded,
    part03_row_total,
    sync_part04_categories,
)
from database.models import DocumenteInregistrate
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

DIN_CARE = [
    "consultare_pe_loc", "imprumut_pe_loc",
    "imprumut_la_domiciliu", "imprumut_inter_bibliotecar",
]
CATS = [
    "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
    "documente_electronice_cd_dvd", "alte_documente",
]

G_DIN_CARE = "Din care"
G_CATEGORII = "După categorii de documente"
G_LIMBI = "După limbi"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("total_imprumuturi", "int", computed_from=DIN_CARE),
    *[ColumnDef(k, "int", group=G_DIN_CARE) for k in DIN_CARE],
    *[ColumnDef(k, "int", group=G_CATEGORII) for k in CATS],
    ColumnDef("limba_romana", "int", group=G_LIMBI),
    ColumnDef("alte_limbi", "int", group=G_LIMBI),
]


class Part03Page(PartPageBase):
    """Partea III — total împrumuturi = suma coloanelor „Din care”."""

    def _load_table(self, table, categorie: str | None, fast: bool = False) -> None:
        super()._load_table(table, categorie, fast=fast)
        from core.part_sync import sync_part03_table_mirrors

        if sync_part03_table_mirrors(table):
            key = self._cache_key(categorie=categorie)
            self._data_cache[key] = self._snapshot_table(table)
            self._recompute_visible_totals()

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)

        table = self.sender()
        if table is None:
            return
        if key == "carti":
            total = part03_row_total(table.get_data_rows()[row])
            table.set_row_extra(
                row, PART03_MIRROR_OVERRIDE["carti"], int(value or 0) != total
            )
            return
        if key == "limba_romana":
            total = part03_row_total(table.get_data_rows()[row])
            table.set_row_extra(
                row, PART03_MIRROR_OVERRIDE["limba_romana"], int(value or 0) != total
            )
            return
        if key in PART03_DIN_CARE and apply_part03_mirrors(table, row):
            self._recompute_visible_totals()
        if key in PART03_IMPRUMUT_KEYS:
            invalidate_part04_cache_if_loaded(self.main_window)

    def save_all(self, show_status: bool = True, reload: bool = False) -> bool:
        ok = super().save_all(show_status=show_status, reload=reload)
        if ok:
            sync_part04_categories(self.year, self.month)
            invalidate_part04_cache_if_loaded(self.main_window)
        return ok


def create_page(main_window) -> PartPageBase:
    return Part03Page(
        roman="III",
        part_id="part_03",
        title="Evidența documentelor înregistrate",
        model_class=DocumenteInregistrate,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
        computed_rules={"total_imprumuturi": DIN_CARE},
    )
