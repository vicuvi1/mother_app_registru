"""Partea IX — Instruirea utilizatorilor (Copii / Adulți — tabele distincte)."""

from __future__ import annotations

from typing import Any

from core.constants_manager import get_all_etichete
from core.part02_cross_sync import PART09_TOTAL, on_part09_total_changed
from database.models import Instruiri
from ui.part_base import PartPageBase
from ui.widgets.editable_table import ColumnDef, EditableTable
from ui.widgets.table_factory import create_register_table

FORMAT = "Formatul instruirii"
FORMA = "Forma de instruire continuă"
PARTICIPANTI = "Participanți"
TOTAL_PARTICIPANTI = "Total participanți"
COPII = "Copii"
COPII_SEX = "copii până la 16 ani după sex"
G_STATUT = "După statutul ocupației"
G_VARSTA = "După vârstă"
G_SEX_MATURI = "Maturi după sex"

_FORMA_COLUMNS = [
    ColumnDef("forma_formala", "bool", group=FORMA, count_in_total=True),
    ColumnDef("ore_formala", "int", group=FORMA),
    ColumnDef("forma_non_formala", "bool", group=FORMA, count_in_total=True),
    ColumnDef("ore_non_formala", "int", group=FORMA),
    ColumnDef("forma_informala", "bool", group=FORMA, count_in_total=True),
]

_COLUMNS_BASE = [
    ColumnDef("data", "date", editable=True),
    ColumnDef("format_online", "bool", group=FORMAT, count_in_total=True),
    ColumnDef("format_offline", "bool", group=FORMAT, count_in_total=True),
    *_FORMA_COLUMNS,
    ColumnDef("tema_instruirii", "preset_text"),
    ColumnDef("formator", "preset_text"),
]

