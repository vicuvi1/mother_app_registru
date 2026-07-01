"""Partea V — Cercetări bibliografice (structură conform registrului fizic)."""
from __future__ import annotations

from database.models import CercetariBibliografice
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

TEMA = "Tema (titlul)"
TIP_REF = "Tip de referință bibliografică"

COLUMNS = [
    ColumnDef("data_primirii_cererii", "date", editable=True),
    ColumnDef("total_referinte", "int"),
    ColumnDef("date_despre_solicitant", "preset_text"),
    ColumnDef("statut_socio_profesional", "preset_text"),
    ColumnDef("referinta", "preset_text"),
    ColumnDef("cercetare_bibliografica", "preset_text", group=TEMA),
    ColumnDef("consultatie", "preset_text", group=TEMA),
    ColumnDef("referinta_tematica", "preset_text", group=TIP_REF),
    ColumnDef("referinta_de_concretizare", "preset_text", group=TIP_REF),
    ColumnDef("referinta_de_adresa", "preset_text", group=TIP_REF),
    ColumnDef("referinta_factologie", "preset_text", group=TIP_REF),
    ColumnDef("limite_cronologice", "preset_text"),
    ColumnDef("surse_consultatie", "int"),
    ColumnDef("numar_descrieri_bibliografice", "int"),
    ColumnDef("surse_recomandate", "int"),
    ColumnDef("data_finalizarii_cererii", "date", editable=True),
    ColumnDef("responsabil", "responsabil"),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="V",
        part_id="part_05",
        title="Evidența cercetărilor bibliografice și a referințelor",
        model_class=CercetariBibliografice,
        columns=COLUMNS,
        main_window=main_window,
        mode="events",
        has_copii_adulti=True,
        cumulative=True,
        date_field="data_primirii_cererii",
    )
