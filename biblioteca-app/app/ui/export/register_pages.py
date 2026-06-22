"""Construire listă pagini registru — ordine: toate părțile Adulți, apoi toate părțile Copii."""

from __future__ import annotations

from core.constants_manager import get_cover_page
from ui.main_window import PARTS, PART_LAYOUT

CATEGORY_ORDER = ["adulti", "copii"]


def pages_for_part_category(page_obj, year: int, category: str | None) -> list[dict]:
    pages: list[dict] = []
    if page_obj.mode in ("daily", "events"):
        for m in range(1, 13):
            pages.append(page_obj._build_page(year, m, category))
    else:
        pages.append(page_obj._build_page(year, None, category))
    return pages


def cover_page(year: int) -> dict:
    data = get_cover_page()
    if not data.get("an"):
        data["an"] = str(year)
    data["type"] = "cover"
    return data


def iter_register_slots() -> list[tuple[str, str, str, str, str | None]]:
    """
    Sloturi în ordinea de export/arbore:
    1) fiecare parte — Adulți (sau fără categorie)
    2) fiecare parte cu tab copii — Copii
    """
    slots: list[tuple[str, str, str, str, str | None]] = []
    for roman, part_id, title, short in PARTS:
        mode, has_copii = PART_LAYOUT.get(part_id, ("daily", False))
        if has_copii:
            slots.append((roman, part_id, title, short, "adulti"))
        else:
            slots.append((roman, part_id, title, short, None))
    for roman, part_id, title, short in PARTS:
        if PART_LAYOUT.get(part_id, ("daily", False))[1]:
            slots.append((roman, part_id, title, short, "copii"))
    return slots


def collect_full_register_pages(
    main_window,
    year: int,
    *,
    include_cover: bool = True,
    get_page_obj=None,
) -> list[dict]:
    """Registru complet: copertă + toate părțile (adulți), apoi toate părțile (copii)."""
    if get_page_obj is None:
        get_page_obj = main_window._get_or_load_part

    pages: list[dict] = []
    if include_cover:
        pages.append(cover_page(year))

    for _roman, part_id, _title, _short, cat in iter_register_slots():
        page_obj = get_page_obj(part_id)
        if page_obj is None:
            continue
        pages.extend(pages_for_part_category(page_obj, year, cat))
    return pages
