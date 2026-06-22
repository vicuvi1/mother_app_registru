"""Partea III — Evidența documentelor înregistrate."""

from database.models import DocumenteInregistrate
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

DIN_CARE = [
    "consultare_pe_loc", "imprumut_pe_loc",
    "imprumut_la_domiciliu", "imprumut_inter_bibliotecar",
]
CATS = [
    "carti", "publicatii_seriale", "documente_muzica", "documente_audiovizuale",
    "documente_electronice_cd_dvd", "alte_documente",
]

G_DIN_CARE = "Din care"
G_CATEGORII = "După categorii de documente"
G_LIMBI = "După limbi"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("total_imprumuturi", "int", computed_from=DIN_CARE),
    *[ColumnDef(k, "int", group=G_DIN_CARE) for k in DIN_CARE],
    *[ColumnDef(k, "int", group=G_CATEGORII) for k in CATS],
    ColumnDef("limba_romana", "int", group=G_LIMBI),
    ColumnDef("alte_limbi", "int", group=G_LIMBI),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="III",
        part_id="part_03",
        title="Evidența documentelor înregistrate",
        model_class=DocumenteInregistrate,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
        computed_rules={"total_imprumuturi": DIN_CARE},
    )
