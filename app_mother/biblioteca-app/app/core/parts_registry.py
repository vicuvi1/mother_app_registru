"""Registru central — părți, layout, factory lazy."""

from __future__ import annotations

from typing import Callable

from PyQt5.QtWidgets import QWidget

PART_ENTRIES: list[dict] = [
    {"roman": "I", "part_id": "part_01", "title": "Evidența utilizatorilor", "short": "Utilizatori", "mode": "daily", "has_copii_adulti": False},
    {"roman": "II", "part_id": "part_02", "title": "Evidența utilizatorilor (Copii / Adulți)", "short": "Utilizatori", "mode": "daily", "has_copii_adulti": True},
    {"roman": "III", "part_id": "part_03", "title": "Evidența documentelor înregistrate", "short": "Documente", "mode": "daily", "has_copii_adulti": True},
    {"roman": "IV", "part_id": "part_04", "title": "Evidența documentelor (conținut CZU)", "short": "Documente", "mode": "daily", "has_copii_adulti": True},
    {"roman": "V", "part_id": "part_05", "title": "Evidența cercetărilor bibliografice", "short": "Cercetări", "mode": "events", "has_copii_adulti": True},
    {"roman": "VI", "part_id": "part_06", "title": "Evidența activităților de informare", "short": "Informare", "mode": "events", "has_copii_adulti": True},
    {"roman": "VII", "part_id": "part_07", "title": "Evidența documentelor electronice online", "short": "Electronice", "mode": "monthly", "has_copii_adulti": True},
    {"roman": "IX", "part_id": "part_09", "title": "Instruirea utilizatorilor bibliotecii", "short": "Instruiri", "mode": "events", "has_copii_adulti": True},
    {"roman": "XI", "part_id": "part_11", "title": "Evidența activităților culturale și științifice", "short": "Cultural", "mode": "events", "has_copii_adulti": True},
    {"roman": "XII", "part_id": "part_12", "title": "Evidența activităților culturale ONLINE", "short": "Online", "mode": "events", "has_copii_adulti": True},
    {"roman": "XIII", "part_id": "part_13", "title": "Parteneri ai bibliotecii", "short": "Parteneri", "mode": "crud", "has_copii_adulti": False},
    {"roman": "XIV", "part_id": "part_14", "title": "Activități de voluntariat", "short": "Voluntariat", "mode": "crud", "has_copii_adulti": False},
]

PARTS: list[tuple[str, str, str, str]] = [
    (e["roman"], e["part_id"], e["title"], e["short"]) for e in PART_ENTRIES
]

PART_LAYOUT: dict[str, tuple[str, bool]] = {
    e["part_id"]: (e["mode"], e["has_copii_adulti"]) for e in PART_ENTRIES
}

_FACTORY_MAP: dict[str, str] = {e["part_id"]: e["part_id"] for e in PART_ENTRIES}


def get_part_factory(part_id: str) -> Callable[[QWidget], QWidget] | None:
    """Import lazy — încarcă modulul părții doar când e necesar."""
    if part_id not in _FACTORY_MAP:
        return None
    factories: dict[str, Callable] = {
        "part_01": _load_part_01,
        "part_02": _load_part_02,
        "part_03": _load_part_03,
        "part_04": _load_part_04,
        "part_05": _load_part_05,
        "part_06": _load_part_06,
        "part_07": _load_part_07,
        "part_09": _load_part_09,
        "part_11": _load_part_11,
        "part_12": _load_part_12,
        "part_13": _load_part_13,
        "part_14": _load_part_14,
    }
    return factories.get(part_id)


def _load_part_01(mw):  # noqa: ANN001
    from ui.part_01_utilizatori import create_page
    return create_page(mw)


def _load_part_02(mw):
    from ui.part_02_utilizatori_copii_adulti import create_page
    return create_page(mw)


def _load_part_03(mw):
    from ui.part_03_documente_inregistrate import create_page
    return create_page(mw)


def _load_part_04(mw):
    from ui.part_04_documente_continut import create_page
    return create_page(mw)


def _load_part_05(mw):
    from ui.part_05_cercetari_bibliografice import create_page
    return create_page(mw)


def _load_part_06(mw):
    from ui.part_06_activitati_informare import create_page
    return create_page(mw)


def _load_part_07(mw):
    from ui.part_07_documente_electronice import create_page
    return create_page(mw)


def _load_part_09(mw):
    from ui.part_09_instruiri import create_page
    return create_page(mw)


def _load_part_11(mw):
    from ui.part_11_activitati_culturale import create_page
    return create_page(mw)


def _load_part_12(mw):
    from ui.part_12_activitati_online import create_page
    return create_page(mw)


def _load_part_13(mw):
    from ui.part_13_parteneri import create_page
    return create_page(mw)


def _load_part_14(mw):
    from ui.part_14_voluntariat import create_page
    return create_page(mw)
