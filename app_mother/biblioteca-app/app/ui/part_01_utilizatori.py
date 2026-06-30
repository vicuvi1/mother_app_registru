"""Partea I — Evidența utilizatorilor."""

from database.models import EvidentaUtilizatori
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef, EditableTable

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


class Part01Page(PartPageBase):
    """Partea I — Copii până la 16 ani = Preșcolari + Elevi (sincronizare automată)."""

    def _apply_copii_split_to_table(
        self, table: EditableTable, data_row: int, row_dict: dict
    ) -> None:
        from core.copii_split import COPII_PANA_16, ELEVI, PRESCOLARI

        table.set_data_cell_silent(
            data_row, COPII_PANA_16, int(row_dict.get(COPII_PANA_16) or 0)
        )
        table.set_data_cell_silent(data_row, PRESCOLARI, int(row_dict.get(PRESCOLARI) or 0))
        table.set_data_cell_silent(data_row, ELEVI, int(row_dict.get(ELEVI) or 0))

    def _sync_copii_split_row(self, table: EditableTable, data_row: int, edited_key: str) -> bool:
        from core.copii_split import COPII_SPLIT_KEYS, apply_copii_split_edit

        if edited_key not in COPII_SPLIT_KEYS:
            return False
        rows = table.get_data_rows()
        if data_row < 0 or data_row >= len(rows):
            return False
        row_dict = dict(rows[data_row])
        if not apply_copii_split_edit(row_dict, edited_key):
            return False
        self._apply_copii_split_to_table(table, data_row, row_dict)
        return True

    def _bind_copii_split_validator(self, table: EditableTable) -> None:
        from core.copii_split import COPII_SPLIT_KEYS, validate_copii_split_value

        def validator(data_row: int, column_key: str, new_value) -> tuple[bool, str]:
            if column_key not in COPII_SPLIT_KEYS:
                return True, ""
            rows = table.get_data_rows()
            if data_row < 0 or data_row >= len(rows):
                return True, ""
            return validate_copii_split_value(rows[data_row], column_key, new_value)

        table._register_model.set_cell_validator(validator)

    def _make_table(self) -> EditableTable:
        table = super()._make_table()
        self._bind_copii_split_validator(table)
        return table

    def _reconcile_table_copii_rows(self, table: EditableTable) -> bool:
        from core.copii_split import reconcile_copii_row

        changed = False
        for i, row in enumerate(table.get_data_rows()):
            row_dict = dict(row)
            if reconcile_copii_row(row_dict):
                self._apply_copii_split_to_table(table, i, row_dict)
                changed = True
        return changed

    def _load_table(
        self, table: EditableTable, categorie: str | None, fast: bool = False
    ) -> None:
        super()._load_table(table, categorie, fast=fast)
        if self._reconcile_table_copii_rows(table):
            key = self._cache_key(categorie=categorie)
            if key in self._data_cache:
                self._data_cache[key] = self._snapshot_table(table)
            self._recompute_visible_totals()

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        from core.copii_split import COPII_SPLIT_KEYS

        super()._on_cell_edited(row, key, value)
        if key not in COPII_SPLIT_KEYS:
            return
        table = self.sender()
        if table is None:
            return
        if self._sync_copii_split_row(table, row, key):
            self._recompute_visible_totals()


def create_page(main_window) -> PartPageBase:
    return Part01Page(
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
