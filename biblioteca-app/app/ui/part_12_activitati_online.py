"""Partea XII — Activități culturale ONLINE."""

from database.models import ActivitatiOnline
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

G_PARTICIPANTI = "Participanți"

COLUMNS = [
    ColumnDef("data", "date", editable=True),
    ColumnDef("denumirea_activitatii", "preset_text"),
    ColumnDef("tipul_activitatii", "preset_text"),
    ColumnDef("platforma", "preset_text"),
    ColumnDef("vizualizari", "int"),
    ColumnDef("impact", "int"),
    ColumnDef("participanti_total", "int", group=G_PARTICIPANTI),
    ColumnDef("participanti_adulti", "int", group=G_PARTICIPANTI),
    ColumnDef("participanti_copii", "int", group=G_PARTICIPANTI),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="XII",
        part_id="part_12",
        title="Evidența activităților culturale ONLINE",
        model_class=ActivitatiOnline,
        columns=COLUMNS,
        main_window=main_window,
        mode="events",
        has_copii_adulti=True,
        cumulative=True,
    )
