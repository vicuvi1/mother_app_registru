"""Teste sincronizare Partea II ↔ Părțile IX și XI."""

from core.part02_cross_sync import (
    PART02_ACTIVITATI,
    PART02_INSTRUIRI,
    PART09_TOTAL,
    PART11_TOTAL,
    _redistribute_event_totals,
    _sum_events_by_date,
    apply_part02_cross_sync_rows,
    cross_sync_guard,
    on_part02_field_changed,
    on_part09_total_changed,
    set_part09_total_for_date,
    set_part11_total_for_date,
    sync_part02_instruiri_for_category,
    sync_part02_instruiri_to_both_categories,
)


def test_sum_events_by_date():
    rows = [
        {"data": "05.06", PART09_TOTAL: 10},
        {"data": "05.06", PART09_TOTAL: 5},
        {"data": "08.06", PART09_TOTAL: 3},
    ]
    assert _sum_events_by_date(rows, PART09_TOTAL) == {"05.06": 15, "08.06": 3}


def test_apply_part02_cross_sync_rows():
    rows = [
        {"data": "05.06", PART02_INSTRUIRI: 0, PART02_ACTIVITATI: 0},
        {"data": "08.06", PART02_INSTRUIRI: 1, PART02_ACTIVITATI: 2},
    ]
    changed = apply_part02_cross_sync_rows(
        rows,
        {"05.06": 15, "08.06": 15},
        {"05.06": 7},
    )
    assert changed == 3
    assert rows[0][PART02_INSTRUIRI] == 15
    assert rows[0][PART02_ACTIVITATI] == 7
    assert rows[1][PART02_INSTRUIRI] == 15
    assert rows[1][PART02_ACTIVITATI] == 2


def test_redistribute_event_totals():
    rows = [
        {"data": "05.06", PART09_TOTAL: 3},
        {"data": "05.06", PART09_TOTAL: 7},
        {"data": "08.06", PART09_TOTAL: 1},
    ]
    assert _redistribute_event_totals(rows, "05.06", 20, PART09_TOTAL)
    assert rows[0][PART09_TOTAL] == 20
    assert rows[1][PART09_TOTAL] == 0
    assert rows[2][PART09_TOTAL] == 1


class _FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = [dict(r) for r in rows]

    def get_data_rows(self) -> list[dict]:
        return self._rows

    def set_data_cell_silent(self, data_row: int, key: str, value) -> bool:
        self._rows[data_row][key] = value
        return True

    def load_rows(self, rows, ids, flags, resize=False, resize_rows=True) -> None:
        self._rows = [dict(r) for r in rows]


class _FakePart02Page:
    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.part_id = "part_02"
        self.year = 2026
        self.month = 6
        self._loaded_year = 2026
        self._loaded_month = 6
        self.has_copii_adulti = True
        self.table_adulti = _FakeTable(
            [{"data": "05.06", PART02_INSTRUIRI: 0, PART02_ACTIVITATI: 0}]
        )
        self.table_copii = _FakeTable(
            [{"data": "05.06", PART02_INSTRUIRI: 0, PART02_ACTIVITATI: 0}]
        )
        self._data_cache = {
            "2026|6|adulti": {
                "rows": [{"data": "05.06", PART02_INSTRUIRI: 0, PART02_ACTIVITATI: 0}],
                "ids": [1],
                "flags": [False],
            },
            "2026|6|copii": {
                "rows": [{"data": "05.06", PART02_INSTRUIRI: 0, PART02_ACTIVITATI: 0}],
                "ids": [2],
                "flags": [False],
            },
        }

    def _cache_key(self, categorie=None):
        return f"{self.year}|{self.month}|{categorie}"

    def _recompute_visible_totals(self) -> None:
        pass


class _FakePart09Page:
    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.part_id = "part_09"
        self.year = 2026
        self.month = 6
        self.has_copii_adulti = True
        self.table_adulti = _FakeTable(
            [
                {"data": "05.06", PART09_TOTAL: 10},
                {"data": "05.06", PART09_TOTAL: 5},
            ]
        )
        self.table_copii = _FakeTable([{"data": "05.06", PART09_TOTAL: 0}])
        self._data_cache = {
            "2026|6|adulti": {
                "rows": [
                    {"data": "05.06", PART09_TOTAL: 10},
                    {"data": "05.06", PART09_TOTAL: 5},
                ],
                "ids": [1, 2],
                "flags": [False, False],
            },
            "2026|6|copii": {
                "rows": [{"data": "05.06", PART09_TOTAL: 0}],
                "ids": [3],
                "flags": [False],
            },
        }

    def _cache_key(self, categorie=None):
        return f"{self.year}|{self.month}|{categorie}"

    def _recompute_visible_totals(self) -> None:
        pass


