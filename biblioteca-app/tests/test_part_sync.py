"""Teste sincronizare Partea III → Partea IV."""

from core.part_sync import (
    PART03_MIRROR_OVERRIDE,
    apply_part03_default_mirrors,
    apply_part03_mirrors,
    apply_part04_totals,
    init_part03_mirror_overrides,
    sync_part03_table_mirrors,
    part03_has_imprumut_data,
    part03_row_total,
    part03_total,
    part04_czu_max_allowed,
    validate_part04_czu_value,
)


class _FakeTable:
    def __init__(self, rows: list[dict], extras: list[dict] | None = None) -> None:
        self._rows = [dict(r) for r in rows]
        self.store = type("Store", (), {"row_extra": list(extras or [{}] * len(rows))})()
        self._updates: list[tuple[int, str, int]] = []

    def get_data_rows(self) -> list[dict]:
        return self._rows

    def set_row_extra(self, i: int, key: str, value) -> None:
        while len(self.store.row_extra) <= i:
            self.store.row_extra.append({})
        self.store.row_extra[i][key] = value

    def set_data_cell_silent(self, data_row: int, key: str, value) -> bool:
        self._rows[data_row][key] = value
        self._updates.append((data_row, key, value))
        return True


def test_part03_default_mirrors_on_generate():
    row = {
        "total_imprumuturi": 17,
        "consultare_pe_loc": 10,
        "imprumut_pe_loc": 7,
        "carti": 22,
        "limba_romana": 0,
    }
    apply_part03_default_mirrors(row)
    assert row["carti"] == 17
    assert row["limba_romana"] == 17


def test_apply_part03_mirrors_updates_linked_columns():
    table = _FakeTable([{"total_imprumuturi": 12, "carti": 5, "limba_romana": 1}])
    updated = apply_part03_mirrors(table, 0)
    assert updated == ["carti", "limba_romana"]
    assert table._rows[0]["carti"] == 12
    assert table._rows[0]["limba_romana"] == 12


def test_apply_part03_mirrors_respects_manual_override():
    table = _FakeTable([{"total_imprumuturi": 12, "carti": 8, "limba_romana": 1}])
    table.set_row_extra(0, PART03_MIRROR_OVERRIDE["carti"], True)
    updated = apply_part03_mirrors(table, 0)
    assert updated == ["limba_romana"]
    assert table._rows[0]["carti"] == 8
    assert table._rows[0]["limba_romana"] == 12


def test_init_part03_mirror_overrides_marks_differences():
    table = _FakeTable([{"total_imprumuturi": 10, "carti": 10, "limba_romana": 3}])
    init_part03_mirror_overrides(table)
    assert table.store.row_extra[0].get(PART03_MIRROR_OVERRIDE["limba_romana"])
    assert PART03_MIRROR_OVERRIDE["carti"] not in table.store.row_extra[0]


def test_init_part03_mirror_skips_zero_defaults():
    table = _FakeTable([{"total_imprumuturi": 10, "carti": 0, "limba_romana": 0}])
    init_part03_mirror_overrides(table)
    assert not table.store.row_extra[0]


def test_sync_part03_table_mirrors_fills_zeros():
    table = _FakeTable([{"total_imprumuturi": 7, "carti": 0, "limba_romana": 0}])
    assert sync_part03_table_mirrors(table)
    assert table._rows[0]["carti"] == 7
    assert table._rows[0]["limba_romana"] == 7


def test_part03_row_total_prefers_stored_total():
    assert part03_row_total({"total_imprumuturi": 9, "consultare_pe_loc": 3}) == 9


def test_part04_czu_max_allowed_respects_total():
    row = {
        "total_imprumuturi": 17,
        "czu_5_matematica": 9,
        "czu_6_stiinte_aplicate": 0,
    }
    assert part04_czu_max_allowed(row, "czu_6_stiinte_aplicate") == 8


