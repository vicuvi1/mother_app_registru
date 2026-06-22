"""Partea VI — Activități de informare (structură conform registrului fizic)."""

from database.models import ActivitatiInformare
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

GEN_ACTIVITATE = "Gen de activitate"

COLUMNS = [
    ColumnDef("grup_tinta_subiect", "preset_text"),
    ColumnDef("activitate_individuala", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("activitate_grup", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("activitate_public_larg", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("numar_participanti", "int"),
    ColumnDef("documente_consultate", "int"),
    ColumnDef("responsabil", "responsabil"),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="VI",
        part_id="part_06",
        title="Evidența activităților de informare",
        model_class=ActivitatiInformare,
        columns=COLUMNS,
        main_window=main_window,
        mode="events",
        has_copii_adulti=True,
        cumulative=True,
        date_field="data",
    )
