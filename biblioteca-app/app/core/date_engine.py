"""Calcul zile lucrătoare, validare format DD.MM."""

import calendar
import re
from datetime import date, datetime


DATE_PATTERN = re.compile(r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])$")


def is_working_day(date_obj: date) -> bool:
    """True dacă date_obj.weekday() < 5 (Luni=0 ... Vineri=4)."""
    return date_obj.weekday() < 5


def validate_date_format(date_str: str) -> bool:
    """Validează că string-ul respectă strict formatul DD.MM."""
    if not DATE_PATTERN.match(date_str.strip()):
        return False
    day_str, month_str = date_str.strip().split(".")
    day, month = int(day_str), int(month_str)
    if month < 1 or month > 12:
        return False
    max_day = calendar.monthrange(2000, month)[1]  # an bisect neutru pt. februarie
    return 1 <= day <= max_day


def _parse_dd_mm(date_str: str, year: int) -> date | None:
    if not validate_date_format(date_str):
        return None
    day_str, month_str = date_str.split(".")
    try:
        return date(year, int(month_str), int(day_str))
    except ValueError:
        return None


def format_dd_mm(date_obj: date) -> str:
    """Formatează un obiect date ca DD.MM."""
    return date_obj.strftime("%d.%m")


def get_working_days(
    year: int,
    month: int,
    excluded_dates: list[str] | None = None,
) -> list[str]:
    """
    Returnează listă de string-uri 'DD.MM' pentru toate zilele Luni-Vineri
    din luna/anul dat, excluzând datele din excluded_dates (format 'DD.MM').
    """
    if month < 1 or month > 12:
        return []

    excluded = set(excluded_dates or [])
    _, days_in_month = calendar.monthrange(year, month)
    result: list[str] = []

    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        if not is_working_day(current):
            continue
        formatted = format_dd_mm(current)
        if formatted in excluded:
            continue
        result.append(formatted)

    return result


def sort_dates_dd_mm(dates: list[str], year: int) -> list[str]:
    """Sortează cronologic o listă de date DD.MM pentru anul dat."""
    valid = [d for d in dates if validate_date_format(d)]
    return sorted(valid, key=lambda d: _parse_dd_mm(d, year) or date.min)


def date_dd_mm_to_sort_key(date_str: str, year: int) -> tuple[int, int]:
    """Cheie de sortare (lună, zi) pentru DD.MM."""
    parsed = _parse_dd_mm(date_str, year)
    if parsed is None:
        return (0, 0)
    return (parsed.month, parsed.day)


def purge_excluded_days_from_registers(year: int) -> int:
    """Șterge din DB rândurile părților zilnice care nu sunt zile lucrătoare."""
    from sqlalchemy import and_, select

    from core.constants_manager import get_excluded_days
    from core.part_models import get_part_model
    from core.parts_registry import PART_ENTRIES
    from database.db_manager import get_session

    removed = 0
    with get_session() as session:
        for entry in PART_ENTRIES:
            if entry.get("mode") != "daily":
                continue
            model = get_part_model(entry["part_id"])
            if model is None or not hasattr(model, "data"):
                continue
            for month in range(1, 13):
                allowed = set(
                    get_working_days(year, month, get_excluded_days(year, month))
                )
                records = session.scalars(
                    select(model).where(
                        and_(model.an == year, model.luna == month)
                    )
                ).all()
                for rec in records:
                    day = getattr(rec, "data", None)
                    if day and day not in allowed:
                        session.delete(rec)
                        removed += 1
        session.commit()
    return removed
