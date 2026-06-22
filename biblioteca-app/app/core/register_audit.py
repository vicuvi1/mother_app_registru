"""Audit registru — identifică luni/perioade fără date în baza de date."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, inspect as sa_inspect, select
from sqlalchemy.orm import DeclarativeBase

from core.constants_manager import LUNI_RO
from core.part_models import get_part_model
from core.parts_registry import PART_ENTRIES
from database.db_manager import get_session

_META_COLUMNS = frozenset(
    {
        "id",
        "an",
        "luna",
        "categorie_varsta",
        "is_auto_generated",
        "created_at",
        "updated_at",
    }
)
_DATE_SCAFFOLD_COLUMNS = frozenset({"data", "luna"})


@dataclass(frozen=True)
class IncompleteSlot:
    part_id: str
    roman: str
    title: str
    month: int | None
    category: str | None
    label: str
    reason: str = "empty"  # empty | zeros


def _category_label(category: str | None) -> str:
    if category == "copii":
        return "Copii"
    if category == "adulti":
        return "Adulți"
    return ""


def _row_has_content(row: DeclarativeBase) -> bool:
    """True dacă rândul conține cel puțin o valoare nenulă / netext goală."""
    mapper = sa_inspect(row.__class__)
    for col in mapper.columns:
        name = col.name
        if name in _META_COLUMNS:
            continue
        if name in _DATE_SCAFFOLD_COLUMNS:
            continue
        val = getattr(row, name, None)
        if val is None:
            continue
        if isinstance(val, bool):
            if val:
                return True
            continue
        if isinstance(val, int):
            if val != 0:
                return True
            continue
        if str(val).strip():
            return True
    return False


def _fetch_rows(model, year: int, month: int | None, category: str | None) -> list:
    with get_session() as session:
        filters = [model.an == year]
        if month is not None and hasattr(model, "luna"):
            filters.append(model.luna == month)
        if category and hasattr(model, "categorie_varsta"):
            filters.append(model.categorie_varsta == category)
        q = select(model).where(and_(*filters))
        return list(session.scalars(q))


def _slot_status(model, year: int, month: int | None, category: str | None) -> str | None:
    """None = complet; 'empty' = fără rânduri; 'zeros' = rânduri dar toate valorile sunt 0/goale."""
    rows = _fetch_rows(model, year, month, category)
    if not rows:
        return "empty"
    if not any(_row_has_content(r) for r in rows):
        return "zeros"
    return None


def find_incomplete_months(year: int) -> list[IncompleteSlot]:
    """Returnează sloturi fără date sau cu rânduri goale (toate valorile 0)."""
    results: list[IncompleteSlot] = []

    for entry in PART_ENTRIES:
        part_id = entry["part_id"]
        mode = entry["mode"]
        if mode == "crud":
            continue

        model = get_part_model(part_id)
        if model is None:
            continue

        roman = entry["roman"]
        title = entry["title"]
        cats: list[str | None] = ["adulti", "copii"] if entry["has_copii_adulti"] else [None]

        if mode in ("daily", "events"):
            for month in range(1, 13):
                for cat in cats:
                    status = _slot_status(model, year, month, cat)
                    if status is None:
                        continue
                    cat_lbl = _category_label(cat)
                    prefix = f"{cat_lbl} — " if cat_lbl else ""
                    suffix = (
                        " (fără rânduri)"
                        if status == "empty"
                        else " (toate valorile sunt 0)"
                    )
                    results.append(
                        IncompleteSlot(
                            part_id=part_id,
                            roman=roman,
                            title=title,
                            month=month,
                            category=cat,
                            reason=status,
                            label=f"Partea {roman}. {title} — {prefix}{LUNI_RO[month - 1]}{suffix}",
                        )
                    )
        elif mode == "monthly":
            for month in range(1, 13):
                status = _slot_status(model, year, month, None)
                if status is None:
                    continue
                suffix = (
                    " (fără rânduri)"
                    if status == "empty"
                    else " (toate valorile sunt 0)"
                )
                results.append(
                    IncompleteSlot(
                        part_id=part_id,
                        roman=roman,
                        title=title,
                        month=month,
                        category=None,
                        reason=status,
                        label=f"Partea {roman}. {title} — {LUNI_RO[month - 1]}{suffix}",
                    )
                )

    return results
