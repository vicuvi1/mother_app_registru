"""Partea XIV — Activități de voluntariat."""
from __future__ import annotations

from database.models import Voluntariat
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

COLUMNS = [
    ColumnDef("nume_prenume", "preset_text"),
    ColumnDef("nr_contract", "preset_text"),
    ColumnDef("data_inceperii", "preset_text"),
    ColumnDef("data_incheierii", "preset_text"),
    ColumnDef("numar_ore", "int"),
    ColumnDef("activitati_realizate", "preset_text"),
    ColumnDef("coordonator", "responsabil"),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="XIV",
        part_id="part_14",
        title="Activități de voluntariat",
        model_class=Voluntariat,
        columns=COLUMNS,
        main_window=main_window,
        mode="crud",
        show_month=False,
    )
