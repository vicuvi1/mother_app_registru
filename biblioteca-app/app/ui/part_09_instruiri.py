"""Partea IX — Instruirea utilizatorilor (structură conform registrului fizic)."""

from database.models import Instruiri
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

FORMAT = "Formatul instruirii"
FORMA = "Forma de instruire continuă"
PARTICIPANTI = "Participanți"

COLUMNS = [
    ColumnDef("data", "date", editable=True),
    ColumnDef("format_online", "bool", group=FORMAT, count_in_total=True),
    ColumnDef("format_offline", "bool", group=FORMAT, count_in_total=True),
    ColumnDef("ore_formala", "int", group=FORMA),
    ColumnDef("ore_non_formala", "int", group=FORMA),
    ColumnDef("ore_informala", "int", group=FORMA),
    ColumnDef("tema_instruirii", "inline_text"),
    ColumnDef("formator", "responsabil"),
    ColumnDef("total_participanti", "int", group=PARTICIPANTI),
    ColumnDef("adulti", "int", group=PARTICIPANTI),
    ColumnDef("copii_pana_16", "int", group=PARTICIPANTI),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="IX",
        part_id="part_09",
        title="Instruirea utilizatorilor",
        model_class=Instruiri,
        columns=COLUMNS,
        main_window=main_window,
        mode="events",
        cumulative=True,
    )