COLUMNS_ADULTI = [
    *_COLUMNS_BASE,
    ColumnDef("total_participanti", "int", group=TOTAL_PARTICIPANTI, super_group=PARTICIPANTI),
    ColumnDef("studenti", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("intelectuali", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("pensionari", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("someri", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("muncitori", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("alte_categorii", "int", group=G_STATUT, super_group=PARTICIPANTI),
    ColumnDef("tineri_17_34", "int", group=G_VARSTA, super_group=PARTICIPANTI),
    ColumnDef("adulti_35_64", "int", group=G_VARSTA, super_group=PARTICIPANTI),
    ColumnDef("varstnici_65_plus", "int", group=G_VARSTA, super_group=PARTICIPANTI),
    ColumnDef("participanti_feminin", "int", group=G_SEX_MATURI, super_group=PARTICIPANTI),
    ColumnDef("participanti_masculin", "int", group=G_SEX_MATURI, super_group=PARTICIPANTI),
]

COLUMNS_COPII = [
    *_COLUMNS_BASE,
    ColumnDef("total_participanti", "int", group=TOTAL_PARTICIPANTI, super_group=PARTICIPANTI),
    ColumnDef("prescolari", "int", group=COPII, super_group=PARTICIPANTI),
    ColumnDef("elevi", "int", group=COPII, super_group=PARTICIPANTI),
    ColumnDef("participanti_feminin", "int", group=COPII_SEX, super_group=PARTICIPANTI),
    ColumnDef("participanti_masculin", "int", group=COPII_SEX, super_group=PARTICIPANTI),
]


class Part09Page(PartPageBase):
    """Partea IX — tab Copii și tab Adulți cu structuri diferite (registru fizic)."""

    def __init__(self, *args, **kwargs) -> None:
        self.columns_adulti = COLUMNS_ADULTI
        self.columns_copii = COLUMNS_COPII
        self._table_build_index = 0
        super().__init__(*args, **kwargs)

    def _columns_for(self, categorie: str | None) -> list[ColumnDef]:
        if categorie == "copii":
            return self.columns_copii
        return self.columns_adulti

    def _make_table(self) -> EditableTable:
        categorie = "adulti" if self._table_build_index == 0 else "copii"
        self._table_build_index += 1
        cols = self._columns_for(categorie)
        table = create_register_table(cols)
        table.setup(cols, self.computed_rules, part_id=self.part_id)
        table._allow_paste_extend = self.mode == "events"
        if hasattr(table, "attach_find_bar"):
            table.attach_find_bar(self._find_bar)
        labels = [get_all_etichete(self.part_id).get(c.key, c.key) for c in cols]
        table.set_header_labels(labels)
        table.cell_edited.connect(self._on_cell_edited)
        table.validation_error.connect(self._show_validation_hint)
        table.header_label_changed.connect(self._on_header_label_changed)
        table.setMinimumHeight(320)
        return table

    def _load_table(
        self, table: EditableTable, categorie: str | None, fast: bool = False
    ) -> None:
        super()._load_table(table, categorie, fast=fast)
        if hasattr(table, "refresh_horizontal_layout"):
            table.refresh_horizontal_layout()

    def _record_to_dict(self, rec) -> dict:
        cat = getattr(rec, "categorie_varsta", None) or "adulti"
        cols = self._columns_for(cat)
        d: dict[str, Any] = {}
        for col in cols:
            d[col.key] = getattr(rec, col.key, None)
        if self.mode in ("daily", "events") and hasattr(rec, self.date_field):
            d[self.date_field] = getattr(rec, self.date_field, None)
        if self.mode == "monthly" and hasattr(rec, "luna"):
            from core.constants_manager import LUNI_RO

            d["luna"] = rec.luna
            d["data"] = LUNI_RO[rec.luna - 1]
        return d

    def _row_to_kwargs(
        self,
        row: dict,
        categorie: str | None,
        for_update: bool = False,
        row_index: int = 0,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> dict:
        saved = self.columns
        self.columns = self._columns_for(categorie)
        try:
            return super()._row_to_kwargs(
                row, categorie, for_update, row_index, year=year, month=month
            )
        finally:
            self.columns = saved

    def _numeric_total_keys(self, categorie: str | None = None) -> dict[str, int]:
        cat = categorie if categorie is not None else self._active_category()
        return {
            c.key: 0
            for c in self._columns_for(cat)
            if c.col_type == "int" or c.counts_checked_in_total()
        }

    def _accumulate_record(self, result: dict[str, int], rec, categorie: str | None = None) -> None:
        cat = categorie or getattr(rec, "categorie_varsta", None) or "adulti"
        for col in self._columns_for(cat):
            if col.col_type == "int":
                result[col.key] += getattr(rec, col.key, 0) or 0
            elif col.counts_checked_in_total():
                if getattr(rec, col.key, False):
                    result[col.key] += 1

    def _get_prior_months_totals(self, categorie: str | None, month: int | None = None) -> dict[str, int]:
        from sqlalchemy import and_, case, func, select

        from database.db_manager import get_session

        m = month or self.month
        if m <= 1:
            return self._numeric_total_keys(categorie)

        key = self._prior_months_cache_key(categorie, m)
        if key in self._cumulative_cache:
            return dict(self._cumulative_cache[key])

        result = self._numeric_total_keys(categorie)
        cols = self._columns_for(categorie)
        sum_exprs = []
        labels: list[str] = []
        for col in cols:
            if col.col_type == "int":
                sum_exprs.append(
                    func.coalesce(func.sum(getattr(self.model_class, col.key)), 0).label(col.key)
                )
                labels.append(col.key)
            elif col.counts_checked_in_total():
                sum_exprs.append(
                    func.coalesce(
                        func.sum(
                            case(
                                (getattr(self.model_class, col.key).is_(True), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ).label(col.key)
                )
                labels.append(col.key)
        if not sum_exprs:
            return result

        with get_session() as session:
            filters = [
                self.model_class.an == self.year,
                self.model_class.luna < m,
            ]
            if categorie and hasattr(self.model_class, "categorie_varsta"):
                filters.append(self.model_class.categorie_varsta == categorie)
            row = session.execute(select(*sum_exprs).where(and_(*filters))).one()
            for label in labels:
                result[label] = int(row._mapping[label] or 0)

        self._cumulative_cache[key] = dict(result)
        return result

    def _generate_month(self) -> None:
        saved = self.columns
        self.columns = self._columns_for(self._active_category())
        try:
            super()._generate_month()
        finally:
            self.columns = saved
        from core.part02_cross_sync import sync_part02_from_ix_xi

        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "adulti")
        sync_part02_from_ix_xi(self.main_window, self.year, self.month, "copii")

    def _open_text_presets(self) -> None:
        from ui.widgets.text_presets_dialog import TextPresetsDialog

        seen: dict[str, ColumnDef] = {}
        for col in self.columns_adulti + self.columns_copii:
            seen[col.key] = col
        dlg = TextPresetsDialog(self.part_id, list(seen.values()), self)
        if dlg.exec():
            for tbl in (self.table_adulti, self.table_copii):
                tbl.refresh_preset_dropdowns()
            self.main_window.statusBar().showMessage("Liste text salvate", 3000)

    def _sync_part02_for_date(self, categorie: str, date: str | None) -> None:
        if date:
            on_part09_total_changed(self.main_window, self, categorie, date)

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)
        if key not in (PART09_TOTAL, "data"):
            return
        table = self.sender()
        if table is None:
            return
        rows = table.get_data_rows()
        if row < 0 or row >= len(rows):
            return
        categorie = "adulti" if table is self.table_adulti else "copii"
        self._sync_part02_for_date(categorie, rows[row].get("data"))


def create_page(main_window) -> PartPageBase:
    return Part09Page(
        roman="IX",
        part_id="part_09",
        title="Instruirea utilizatorilor",
        model_class=Instruiri,
        columns=COLUMNS_ADULTI,
        main_window=main_window,
        mode="events",
        has_copii_adulti=True,
        cumulative=True,
    )
