"""Sincronizare Partea II ↔ Părțile IX (instruiri) și XI (activități culturale)."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from typing import Any

from sqlalchemy import and_, select

from database.db_manager import get_session
from database.models import ActivitatiCulturale, Instruiri

PART02_INSTRUIRI = "instruiri"
PART02_ACTIVITATI = "activitati_culturale_stiintifice"
PART09_TOTAL = "total_participanti"
PART11_TOTAL = "total_participanti"


@contextmanager
def cross_sync_guard(main_window: Any):
    """Evită bucle la sincronizare bidirecțională."""
    depth = getattr(main_window, "_cross_sync_depth", 0)
    main_window._cross_sync_depth = depth + 1
    try:
        yield
    finally:
        main_window._cross_sync_depth = max(0, getattr(main_window, "_cross_sync_depth", 1) - 1)


def cross_sync_active(main_window: Any) -> bool:
    return getattr(main_window, "_cross_sync_depth", 0) > 0


def _resolve_page(main_window: Any, part_id: str) -> Any | None:
    if main_window is None:
        return None
    loaded = getattr(main_window, "_loaded_parts", None)
    if not loaded or part_id not in loaded:
        return None
    page = getattr(main_window, "_part_pages", {}).get(part_id)
    if page is None or not hasattr(page, "year"):
        return None
    return page


def _sum_events_by_date(
    rows: list[dict[str, Any]],
    value_key: str,
    *,
    date_key: str = "data",
) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        date = row.get(date_key)
        if not date:
            continue
        totals[str(date)] += max(0, int(row.get(value_key) or 0))
    return dict(totals)


def _rows_from_page_cache(page: Any, categorie: str | None) -> list[dict[str, Any]]:
    if not hasattr(page, "_data_cache") or not hasattr(page, "_cache_key"):
        return []
    key = page._cache_key(categorie=categorie)
    cached = page._data_cache.get(key)
    if not cached:
        return []
    return [dict(r) for r in cached.get("rows") or []]


def _live_event_rows(page: Any, categorie: str | None) -> list[dict[str, Any]]:
    if page is None:
        return []
    if getattr(page, "has_copii_adulti", False):
        table = page.table_adulti if categorie == "adulti" else page.table_copii
    else:
        table = getattr(page, "table", None)
    if table is None or not hasattr(table, "get_data_rows"):
        return []
    return [dict(r) for r in table.get_data_rows()]


def load_part09_totals_by_date(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
) -> dict[str, int]:
    """Sumă total participanți instruiri pe dată și categorie (cache live + DB)."""
    page = _resolve_page(main_window, "part_09")
    if page is not None and page.year == year and page.month == month:
        live = _live_event_rows(page, categorie)
        if live:
            return _sum_events_by_date(live, PART09_TOTAL)
        cached = _rows_from_page_cache(page, categorie)
        if cached:
            return _sum_events_by_date(cached, PART09_TOTAL)

    with get_session() as session:
        rows = session.scalars(
            select(Instruiri).where(
                and_(
                    Instruiri.an == year,
                    Instruiri.luna == month,
                    Instruiri.categorie_varsta == categorie,
                )
            )
        ).all()
    return _sum_events_by_date(
        [
            {
                "data": r.data,
                PART09_TOTAL: r.total_participanti,
            }
            for r in rows
        ],
        PART09_TOTAL,
    )


def load_part11_totals_by_date(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
) -> dict[str, int]:
    """Sumă total participanți activități culturale pe dată și categorie."""
    with get_session() as session:
        rows = session.scalars(
            select(ActivitatiCulturale).where(
                and_(
                    ActivitatiCulturale.an == year,
                    ActivitatiCulturale.luna == month,
                    ActivitatiCulturale.categorie_varsta == categorie,
                )
            )
        ).all()
    by_date = _sum_events_by_date(
        [
            {
                "data": r.data,
                PART11_TOTAL: r.total_participanti,
            }
            for r in rows
            if r.data
        ],
        PART11_TOTAL,
    )

    page = _resolve_page(main_window, "part_11")
    if page is not None and page.year == year and page.month == month:
        live = _live_event_rows(page, categorie)
        if live:
            by_date = _sum_events_by_date(live, PART11_TOTAL)
    elif page is not None:
        cached = _rows_from_page_cache(page, categorie)
        if cached:
            by_date = _sum_events_by_date(cached, PART11_TOTAL)

    return by_date


def apply_part02_cross_sync_rows(
    rows: list[dict[str, Any]],
    instruiri_by_date: dict[str, int],
    activitati_by_date: dict[str, int],
) -> int:
    """Actualizează coloanele Partea II din sumele pe dată. Returnează rânduri modificate."""
    changed = 0
    for row in rows:
        date = row.get("data")
        if not date:
            continue
        if date in instruiri_by_date:
            val = instruiri_by_date[date]
            if int(row.get(PART02_INSTRUIRI) or 0) != val:
                row[PART02_INSTRUIRI] = val
                changed += 1
        if date in activitati_by_date:
            val = activitati_by_date[date]
            if int(row.get(PART02_ACTIVITATI) or 0) != val:
                row[PART02_ACTIVITATI] = val
                changed += 1
    return changed


def _apply_computed_part02_row(table: Any, data_row: int) -> None:
    store = getattr(getattr(table, "_register_model", None), "store", None)
    if store is not None and hasattr(store, "apply_computed_row"):
        store.apply_computed_row(data_row)
        if hasattr(table, "_register_model"):
            top_left = table._register_model.index(data_row, 0)
            bottom_right = table._register_model.index(
                data_row, table._register_model.columnCount() - 1
            )
            table._register_model.dataChanged.emit(top_left, bottom_right)


def _set_part02_cell(
    page: Any,
    categorie: str,
    date: str,
    field: str,
    value: int,
) -> bool:
    key = page._cache_key(categorie=categorie)
    cached = page._data_cache.get(key)
    if cached is None:
        return False
    changed = False
    for row in cached.get("rows") or []:
        if row.get("data") == date:
            if int(row.get(field) or 0) != value:
                row[field] = value
                changed = True
    if not changed and page.year == page._loaded_year and page.month == page._loaded_month:
        pass

    table = page.table_adulti if categorie == "adulti" else page.table_copii
    if page.year != page._loaded_year or page.month != page._loaded_month:
        return changed
    for i, row in enumerate(table.get_data_rows()):
        if row.get("data") == date:
            if int(row.get(field) or 0) != value:
                table.set_data_cell_silent(i, field, value)
                _apply_computed_part02_row(table, i)
                changed = True
    return changed


def sync_part02_from_ix_xi(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
) -> bool:
    """Partea II ← sume IX/XI pentru categoria dată."""
    page = _resolve_page(main_window, "part_02")
    if page is None or page.year != year or page.month != month:
        return False

    instruiri = load_part09_totals_by_date(main_window, year, month, categorie)
    activitati = load_part11_totals_by_date(main_window, year, month, categorie)

    key = page._cache_key(categorie=categorie)
    cached = page._data_cache.get(key)
    if cached is None:
        return False
    rows = [dict(r) for r in cached.get("rows") or []]
    apply_part02_cross_sync_rows(rows, instruiri, activitati)
    page._data_cache[key] = {**cached, "rows": rows}

    if not instruiri and not activitati:
        return False

    table = page.table_adulti if categorie == "adulti" else page.table_copii
    for i, row in enumerate(rows):
        date = row.get("data")
        if not date:
            continue
        if date in instruiri:
            table.set_data_cell_silent(i, PART02_INSTRUIRI, instruiri[date])
            _apply_computed_part02_row(table, i)
        if date in activitati:
            table.set_data_cell_silent(i, PART02_ACTIVITATI, activitati[date])
            _apply_computed_part02_row(table, i)
    if hasattr(page, "_recompute_visible_totals"):
        page._recompute_visible_totals()
    return True


def sync_part02_instruiri_for_category(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
    date: str,
    value: int,
) -> None:
    """Partea IX pe categorie — total instruiri în Partea II (același tab)."""
    page = _resolve_page(main_window, "part_02")
    if page is None or page.year != year or page.month != month:
        return
    _set_part02_cell(page, categorie, date, PART02_INSTRUIRI, value)


def sync_part02_instruiri_to_both_categories(
    main_window: Any,
    year: int,
    month: int,
    date: str,
    value: int,
) -> None:
    """Compatibilitate — preferă sync_part02_instruiri_for_category."""
    for cat in ("adulti", "copii"):
        sync_part02_instruiri_for_category(main_window, year, month, cat, date, value)


def sync_part02_activitati_for_category(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
    date: str,
    value: int,
) -> None:
    page = _resolve_page(main_window, "part_02")
    if page is not None:
        _set_part02_cell(page, categorie, date, PART02_ACTIVITATI, value)


def _redistribute_event_totals(
    rows: list[dict[str, Any]],
    date: str,
    target_sum: int,
    value_key: str,
) -> bool:
    """Pune totalul țintă pe primul rând al zilei; celelalte rânduri → 0."""
    indices = [i for i, r in enumerate(rows) if r.get("data") == date]
    if not indices:
        return False
    target_sum = max(0, int(target_sum))
    changed = False
    for pos, i in enumerate(indices):
        new_val = target_sum if pos == 0 else 0
        if int(rows[i].get(value_key) or 0) != new_val:
            rows[i][value_key] = new_val
            changed = True
    return changed


def _push_rows_to_event_table(page: Any, categorie: str | None, rows: list[dict]) -> None:
    if getattr(page, "has_copii_adulti", False):
        table = page.table_adulti if categorie == "adulti" else page.table_copii
    else:
        table = page.table
    ids = page._data_cache.get(page._cache_key(categorie=categorie), {}).get("ids", [])
    flags = page._data_cache.get(page._cache_key(categorie=categorie), {}).get("flags", [])
    table.load_rows(rows, ids, flags, resize=False, resize_rows=True)
    if hasattr(page, "_recompute_visible_totals"):
        page._recompute_visible_totals()


def set_part09_total_for_date(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
    date: str,
    target_sum: int,
) -> bool:
    """Partea II → IX: total participanți pe dată și categorie."""
    page = _resolve_page(main_window, "part_09")
    if page is None or page.year != year or page.month != month:
        return False
    key = page._cache_key(categorie=categorie)
    cached = page._data_cache.get(key)
    if cached is None:
        return False
    rows = [dict(r) for r in cached.get("rows") or []]
    indices = [i for i, r in enumerate(rows) if r.get("data") == date]
    if not indices:
        base = {
            "data": date,
            PART09_TOTAL: max(0, int(target_sum)),
            "format_online": False,
            "format_offline": False,
            "forma_formala": False,
            "ore_formala": 0,
            "forma_non_formala": False,
            "ore_non_formala": 0,
            "forma_informala": False,
            "ore_informala": 0,
            "tema_instruirii": "",
            "formator": "",
            "participanti_feminin": 0,
            "participanti_masculin": 0,
        }
        if categorie == "copii":
            base.update({"prescolari": 0, "elevi": 0})
        else:
            base.update(
                {
                    "studenti": 0,
                    "intelectuali": 0,
                    "pensionari": 0,
                    "someri": 0,
                    "muncitori": 0,
                    "alte_categorii": 0,
                    "tineri_17_34": 0,
                    "adulti_35_64": 0,
                    "varstnici_65_plus": 0,
                }
            )
        rows.append(base)
        cached["ids"] = list(cached.get("ids") or []) + [None]
        cached["flags"] = list(cached.get("flags") or []) + [False]
        changed = True
    else:
        changed = _redistribute_event_totals(rows, date, target_sum, PART09_TOTAL)
    if not changed:
        return False
    page._data_cache[key] = {**cached, "rows": rows}
    _push_rows_to_event_table(page, categorie, rows)
    return True


def set_part11_total_for_date(
    main_window: Any,
    year: int,
    month: int,
    categorie: str,
    date: str,
    target_sum: int,
) -> bool:
    page = _resolve_page(main_window, "part_11")
    if page is None or page.year != year or page.month != month:
        return False
    key = page._cache_key(categorie=categorie)
    cached = page._data_cache.get(key)
    if cached is None:
        return False
    rows = [dict(r) for r in cached.get("rows") or []]
    indices = [i for i, r in enumerate(rows) if r.get("data") == date]
    if not indices:
        rows.append(
            {
                "data": date,
                "total_activitati": 1,
                "din_care_expozitii": 0,
                "tipul_activitatii": "",
                "denumirea_activitatii": "",
                PART11_TOTAL: max(0, int(target_sum)),
                "participanti_masculin": 0,
                "participanti_feminin": 0,
                "categorie_varsta": categorie,
            }
        )
        cached["ids"] = list(cached.get("ids") or []) + [None]
        cached["flags"] = list(cached.get("flags") or []) + [False]
        changed = True
    else:
        changed = _redistribute_event_totals(rows, date, target_sum, PART11_TOTAL)
    if not changed:
        return False
    page._data_cache[key] = {**cached, "rows": rows}
    _push_rows_to_event_table(page, categorie, rows)
    return True


def sync_part02_from_events_for_page(page: Any) -> None:
    """Reîmprospătează Partea II din IX/XI pentru categoria activă."""
    if page is None:
        return
    categorie = page._active_category() if hasattr(page, "_active_category") else "adulti"
    sync_part02_from_ix_xi(page.main_window, page.year, page.month, categorie)


def on_part09_total_changed(
    main_window: Any, page: Any, categorie: str, date: str
) -> None:
    if not date or cross_sync_active(main_window):
        return
    with cross_sync_guard(main_window):
        totals = load_part09_totals_by_date(
            main_window, page.year, page.month, categorie
        )
        value = totals.get(date, 0)
        sync_part02_instruiri_for_category(
            main_window, page.year, page.month, categorie, date, value
        )
        part02 = _resolve_page(main_window, "part_02")
        if part02 is not None and hasattr(part02, "_recompute_visible_totals"):
            part02._recompute_visible_totals()


def on_part11_total_changed(
    main_window: Any, page: Any, categorie: str, date: str
) -> None:
    if not date or cross_sync_active(main_window):
        return
    with cross_sync_guard(main_window):
        totals = load_part11_totals_by_date(
            main_window, page.year, page.month, categorie
        )
        value = totals.get(date, 0)
        p02 = _resolve_page(main_window, "part_02")
        if p02 is not None:
            _set_part02_cell(p02, categorie, date, PART02_ACTIVITATI, value)
            if hasattr(p02, "_recompute_visible_totals"):
                p02._recompute_visible_totals()


def on_part02_field_changed(
    main_window: Any,
    page: Any,
    categorie: str,
    date: str,
    field: str,
    value: int,
) -> None:
    if not date or cross_sync_active(main_window):
        return
    with cross_sync_guard(main_window):
        if field == PART02_INSTRUIRI:
            set_part09_total_for_date(
                main_window, page.year, page.month, categorie, date, value
            )
            sync_part02_instruiri_for_category(
                main_window, page.year, page.month, categorie, date, value
            )
        elif field == PART02_ACTIVITATI:
            set_part11_total_for_date(
                main_window, page.year, page.month, categorie, date, value
            )
            p02 = _resolve_page(main_window, "part_02")
            if p02 is not None:
                _set_part02_cell(p02, categorie, date, PART02_ACTIVITATI, value)
                if hasattr(p02, "_recompute_visible_totals"):
                    p02._recompute_visible_totals()
