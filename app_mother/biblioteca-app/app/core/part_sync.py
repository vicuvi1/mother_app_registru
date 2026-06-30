"""Sincronizare date între Părți ale registrului."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, select

from core.constants_manager import get_excluded_days
from core.date_engine import get_working_days
from database.db_manager import get_session
from database.models import DocumenteContinutCZU, DocumenteInregistrate

PART03_IMPRUMUT_KEYS = (
    "total_imprumuturi",
    "consultare_pe_loc",
    "imprumut_pe_loc",
    "imprumut_la_domiciliu",
    "imprumut_inter_bibliotecar",
)
PART03_DIN_CARE = PART03_IMPRUMUT_KEYS[1:]
PART03_MIRROR_FIELDS = ("carti", "limba_romana")
PART03_MIRROR_OVERRIDE = {
    "carti": "_override_part03_carti",
    "limba_romana": "_override_part03_limba_romana",
}


def part03_has_imprumut_data(row: dict[str, Any] | None) -> bool:
    """True dacă Partea III are date în secțiunea total împrumuturi."""
    if not row:
        return False
    return any(int(row.get(k) or 0) > 0 for k in PART03_IMPRUMUT_KEYS)


def part03_row_total(row: dict[str, Any] | None) -> int:
    """Total împrumuturi afișat pe rând (suma „Din care”)."""
    if not row:
        return 0
    stored = row.get("total_imprumuturi")
    if stored is not None and str(stored).strip() != "":
        return max(0, int(stored))
    return part03_total(row)


def apply_part03_default_mirrors(row: dict[str, Any]) -> None:
    """La generare automată: cărți și limba română = total împrumuturi."""
    total = part03_row_total(row)
    row["carti"] = total
    row["limba_romana"] = total


def init_part03_mirror_overrides(table) -> None:
    """Marchează doar corecțiile explicite (valoare nenulă, diferită de total)."""
    for i, row in enumerate(table.get_data_rows()):
        total = part03_row_total(row)
        for field, flag in PART03_MIRROR_OVERRIDE.items():
            val = int(row.get(field) or 0)
            if val != total and val != 0:
                table.set_row_extra(i, flag, True)


def apply_part03_mirrors(table, data_row: int) -> list[str]:
    """Propagă totalul în cărți / limba română dacă nu au fost corectate manual."""
    rows = table.get_data_rows()
    if data_row < 0 or data_row >= len(rows):
        return []
    row = rows[data_row]
    total = part03_row_total(row)
    extra = (
        table.store.row_extra[data_row]
        if data_row < len(table.store.row_extra)
        else {}
    )
    updated: list[str] = []
    for field in PART03_MIRROR_FIELDS:
        if extra.get(PART03_MIRROR_OVERRIDE[field]):
            continue
        if int(row.get(field) or 0) == total:
            continue
        if hasattr(table, "set_data_cell_silent"):
            table.set_data_cell_silent(data_row, field, total)
        updated.append(field)
    return updated


def sync_part03_table_mirrors(table) -> bool:
    """Aplică total → cărți / limba română la încărcare (date vechi cu 0)."""
    init_part03_mirror_overrides(table)
    changed = False
    for i in range(len(table.get_data_rows())):
        if apply_part03_mirrors(table, i):
            changed = True
    return changed


def part03_total(row: dict[str, Any] | None) -> int:
    """Total împrumuturi pentru o zi — suma coloanelor „Din care” (ca în UI)."""
    if not row:
        return 0
    return sum(int(row.get(k) or 0) for k in PART03_IMPRUMUT_KEYS[1:])


def load_part03_by_date(
    categorie: str | None,
    year: int,
    month: int,
) -> dict[str, dict[str, Any]]:
    """Încarcă rândurile Părții III indexate după dată (DD.MM)."""
    with get_session() as session:
        filters = [
            DocumenteInregistrate.an == year,
            DocumenteInregistrate.luna == month,
        ]
        if categorie:
            filters.append(DocumenteInregistrate.categorie_varsta == categorie)
        rows = session.scalars(
            select(DocumenteInregistrate).where(and_(*filters)).order_by(DocumenteInregistrate.data)
        ).all()

    by_date: dict[str, dict[str, Any]] = {}
    for rec in rows:
        d = dict(rec.__dict__)
        d.pop("_sa_instance_state", None)
        by_date[rec.data] = d
    return by_date


def _merge_part03_table_rows(
    by_date: dict[str, dict[str, Any]],
    table: Any,
) -> None:
    if table is None or not hasattr(table, "get_data_rows"):
        return
    for row in table.get_data_rows():
        date = row.get("data")
        if date:
            by_date[date] = dict(row)


def _merge_part03_from_page_cache(
    by_date: dict[str, dict[str, Any]],
    page: Any,
    categorie: str | None,
    year: int,
    month: int,
) -> None:
    """Suprascrie cu luni păstrate în _data_cache (nesalvate), indiferent de luna afișată."""
    cache = getattr(page, "_data_cache", None)
    if not cache or not hasattr(page, "_cache_key"):
        return
    categories: list[str | None]
    if getattr(page, "has_copii_adulti", False):
        categories = []
        if categorie in (None, "adulti"):
            categories.append("adulti")
        if categorie in (None, "copii"):
            categories.append("copii")
    else:
        categories = [None]
    for cat in categories:
        key = page._cache_key(year, month, cat)
        cached = cache.get(key)
        if not cached:
            continue
        for row in cached.get("rows") or []:
            date = row.get("data")
            if date:
                by_date[date] = dict(row)


def _resolve_live_part03_page(main_window: Any) -> Any | None:
    """Pagina Părții III încărcată sau None (ignoră placeholder-ele QWidget din meniu)."""
    if main_window is None:
        return None
    loaded = getattr(main_window, "_loaded_parts", None)
    if not loaded or "part_03" not in loaded:
        return None
    page = getattr(main_window, "_part_pages", {}).get("part_03")
    if page is None or not hasattr(page, "year") or not hasattr(page, "month"):
        return None
    return page


def load_part03_with_live_cache(
    main_window: Any,
    categorie: str | None,
    year: int,
    month: int,
) -> dict[str, dict[str, Any]]:
    """Părtea III din DB, suprascrisă cu cache și tabele live (modificări nesalvate)."""
    by_date = dict(load_part03_by_date(categorie, year, month))
    page = _resolve_live_part03_page(main_window)
    if page is None:
        return by_date

    _merge_part03_from_page_cache(by_date, page, categorie, year, month)

    if page.year != year or page.month != month:
        return by_date

    if getattr(page, "has_copii_adulti", False):
        if categorie in (None, "adulti"):
            _merge_part03_table_rows(by_date, getattr(page, "table_adulti", None))
        if categorie in (None, "copii"):
            _merge_part03_table_rows(by_date, getattr(page, "table_copii", None))
    else:
        _merge_part03_table_rows(by_date, getattr(page, "table", None))
    return by_date


def part04_total_for_date(
    main_window: Any,
    categorie: str | None,
    year: int,
    month: int,
    date: str,
) -> int:
    """Total împrumuturi din P. III pentru o zi (inclusiv modificări nesalvate)."""
    by_date = load_part03_with_live_cache(main_window, categorie, year, month)
    return part03_row_total(by_date.get(date))


PART04_CZU_KEYS = (
    "czu_0_generalitati",
    "czu_1_filozofie",
    "czu_2_religie",
    "czu_3_stiinte_sociale",
    "czu_5_matematica",
    "czu_6_stiinte_aplicate",
    "czu_7_arte",
    "czu_8_limbi",
    "czu_9_geografie",
)


def part04_czu_sum(row: dict[str, Any] | None) -> int:
    if not row:
        return 0
    return sum(max(0, int(row.get(k) or 0)) for k in PART04_CZU_KEYS)


def part04_row_total(row: dict[str, Any], part03_total: int) -> int:
    """Total afișat/salvat: din P. III dacă > 0, altfel suma coloanelor CZU."""
    p3 = max(0, int(part03_total))
    if p3 > 0:
        return p3
    return part04_czu_sum(row)


def part04_czu_max_allowed(row: dict[str, Any], column_key: str) -> int:
    """Valoarea maximă permisă într-o coloană CZU, fără a depăși totalul împrumuturi."""
    if column_key not in PART04_CZU_KEYS:
        return 0
    total = max(0, int(row.get("total_imprumuturi") or 0))
    other_sum = part04_czu_sum(row) - max(0, int(row.get(column_key) or 0))
    return max(0, total - other_sum)


def rebalance_part04_czu_to_total(row: dict[str, Any]) -> bool:
    """Scala proporțional coloanele CZU dacă depășesc totalul împrumuturi."""
    total = max(0, int(row.get("total_imprumuturi") or 0))
    current_sum = part04_czu_sum(row)
    if current_sum <= total:
        return False
    if total == 0:
        # Total 0 din P. III — păstrăm CZU introdus manual până se completează P. III.
        return False

    values = {key: max(0, int(row.get(key) or 0)) for key in PART04_CZU_KEYS}
    exact = {key: values[key] * total / current_sum for key in PART04_CZU_KEYS}
    floored = {key: int(exact[key]) for key in PART04_CZU_KEYS}
    remainder = total - sum(floored.values())
    order = sorted(PART04_CZU_KEYS, key=lambda k: exact[k] - floored[k], reverse=True)
    for i in range(remainder):
        floored[order[i % len(order)]] += 1
    for key in PART04_CZU_KEYS:
        row[key] = floored[key]
    return True


def align_part04_czu_rows(rows: list[dict[str, Any]]) -> int:
    """Ajustează rândurile unde suma CZU > total. Returnează numărul de rânduri modificate."""
    changed = 0
    for row in rows:
        if rebalance_part04_czu_to_total(row):
            changed += 1
    return changed


def validate_part04_czu_value(
    row: dict[str, Any], column_key: str, new_value: int
) -> tuple[bool, str]:
    """Verifică dacă suma categoriilor CZU rămâne ≤ total împrumuturi."""
    if column_key not in PART04_CZU_KEYS:
        return True, ""
    try:
        num = max(0, int(new_value))
    except (TypeError, ValueError):
        return False, "Doar numere întregi ≥ 0"

    total = max(0, int(row.get("total_imprumuturi") or 0))
    other_sum = sum(
        max(0, int(row.get(k) or 0)) for k in PART04_CZU_KEYS if k != column_key
    )
    max_allowed = max(0, total - other_sum)
    if num <= max_allowed:
        return True, ""

    if total == 0:
        return True, ""
    if other_sum > total:
        return False, (
            f"Valoare respinsă — suma celorlalte categorii CZU ({other_sum}) depășește "
            f"totalul împrumuturi ({total}). Reduceți celelalte coloane sau măriți "
            f"totalul în Partea III (maxim aici: {max_allowed})."
        )
    if max_allowed == 0:
        return False, (
            f"Valoare respinsă — suma celorlalte categorii CZU este deja {other_sum} "
            f"(egală cu totalul {total}). Pentru această coloană puteți introduce doar 0."
        )
    return False, (
        f"Valoare respinsă — maxim {max_allowed} (celelalte categorii: {other_sum}, "
        f"total împrumuturi: {total})."
    )


def apply_part04_totals(
    rows: list[dict[str, Any]],
    part03_by_date: dict[str, dict[str, Any]],
) -> None:
    """Fixează total împrumuturi: P. III dacă există, altfel suma CZU."""
    for row in rows:
        date = row.get("data")
        p3 = part03_by_date.get(date) if date else None
        p3_total = part03_row_total(p3)
        row["total_imprumuturi"] = part04_row_total(row, p3_total)
        row["_sync_total_from_part03"] = p3_total > 0


def sync_part04_row_total_and_align(
    row: dict[str, Any],
    total: int,
) -> bool:
    """Actualizează totalul pe rând și rebalancează CZU doar dacă total > 0 și suma depășește."""
    row["total_imprumuturi"] = max(0, int(total))
    if row["total_imprumuturi"] <= 0:
        return False
    return rebalance_part04_czu_to_total(row)


def sync_part04_rows_from_part03(
    rows: list[dict[str, Any]],
    main_window: Any,
    categorie: str | None,
    year: int,
    month: int,
    *,
    rebalance_czu: bool = True,
) -> int:
    """Sincronizează totalurile din P. III; opțional rebalancează CZU dacă depășesc totalul."""
    p3_by_date = load_part03_with_live_cache(main_window, categorie, year, month)
    apply_part04_totals(rows, p3_by_date)
    if rebalance_czu:
        return align_part04_czu_rows(rows)
    return 0


def persist_part04_totals_from_part03(
    year: int,
    month: int,
    categorie: str,
) -> None:
    """Scrie totaluri P. IV din P. III în baza de date."""
    p3_by_date = load_part03_by_date(categorie, year, month)
    working_days = get_working_days(year, month, get_excluded_days(year, month))
    if not working_days:
        return

    with get_session() as session:
        for date in working_days:
            total = part03_row_total(p3_by_date.get(date))
            rec = session.scalar(
                select(DocumenteContinutCZU).where(
                    DocumenteContinutCZU.an == year,
                    DocumenteContinutCZU.luna == month,
                    DocumenteContinutCZU.data == date,
                    DocumenteContinutCZU.categorie_varsta == categorie,
                )
            )
            if rec is not None:
                rec.total_imprumuturi = total
            else:
                session.add(
                    DocumenteContinutCZU(
                        an=year,
                        luna=month,
                        data=date,
                        categorie_varsta=categorie,
                        total_imprumuturi=total,
                    )
                )
        session.commit()


def sync_part04_categories(year: int, month: int) -> None:
    """Sincronizează totaluri P. IV din P. III (Copii și Adulți) în baza de date."""
    for categorie in ("adulti", "copii"):
        persist_part04_totals_from_part03(year, month, categorie)


def invalidate_part04_cache_if_loaded(main_window) -> None:
    """Reîncarcă Partea IV sau actualizează totalurile dacă are modificări nesalvate."""
    loaded = getattr(main_window, "_loaded_parts", set())
    if "part_04" not in loaded:
        return
    page = getattr(main_window, "_part_pages", {}).get("part_04")
    if page is None or not hasattr(page, "_load_current"):
        return
    if hasattr(page, "has_unsaved_changes") and page.has_unsaved_changes():
        if hasattr(page, "refresh_totals_from_part03"):
            page.refresh_totals_from_part03()
        return
    if hasattr(page, "_invalidate_caches"):
        page._invalidate_caches()
    page._load_current(fast=True)
