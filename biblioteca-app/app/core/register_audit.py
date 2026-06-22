"""Audit registru — identifică luni/perioade fără date în baza de date."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, select

from core.constants_manager import LUNI_RO
from core.part_models import get_part_model
from core.parts_registry import PART_ENTRIES
from database.db_manager import get_session


@dataclass(frozen=True)
class IncompleteSlot:
    part_id: str
    roman: str
    title: str
    month: int | None
    category: str | None
    label: str


def _count_rows(model, year: int, month: int | None, category: str | None) -> int:
    with get_session() as session:
        filters = [model.an == year]
        if month is not None and hasattr(model, "luna"):
            filters.append(model.luna == month)
        if category and hasattr(model, "categorie_varsta"):
            filters.append(model.categorie_varsta == category)
        q = select(func.count()).select_from(model).where(and_(*filters))
        return int(session.scalar(q) or 0)


def _category_label(category: str | None) -> str:
    if category == "copii":
        return "Copii"
    if category == "adulti":
        return "Adulți"
    return ""


def find_incomplete_months(year: int) -> list[IncompleteSlot]:
    """Returnează sloturi fără niciun rând salvat în DB pentru anul dat."""
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
                    if _count_rows(model, year, month, cat) == 0:
                        cat_lbl = _category_label(cat)
                        prefix = f"{cat_lbl} — " if cat_lbl else ""
                        results.append(
                            IncompleteSlot(
                                part_id=part_id,
                                roman=roman,
                                title=title,
                                month=month,
                                category=cat,
                                label=f"Partea {roman}. {title} — {prefix}{LUNI_RO[month - 1]}",
                            )
                        )
        elif mode == "monthly":
            for month in range(1, 13):
                if _count_rows(model, year, month, None) == 0:
                    results.append(
                        IncompleteSlot(
                            part_id=part_id,
                            roman=roman,
                            title=title,
                            month=month,
                            category=None,
                            label=f"Partea {roman}. {title} — {LUNI_RO[month - 1]}",
                        )
                    )

    return results
