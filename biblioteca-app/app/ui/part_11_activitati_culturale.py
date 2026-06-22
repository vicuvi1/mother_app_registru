"""Partea XI — Activități culturale și științifice (structură conform registrului fizic)."""

from database.models import ActivitatiCulturale
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

TOTAL_NUMAR = "Total număr"

COLUMNS = [
    ColumnDef("data", "date", editable=True),
    ColumnDef("total_activitati", "int", group=TOTAL_NUMAR),
    ColumnDef("din_care_expozitii", "int", group=TOTAL_NUMAR),
    ColumnDef("tipul_activitatii", "inline_text"),
    ColumnDef("denumirea_activitatii", "inline_text"),
    ColumnDef("total_participanti", "int"),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
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
