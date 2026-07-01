"""Partea XIII — Parteneri ai bibliotecii."""
from __future__ import annotations

from database.models import Parteneri
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

COLUMNS = [
    ColumnDef("partener", "preset_text"),
    ColumnDef("scope_local", "scope_local", count_in_total=True),
    ColumnDef("scope_national", "scope_national", count_in_total=True),
    ColumnDef("scope_international", "scope_intl", count_in_total=True),
    ColumnDef("date_contact", "preset_text"),
    ColumnDef("tip_contract", "preset_text"),
    ColumnDef("data_semnarii", "preset_text"),
    ColumnDef("termen_realizare", "preset_text"),
    ColumnDef("modalitati_realizare", "preset_text"),
    ColumnDef("participanti_total", "int"),
    ColumnDef("participanti_adulti", "int"),
    ColumnDef("participanti_copii", "int"),
    ColumnDef("impact", "int"),
]


def create_page(main_window) -> PartPageBase:
    page = PartPageBase(
        roman="XIII",
        part_id="part_13",
        title="Parteneri ai bibliotecii",
        model_class=Parteneri,
        columns=COLUMNS,
        main_window=main_window,
        mode="crud",
        show_month=False,
    )
    return page
