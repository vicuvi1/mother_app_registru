"""Partea IV — Evidența documentelor (conținut CZU)."""

from database.models import DocumenteContinutCZU
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

CZU = [
    "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie", "czu_3_stiinte_sociale",
    "czu_5_matematica", "czu_6_stiinte_aplicate", "czu_7_arte", "czu_8_limbi", "czu_9_geografie",
]

G_CZU = "După conținut (CZU)"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("total_imprumuturi", "int", computed_from=CZU),
    *[ColumnDef(k, "int", group=G_CZU) for k in CZU],
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="IV",
        part_id="part_04",
        title="Evidența documentelor (conținut CZU)",
        model_class=DocumenteContinutCZU,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
        computed_rules={"total_imprumuturi": CZU},
    )
