"""Construire listă pagini registru — ordine: toate părțile Adulți, apoi toate părțile Copii."""

from __future__ import annotations

import logging
from typing import Callable

from core.constants_manager import get_cover_page
from core.parts_registry import PARTS, PART_LAYOUT

logger = logging.getLogger(__name__)

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
    progress_callback: Callable[[int, int, str], bool] | None = None,
) -> list[dict]:
    """
    Registru complet: copertă + toate părțile (adulți), apoi toate părțile (copii).

    progress_callback(current, total, label) -> False pentru anulare.
  """
    if get_page_obj is None:
        get_page_obj = main_window._get_or_load_part

    slots = iter_register_slots()
    total_steps = (1 if include_cover else 0) + len(slots)
    step = 0

    pages: list[dict] = []
    if include_cover:
        if progress_callback and not progress_callback(step, total_steps, "Copertă"):
            raise InterruptedError("Export anulat de utilizator.")
        pages.append(cover_page(year))
        step += 1

    for roman, part_id, title, short, cat in slots:
        label = f"Partea {roman}. {title}"
        if cat:
            label += f" ({cat})"
        if progress_callback and not progress_callback(step, total_steps, label):
            raise InterruptedError("Export anulat de utilizator.")

        try:
            page_obj = get_page_obj(part_id)
            if page_obj is None:
                logger.warning("Partea %s (%s) nu a putut fi încărcată", roman, part_id)
                raise ValueError(f"Partea {roman}. {title} nu a putut fi încărcată.")
            pages.extend(pages_for_part_category(page_obj, year, cat))
        except InterruptedError:
            raise
        except Exception as exc:
            logger.exception("Eroare la colectarea părții %s (%s)", roman, part_id)
            raise ValueError(f"Partea {roman}. {title}: {exc}") from exc
        step += 1

    return pages


def collect_full_register_pages_with_dialog(parent, main_window, year: int) -> list[dict]:
    """Colectează paginile registrului complet cu dialog de progres."""
    from PyQt5.QtWidgets import QApplication, QProgressDialog

    progress = QProgressDialog("Se pregătesc paginile pentru export…", "Anulează", 0, 100, parent)
    progress.setWindowTitle("Export registru complet")
    progress.setMinimumDuration(0)
    progress.setValue(0)

    cancelled = False

    def on_progress(current: int, total: int, label: str) -> bool:
        nonlocal cancelled
        if cancelled or progress.wasCanceled():
            cancelled = True
            return False
        if total > 0:
            progress.setMaximum(total)
            progress.setValue(current)
        progress.setLabelText(label)
        QApplication.processEvents()
        return not progress.wasCanceled()

    try:
        return collect_full_register_pages(
            main_window,
            year,
            progress_callback=on_progress,
        )
    finally:
        progress.close()
