"""Partea II — Evidența utilizatorilor (Copii / Adulți)."""
from __future__ import annotations

from core.part02_cross_sync import (
    PART02_ACTIVITATI,
    PART02_INSTRUIRI,
    on_part02_field_changed,
    sync_part02_from_ix_xi,
)
from database.models import EvidentaUtilizatoriCopiiAdulti
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef, EditableTable

SUB = [
    "imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice",
    "instruiri", "alte_scopuri_excursii",
]
G_DIN_CARE = "Din care"
G_VIZITE = "Vizite virtuale"
G_VIZITATORI = "Vizitatori virtuali"
G_RETELE = "Indicatori ai rețelelor sociale"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("intrari_total_zi", "int", computed_from=SUB),
    *[ColumnDef(k, "int", group=G_DIN_CARE) for k in SUB],
    ColumnDef("vizite_virtuale_total", "int", group=G_VIZITE, computed_from=["vizite_virtuale_pagina_web", "vizite_virtuale_blog"]),
    ColumnDef("vizite_virtuale_pagina_web", "int", group=G_VIZITE),
    ColumnDef("vizite_virtuale_blog", "int", group=G_VIZITE),
    ColumnDef("vizitatori_virtuali_total", "int", group=G_VIZITATORI, computed_from=["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"]),
    ColumnDef("vizitatori_virtuali_pagina_web", "int", group=G_VIZITATORI),
    ColumnDef("vizitatori_virtuali_blog", "int", group=G_VIZITATORI),
    ColumnDef("facebook_vizualizari", "int", group=G_RETELE),
    ColumnDef("facebook_impact", "int", group=G_RETELE),
    ColumnDef("facebook_interactiuni", "int", group=G_RETELE),
    ColumnDef("instagram_vizualizari", "int", group=G_RETELE),
    ColumnDef("instagram_impact", "int", group=G_RETELE),
    ColumnDef("instagram_interactiuni", "int", group=G_RETELE),
    ColumnDef("twitter_vizualizari", "int", group=G_RETELE),
    ColumnDef("twitter_impact", "int", group=G_RETELE),
    ColumnDef("twitter_interactiuni", "int", group=G_RETELE),
]

COMPUTED = {
    "intrari_total_zi": SUB,
    "vizite_virtuale_total": ["vizite_virtuale_pagina_web", "vizite_virtuale_blog"],
    "vizitatori_virtuali_total": ["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"],
}


class Part02Page(PartPageBase):
    """Partea II — Instruiri (IX) și Activități culturale (XI) sincronizate pe dată."""

    def _load_table(
        self, table: EditableTable, categorie: str | None, fast: bool = False
    ) -> None:
        super()._load_table(table, categorie, fast=fast)
        if categorie:
            sync_part02_from_ix_xi(
                self.main_window, self.year, self.month, categorie
            )

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)
        if key not in (PART02_INSTRUIRI, PART02_ACTIVITATI):
            return
        table = self.sender()
        if table is None:
            return
        rows = table.get_data_rows()
        if row < 0 or row >= len(rows):
            return
        date = rows[row].get("data")
        if not date:
            return
        categorie = "adulti" if table is self.table_adulti else "copii"
        on_part02_field_changed(
            self.main_window,
            self,
            categorie,
            date,
            key,
            max(0, int(value or 0)),
        )

    def _generate_month(self) -> None:
        super()._generate_month()
        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "adulti")
        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "copii")


def create_page(main_window) -> PartPageBase:
    return Part02Page(
        roman="II",
        part_id="part_02",
        title="Evidența utilizatorilor (Copii / Adulți)",
        model_class=EvidentaUtilizatoriCopiiAdulti,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
        computed_rules=COMPUTED,
    )
