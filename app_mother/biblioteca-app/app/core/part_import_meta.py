"""Metadate părți pentru import Excel."""

from __future__ import annotations

import importlib
from typing import Any

from core.part_models import get_part_model
from core.parts_registry import PART_ENTRIES
from ui.widgets.table.column_def import ColumnDef

_PART_MODULES: dict[str, str] = {
    "part_01": "ui.part_01_utilizatori",
    "part_02": "ui.part_02_utilizatori_copii_adulti",
    "part_03": "ui.part_03_documente_inregistrate",
    "part_04": "ui.part_04_documente_continut",
    "part_05": "ui.part_05_cercetari_bibliografice",
    "part_06": "ui.part_06_activitati_informare",
    "part_07": "ui.part_07_documente_electronice",
    "part_09": "ui.part_09_instruiri",
    "part_11": "ui.part_11_activitati_culturale",
    "part_12": "ui.part_12_activitati_online",
    "part_13": "ui.part_13_parteneri",
    "part_14": "ui.part_14_voluntariat",
}


def get_part_import_meta(part_id: str) -> dict[str, Any]:
    entry = next((e for e in PART_ENTRIES if e["part_id"] == part_id), None)
    if entry is None:
        raise ValueError(f"Parte necunoscută: {part_id}")
    mod_name = _PART_MODULES.get(part_id)
    if not mod_name:
        raise ValueError(f"Import neacceptat pentru {part_id}")
    mod = importlib.import_module(mod_name)
    columns: list[ColumnDef] = list(mod.COLUMNS)
    model = get_part_model(part_id)
    if model is None:
        raise ValueError(f"Model lipsă pentru {part_id}")
    date_field = "data"
    for col in columns:
        if col.col_type == "date":
            date_field = col.key
            break
    return {
        "part_id": part_id,
        "roman": entry["roman"],
        "title": entry["title"],
        "mode": entry["mode"],
        "has_copii_adulti": entry["has_copii_adulti"],
        "columns": columns,
        "model": model,
        "date_field": date_field,
    }


def list_importable_parts() -> list[tuple[str, str, str]]:
    return [
        (e["part_id"], e["roman"], e["title"])
        for e in PART_ENTRIES
        if e["part_id"] in _PART_MODULES and e["mode"] != "crud"
    ]