class _FakePart11Page:
    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.part_id = "part_11"
        self.year = 2026
        self.month = 6
        self.has_copii_adulti = True
        self.table_adulti = _FakeTable([{"data": "16.06", PART11_TOTAL: 0}])
        self.table_copii = _FakeTable([{"data": "16.06", PART11_TOTAL: 0}])
        self._data_cache = {
            "2026|6|adulti": {
                "rows": [{"data": "16.06", PART11_TOTAL: 0}],
                "ids": [1],
                "flags": [False],
            },
            "2026|6|copii": {
                "rows": [{"data": "16.06", PART11_TOTAL: 0}],
                "ids": [2],
                "flags": [False],
            },
        }

    def _cache_key(self, categorie=None):
        return f"{self.year}|{self.month}|{categorie}"

    def _recompute_visible_totals(self) -> None:
        pass


class _FakeMainWindow:
    def __init__(self) -> None:
        self._cross_sync_depth = 0
        self._loaded_parts = {"part_02", "part_09", "part_11"}
        p02 = _FakePart02Page(self)
        p09 = _FakePart09Page(self)
        p11 = _FakePart11Page(self)
        self._part_pages = {
            "part_02": p02,
            "part_09": p09,
            "part_11": p11,
        }


def test_on_part09_total_changed_sums_into_part02_adulti_only():
    mw = _FakeMainWindow()
    p09 = mw._part_pages["part_09"]
    on_part09_total_changed(mw, p09, "adulti", "05.06")
    p02 = mw._part_pages["part_02"]
    assert p02.table_adulti.get_data_rows()[0][PART02_INSTRUIRI] == 15
    assert p02.table_copii.get_data_rows()[0][PART02_INSTRUIRI] == 0


def test_on_part02_field_changed_updates_part09_adulti():
    mw = _FakeMainWindow()
    p02 = mw._part_pages["part_02"]
    on_part02_field_changed(mw, p02, "adulti", "05.06", PART02_INSTRUIRI, 20)
    p09 = mw._part_pages["part_09"]
    rows = p09.table_adulti.get_data_rows()
    assert rows[0][PART09_TOTAL] == 20
    assert rows[1][PART09_TOTAL] == 0


def test_set_part11_total_for_date_creates_row():
    mw = _FakeMainWindow()
    assert set_part11_total_for_date(mw, 2026, 6, "adulti", "24.06", 8)
    p11 = mw._part_pages["part_11"]
    rows = p11.table_adulti.get_data_rows()
    match = [r for r in rows if r.get("data") == "24.06"]
    assert match and match[0][PART11_TOTAL] == 8


def test_cross_sync_guard_prevents_reentry():
    mw = _FakeMainWindow()
    with cross_sync_guard(mw):
        assert mw._cross_sync_depth == 1
    assert mw._cross_sync_depth == 0


def test_sync_part02_instruiri_for_category():
    mw = _FakeMainWindow()
    sync_part02_instruiri_for_category(mw, 2026, 6, "copii", "05.06", 42)
    p02 = mw._part_pages["part_02"]
    assert p02.table_copii.get_data_rows()[0][PART02_INSTRUIRI] == 42
    assert p02.table_adulti.get_data_rows()[0][PART02_INSTRUIRI] == 0


def test_sync_part02_instruiri_to_both_categories():
    mw = _FakeMainWindow()
    sync_part02_instruiri_to_both_categories(mw, 2026, 6, "05.06", 42)
    p02 = mw._part_pages["part_02"]
    assert p02.table_adulti.get_data_rows()[0][PART02_INSTRUIRI] == 42
    assert p02.table_copii.get_data_rows()[0][PART02_INSTRUIRI] == 42


def test_set_part09_total_for_date_creates_row():
    mw = _FakeMainWindow()
    p09 = mw._part_pages["part_09"]
    p09._data_cache["2026|6|copii"]["rows"] = []
    p09.table_copii._rows = []
    assert set_part09_total_for_date(mw, 2026, 6, "copii", "10.06", 7)
    rows = p09.table_copii.get_data_rows()
    assert len(rows) == 1
    assert rows[0]["data"] == "10.06"
    assert rows[0][PART09_TOTAL] == 7
