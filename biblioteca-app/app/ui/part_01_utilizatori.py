"""Partea I — Evidența utilizatorilor."""

from database.models import EvidentaUtilizatori
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

G_ACTIVI = "Utilizatori activi"
G_STATUT = "După statutul ocupației și social"
G_VARSTA = "După vârstă"
G_SEX_COPII = "După sex copii 16 ani"
G_SEX_ADULTI = "După sex adulți"

ACTIVI = ["adulti", "copii_pana_16"]
STATUT = [
    "prescolari", "elevi", "studenti", "intelectuali",
    "muncitori", "pensionari", "someri", "alte_categorii",
]
VARSTA = ["tineri_17_34", "adulti_35_64", "varstnici_65_plus"]
SEX = ["sex_copii_f", "sex_copii_m", "sex_adulti_f", "sex_adulti_m"]

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    *[ColumnDef(k, "int", group=G_ACTIVI) for k in ACTIVI],
    *[ColumnDef(k, "int", group=G_STATUT) for k in STATUT],
    *[ColumnDef(k, "int", group=G_VARSTA) for k in VARSTA],
    *[ColumnDef(k, "int", group=G_SEX_COPII) for k in ("sex_copii_f", "sex_copii_m")],
    *[ColumnDef(k, "int", group=G_SEX_ADULTI) for k in ("sex_adulti_f", "sex_adulti_m")],
]


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="I",
        part_id="part_01",
        title="Evidența utilizatorilor",
        model_class=EvidentaUtilizatori,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        cumulative=True,
        numeric_columns=ACTIVI + STATUT + VARSTA + SEX,
    )
