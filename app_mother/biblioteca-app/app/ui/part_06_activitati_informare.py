"""Partea VI — Activități de informare (structură conform registrului fizic)."""

from database.models import ActivitatiInformare
from ui.part_base import PartPageBase
from ui.parts.mixins.participant_split_mixin import ParticipantGenderSplitMixin
from ui.widgets.editable_table import ColumnDef

GEN_ACTIVITATE = "Gen de activitate"
PARTICIPANTI = "Număr participanți"

COLUMNS = [
    ColumnDef("grup_tinta_subiect", "preset_text"),
    ColumnDef("activitate_individuala", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("activitate_grup", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("activitate_public_larg", "preset_text", group=GEN_ACTIVITATE),
    ColumnDef("numar_participanti", "int", group=PARTICIPANTI),
    ColumnDef("participanti_masculin", "int", group=PARTICIPANTI),
    ColumnDef("participanti_feminin", "int", group=PARTICIPANTI),
    ColumnDef("documente_consultate", "int"),
    ColumnDef("responsabil", "responsabil"),
]


class Part06Page(ParticipantGenderSplitMixin, PartPageBase):
    """Partea VI — după total participanți, M/F se completează automat în 2s."""


def create_page(main_window) -> PartPageBase:
    return Part06Page(
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
