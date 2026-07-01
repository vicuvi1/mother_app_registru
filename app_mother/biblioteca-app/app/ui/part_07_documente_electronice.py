"""Partea VII — Documente electronice online (pe luni)."""
from __future__ import annotations

from database.models import DocumenteElectronice
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

G_MEDIU = "Mediu furnizare"
G_CATEGORII = "După categorii de documente"
G_LIMBI = "După limbi"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("total_documente_electronice", "int"),
    ColumnDef("mediu_email", "int", group=G_MEDIU),
    ColumnDef("mediu_skype_retele_sociale", "int", group=G_MEDIU),
    ColumnDef("carti", "int", group=G_CATEGORII),
    ColumnDef("publicatii_seriale", "int", group=G_CATEGORII),
    ColumnDef("documente_muzica", "int", group=G_CATEGORII),
    ColumnDef("documente_audiovizuale", "int", group=G_CATEGORII),
    ColumnDef("documente_electronice_cd_dvd", "int", group=G_CATEGORII),
    ColumnDef("alte_documente", "int", group=G_CATEGORII),
    ColumnDef("limba_romana", "int", group=G_LIMBI),
    ColumnDef("alte_limbi", "int", group=G_LIMBI),
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="VII",
        part_id="part_07",
        title="Evidența documentelor electronice online",
        model_class=DocumenteElectronice,
        columns=COLUMNS,
        main_window=main_window,
        mode="monthly",
        has_copii_adulti=True,
        show_month=False,
        cumulative=False,
    )