def test_validate_part04_czu_value_rejects_overflow():
    row = {"total_imprumuturi": 17, "czu_5_matematica": 9, "czu_6_stiinte_aplicate": 0}
    ok, msg = validate_part04_czu_value(row, "czu_6_stiinte_aplicate", 45)
    assert not ok
    assert "8" in msg
    assert "17" in msg


def test_validate_part04_czu_value_rejects_when_other_columns_exceed_total():
    row = {
        "total_imprumuturi": 59,
        "czu_0_generalitati": 5,
        "czu_2_religie": 9,
        "czu_3_stiinte_sociale": 2,
        "czu_5_matematica": 20,
        "czu_6_stiinte_aplicate": 2,
        "czu_7_arte": 9,
        "czu_8_limbi": 13,
        "czu_9_geografie": 6,
        "czu_1_filozofie": 7,
    }
    ok, msg = validate_part04_czu_value(row, "czu_1_filozofie", 6)
    assert not ok
    assert "66" in msg
    assert "59" in msg


def test_validate_part04_czu_value_allows_reduction_within_limit():
    row = {"total_imprumuturi": 17, "czu_5_matematica": 9, "czu_6_stiinte_aplicate": 7}
    ok, msg = validate_part04_czu_value(row, "czu_6_stiinte_aplicate", 5)
    assert ok
    assert msg == ""


def test_validate_part04_czu_value_accepts_within_limit():
    row = {"total_imprumuturi": 17, "czu_5_matematica": 9}
    ok, msg = validate_part04_czu_value(row, "czu_6_stiinte_aplicate", 8)
    assert ok
    assert msg == ""


def test_part03_has_imprumut_data_detects_section():
    assert part03_has_imprumut_data({"consultare_pe_loc": 2})
    assert not part03_has_imprumut_data({"carti": 5})
    assert not part03_has_imprumut_data(None)


def test_part03_total_sums_din_care():
    assert part03_total({"consultare_pe_loc": 3, "imprumut_pe_loc": 2}) == 5
    assert part03_total({"total_imprumuturi": 12, "consultare_pe_loc": 3}) == 3
    assert part03_total(None) == 0


def test_apply_part04_totals_always_from_part03():
    rows = [{"data": "01.03", "czu_0_generalitati": 99, "czu_1_filozofie": 99}]
    p3 = {"01.03": {"total_imprumuturi": 10, "consultare_pe_loc": 10}}
    apply_part04_totals(rows, p3)
    assert rows[0]["total_imprumuturi"] == 10
    assert rows[0]["_sync_total_from_part03"] is True


def test_apply_part04_totals_sums_czu_when_part03_missing():
    from core.part_sync import part04_row_total

    rows = [{"data": "02.03", "czu_0_generalitati": 3, "czu_1_filozofie": 4}]
    apply_part04_totals(rows, {})
    assert rows[0]["total_imprumuturi"] == 7
    assert rows[0]["_sync_total_from_part03"] is False
    assert part04_row_total(rows[0], 0) == 7


def test_apply_part04_totals_sums_czu_when_part03_zero():
    rows = [{"data": "03.03", "czu_0_generalitati": 7, "czu_1_filozofie": 2}]
    p3 = {"03.03": {"total_imprumuturi": 0, "consultare_pe_loc": 0}}
    apply_part04_totals(rows, p3)
    assert rows[0]["total_imprumuturi"] == 9
    assert rows[0]["_sync_total_from_part03"] is False


def test_rebalance_part04_czu_scales_to_total():
    from core.part_sync import rebalance_part04_czu_to_total

    row = {
        "total_imprumuturi": 70,
        "czu_0_generalitati": 50,
        "czu_1_filozofie": 50,
        "czu_2_religie": 21,
    }
    assert rebalance_part04_czu_to_total(row)
    assert sum(row[k] for k in (
        "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie",
        "czu_3_stiinte_sociale", "czu_5_matematica", "czu_6_stiinte_aplicate",
        "czu_7_arte", "czu_8_limbi", "czu_9_geografie",
    )) == 70


