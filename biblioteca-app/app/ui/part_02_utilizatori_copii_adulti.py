"""Partea II — Evidența utilizatorilor (Copii / Adulți)."""

from database.models import EvidentaUtilizatoriCopiiAdulti
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef

SUB = [
    "imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice",
    "instruiri", "alte_scopuri_excursii",
]
G_DIN_CARE = "Din care"
G_VIZITE = "Vizite virtuale"
G_VIZITATORI = "Vizitatori virtuali"
G_FB = "Facebook"
G_IG = "Instagram"
G_TW = "Twitter"

COLUMNS = [
    ColumnDef("data", "date", editable=False),
    ColumnDef("intrari_total_zi", "int", computed_from=SUB),
    *[ColumnDef(k, "int", group=G_DIN_CARE) for k in SUB],
    ColumnDef("vizite_virtuale_total", "int", group=G_VIZITE, computed_from=["vizite_virtuale_pagina_web", "vizite_virtuale_blog"]),
    ColumnDef("vizite_virtuale_pagina_web", "int", group=G_VIZITE),
    ColumnDef("vizite_virtuale_blog", "int", group=G_VIZITE),
    ColumnDef("vizitatori_virtuali_total", "int", group=G_VIZITATORI, computed_from=["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"]),
    ColumnDef("vizitatori_virtuali_pagina_web", "int", group=G_VIZITATORI),
    ColumnDef("vizitatori_virtuali_blog", "int", group=G_VIZITATORI),
    ColumnDef("facebook_vizualizari", "int", group=G_FB),
    ColumnDef("facebook_impact", "int", group=G_FB),
    ColumnDef("facebook_interactiuni", "int", group=G_FB),
    ColumnDef("instagram_vizualizari", "int", group=G_IG),
    ColumnDef("instagram_impact", "int", group=G_IG),
    ColumnDef("instagram_interactiuni", "int", group=G_IG),
    ColumnDef("twitter_vizualizari", "int", group=G_TW),
    ColumnDef("twitter_impact", "int", group=G_TW),
    ColumnDef("twitter_interactiuni", "int", group=G_TW),
]

COMPUTED = {
    "intrari_total_zi": SUB,
    "vizite_virtuale_total": ["vizite_virtuale_pagina_web", "vizite_virtuale_blog"],
    "vizitatori_virtuali_total": ["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"],
}


def create_page(main_window) -> PartPageBase:
    return PartPageBase(
        roman="II",
        part_id="part_02",
        title="Evidența utilizatorilor (Copii / Adulți)",
        model_class=EvidentaUtilizatoriCopiiAdulti,
        columns=COLUMNS,
        main_window=main_window,
        mode="daily",
        has_copii_adulti=True,
        cumulative=True,
        computed_rules=COMPUTED,
    )
