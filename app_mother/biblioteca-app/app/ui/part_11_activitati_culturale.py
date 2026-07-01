"""Partea XI — Activități culturale și științifice (structură conform registrului fizic)."""
from __future__ import annotations

from database.models import ActivitatiCulturale
from ui.part_base import PartPageBase
from ui.parts.mixins.participant_split_mixin import ParticipantGenderSplitMixin
from ui.widgets.editable_table import ColumnDef

TOTAL_NUMAR = "Total număr"
PARTICIPANTI = "Număr participanți"

COLUMNS = [
    ColumnDef("data", "date", editable=True),
    ColumnDef("total_activitati", "int", group=TOTAL_NUMAR),
    ColumnDef("din_care_expozitii", "int", group=TOTAL_NUMAR),
    ColumnDef("tipul_activitatii", "preset_text"),
    ColumnDef("denumirea_activitatii", "preset_text"),
    ColumnDef("total_participanti", "int", group=PARTICIPANTI),
    ColumnDef("participanti_masculin", "int", group=PARTICIPANTI),
    ColumnDef("participanti_feminin", "int", group=PARTICIPANTI),
]


class Part11Page(ParticipantGenderSplitMixin, PartPageBase):
    PARTICIPANTI_TOTAL_KEY = "total_participanti"

    def _sync_part02_for_date(self, categorie: str, date: str | None) -> None:
        if date:
            from core.part02_cross_sync import on_part11_total_changed

            on_part11_total_changed(self.main_window, self, categorie, date)

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)
        if key not in (self.PARTICIPANTI_TOTAL_KEY, "data"):
            return
        table = self.sender()
        if table is None:
            return
        rows = table.get_data_rows()
        if row < 0 or row >= len(rows):
            return
        categorie = "adulti" if table is self.table_adulti else "copii"
        self._sync_part02_for_date(categorie, rows[row].get("data"))

    def _generate_month(self) -> None:
        super()._generate_month()
        from core.part02_cross_sync import sync_part02_from_ix_xi

        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "adulti")
        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "copii")


def create_page(main_window) -> PartPageBase:
    return Part11Page(
        roman="XI",
        part_id="part_11",
        title="Evidența activităților culturale și științifice",
        model_class=ActivitatiCulturale,
        columns=COLUMNS,
        main_window=main_window,
        mode="events",
        has_copii_adulti=True,
        cumulative=True,
    )