def test_rebalance_part04_czu_skips_when_within_total():
    from core.part_sync import rebalance_part04_czu_to_total

    row = {"total_imprumuturi": 70, "czu_0_generalitati": 30, "czu_1_filozofie": 40}
    assert not rebalance_part04_czu_to_total(row)
    assert row["czu_0_generalitati"] == 30


def test_validate_part04_czu_accepts_after_rebalance():
    from core.part_sync import rebalance_part04_czu_to_total, validate_part04_czu_value

    row = {
        "total_imprumuturi": 70,
        "czu_0_generalitati": 40,
        "czu_1_filozofie": 50,
        "czu_2_religie": 31,
    }
    rebalance_part04_czu_to_total(row)
    ok, msg = validate_part04_czu_value(row, "czu_1_filozofie", row["czu_1_filozofie"] + 1)
    assert not ok
    ok, msg = validate_part04_czu_value(row, "czu_1_filozofie", max(0, row["czu_1_filozofie"] - 1))
    assert ok


def test_load_part03_with_live_cache_prefers_unsaved_table_rows():
    from core.part_sync import load_part03_with_live_cache

    class FakeTable:
        def get_data_rows(self):
            return [{"data": "05.05", "consultare_pe_loc": 22, "total_imprumuturi": 22}]

    class FakePart03:
        year = 2026
        month = 5
        has_copii_adulti = True
        table_adulti = FakeTable()
        table_copii = FakeTable()

    class FakeWindow:
        _loaded_parts = {"part_03"}
        _part_pages = {"part_03": FakePart03()}

    merged = load_part03_with_live_cache(FakeWindow(), "adulti", 2026, 5)
    assert merged["05.05"]["consultare_pe_loc"] == 22
    assert part03_total(merged["05.05"]) == 22


def test_load_part03_with_live_cache_ignores_unloaded_placeholder():
    from core.part_sync import load_part03_with_live_cache

    class FakePlaceholder:
        pass

    class FakeWindow:
        _loaded_parts: set[str] = set()
        _part_pages = {"part_03": FakePlaceholder()}

    merged = load_part03_with_live_cache(FakeWindow(), "adulti", 2026, 5)
    assert isinstance(merged, dict)


def test_load_part03_with_live_cache_skips_placeholder_even_if_marked_loaded():
    from core.part_sync import load_part03_with_live_cache

    class FakePlaceholder:
        pass

    class FakeWindow:
        _loaded_parts = {"part_03"}
        _part_pages = {"part_03": FakePlaceholder()}

    merged = load_part03_with_live_cache(FakeWindow(), "adulti", 2026, 5)
    assert isinstance(merged, dict)


def test_validate_part04_czu_allows_entry_when_total_zero():
    ok, msg = validate_part04_czu_value(
        {"total_imprumuturi": 0}, "czu_3_stiinte_sociale", 5
    )
    assert ok
    assert msg == ""


def test_rebalance_preserves_czu_when_total_zero():
    from core.part_sync import rebalance_part04_czu_to_total

    row = {
        "total_imprumuturi": 0,
        "czu_0_generalitati": 12,
        "czu_1_filozofie": 8,
    }
    assert not rebalance_part04_czu_to_total(row)
    assert row["czu_0_generalitati"] == 12
    assert row["czu_1_filozofie"] == 8


def test_invalidate_part04_refreshes_totals_when_dirty():
    from core.part_sync import invalidate_part04_cache_if_loaded

    class FakePage:
        reloaded = False
        totals_refreshed = False

        def has_unsaved_changes(self):
            return True

        def refresh_totals_from_part03(self):
            self.totals_refreshed = True

        def _invalidate_caches(self):
            raise AssertionError("should not invalidate when dirty")

        def _load_current(self, fast=False):
            self.reloaded = True

    class FakeWindow:
        _loaded_parts = {"part_04"}
        _part_pages = {"part_04": FakePage()}

    invalidate_part04_cache_if_loaded(FakeWindow())
    page = FakeWindow._part_pages["part_04"]
    assert page.totals_refreshed
    assert not page.reloaded


def test_load_part03_with_live_cache_uses_data_cache_for_other_month():
    from core.part_sync import load_part03_with_live_cache

    class FakePart03:
        year = 2026
        month = 6
        has_copii_adulti = True

        def _cache_key(self, year, month, categorie):
            return (year, month, categorie)

        _data_cache = {
            (2026, 5, "adulti"): {
                "rows": [{"data": "05.05", "consultare_pe_loc": 33, "total_imprumuturi": 33}]
            }
        }

    class FakeWindow:
        _loaded_parts = {"part_03"}
        _part_pages = {"part_03": FakePart03()}

    merged = load_part03_with_live_cache(FakeWindow(), "adulti", 2026, 5)
    assert merged["05.05"]["consultare_pe_loc"] == 33


def test_sync_part04_row_total_and_align_rebalances_on_lower_total():
    from core.part_sync import sync_part04_row_total_and_align

    row = {
        "total_imprumuturi": 50,
        "czu_0_generalitati": 20,
        "czu_1_filozofie": 20,
        "czu_2_religie": 20,
    }
    changed = sync_part04_row_total_and_align(row, 30)
    assert changed
    assert row["total_imprumuturi"] == 30
    assert sum(row.get(k, 0) for k in (
        "czu_0_generalitati", "czu_1_filozofie", "czu_2_religie"
    )) <= 30


def test_validate_part04_allows_edit_after_total_drops():
    from core.part_sync import rebalance_part04_czu_to_total, validate_part04_czu_value

    row = {
        "total_imprumuturi": 30,
        "czu_0_generalitati": 20,
        "czu_1_filozofie": 20,
        "czu_2_religie": 10,
    }
    rebalance_part04_czu_to_total(row)
    ok, _ = validate_part04_czu_value(row, "czu_0_generalitati", 5)
    assert ok


def test_part04_total_for_date_uses_live_part03(monkeypatch):
    from core.part_sync import part04_total_for_date

    monkeypatch.setattr(
        "core.part_sync.load_part03_with_live_cache",
        lambda mw, cat, y, m: {"02.09": {"total_imprumuturi": 15, "consultare_pe_loc": 15}},
    )
    assert part04_total_for_date(object(), "adulti", 2026, 9, "02.09") == 15
    assert part04_total_for_date(object(), "adulti", 2026, 9, "99.09") == 0


def test_part04_prepare_cache_syncs_total_from_part03(monkeypatch):
    from ui.part_04_documente_continut import Part04Page, COLUMNS

    page = Part04Page.__new__(Part04Page)
    page.part_id = "part_04"
    page.columns = COLUMNS
    page._loaded_year = 2026
    page._loaded_month = 3
    page._has_month_bar = True
    page.main_window = object()
    page._data_cache = {}

    monkeypatch.setattr(
        page,
        "_fetch_table_data",
        lambda categorie: {
            "rows": [{"data": "01.03", "total_imprumuturi": 99, "czu_0_generalitati": 1}],
            "ids": [1],
            "flags": [False],
            "db_empty": False,
        },
    )
    monkeypatch.setattr(
        "core.part_sync.load_part03_with_live_cache",
        lambda mw, cat, y, m: {"01.03": {"total_imprumuturi": 12, "consultare_pe_loc": 12}},
    )

    page._prepare_part04_cache("adulti")
    rows = page._data_cache[(2026, 3, "adulti")]["rows"]
    assert rows[0]["total_imprumuturi"] == 12
    assert rows[0]["czu_0_generalitati"] == 1


def test_sync_part04_rows_from_part03_applies_part03_total(monkeypatch):
    from core.part_sync import sync_part04_rows_from_part03

    rows = [{"data": "05.06", "total_imprumuturi": 0, "czu_0_generalitati": 3}]
    monkeypatch.setattr(
        "core.part_sync.load_part03_with_live_cache",
        lambda mw, cat, y, m: {"05.06": {"total_imprumuturi": 22, "consultare_pe_loc": 22}},
    )
    sync_part04_rows_from_part03(rows, object(), "adulti", 2026, 6)
    assert rows[0]["total_imprumuturi"] == 22


def test_merge_daily_rows_fills_missing_working_days(monkeypatch):
    from ui.parts.part_page_base import PartPageBase
    from ui.widgets.editable_table import ColumnDef

    class StubDaily(PartPageBase):
        pass

    page = StubDaily.__new__(StubDaily)
    page.mode = "daily"
    page.date_field = "data"
    page.columns = [ColumnDef("data", "date"), ColumnDef("total_imprumuturi", "int")]
    page._loaded_year = 2026
    page._loaded_month = 6
    page.show_month = True
    page.part_id = "part_03"
    monkeypatch.setattr(
        page,
        "_working_days",
        lambda year=None, month=None: [
            "01.06", "02.06", "03.06", "04.06", "05.06", "08.06", "09.06",
        ],
    )

    existing = [{"data": "03.06", "total_imprumuturi": 7}]
    merged, ids, flags = page._merge_daily_rows(existing, [1], [False], "adulti", 2026, 6)
    dates = [r["data"] for r in merged]
    assert "01.06" in dates
    assert "03.06" in dates
    assert dates.index("01.06") < dates.index("03.06")
    row_03 = next(r for r in merged if r["data"] == "03.06")
    assert row_03["total_imprumuturi"] == 7
    assert ids[dates.index("03.06")] == 1


def test_merge_daily_rows_drops_excluded_dates(monkeypatch):
    from ui.parts.part_page_base import PartPageBase
    from ui.widgets.editable_table import ColumnDef

    class StubDaily(PartPageBase):
        pass

    page = StubDaily.__new__(StubDaily)
    page.mode = "daily"
    page.date_field = "data"
    page.columns = [ColumnDef("data", "date"), ColumnDef("total_imprumuturi", "int")]
    page._loaded_year = 2026
    page._loaded_month = 6
    page.show_month = True
    page.part_id = "part_04"
    monkeypatch.setattr(
        page,
        "_working_days",
        lambda year=None, month=None: ["02.06", "03.06"],
    )

    existing = [
        {"data": "01.06", "total_imprumuturi": 17},
        {"data": "03.06", "total_imprumuturi": 9},
    ]
    merged, ids, flags = page._merge_daily_rows(existing, [10, 11], [False, False], None, 2026, 6)
    dates = [r["data"] for r in merged]
    assert "01.06" not in dates
    assert dates == ["02.06", "03.06"]
    assert merged[1]["total_imprumuturi"] == 9
    assert ids[1] == 11


def test_load_current_fast_loads_both_copii_adulti_tables():
    from ui.parts.mixins.cache_mixin import PartCacheMixin

    calls: list[tuple] = []

    class Page(PartCacheMixin):
        has_copii_adulti = True
        table_copii = "copii_table"
        table_adulti = "adulti_table"

        def _load_table(self, table, cat, fast=False):
            calls.append((table, cat, fast))

        def _schedule_preload_adjacent(self):
            pass

    Page()._load_current(fast=True)
    assert calls == [
        ("copii_table", "copii", True),
        ("adulti_table", "adulti", True),
    ]


def test_excluded_days_dialog_returns_saved_year(qtbot, monkeypatch):
    from ui.excluded_days_dialog import ExcludedDaysDialog

    monkeypatch.setattr(
        "ui.excluded_days_dialog.get_excluded_days_for_year",
        lambda _year: {},
    )
    monkeypatch.setattr(
        "ui.excluded_days_dialog.set_excluded_days_for_year",
        lambda _year, _by_month: None,
    )

    dlg = ExcludedDaysDialog(default_year=2025)
    qtbot.addWidget(dlg)
    dlg._year.setValue(2024)
    dlg._save()
    assert dlg.saved_year() == 2024
