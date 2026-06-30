"""Mapare part_id → model SQLAlchemy (import lazy)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

_PART_MODEL_NAMES: dict[str, str] = {
    "part_01": "EvidentaUtilizatori",
    "part_02": "EvidentaUtilizatoriCopiiAdulti",
    "part_03": "DocumenteInregistrate",
    "part_04": "DocumenteContinutCZU",
    "part_05": "CercetariBibliografice",
    "part_06": "ActivitatiInformare",
    "part_07": "DocumenteElectronice",
    "part_09": "Instruiri",
    "part_11": "ActivitatiCulturale",
    "part_12": "ActivitatiOnline",
    "part_13": "Parteneri",
    "part_14": "Voluntariat",
}


def get_part_model(part_id: str) -> type[DeclarativeBase] | None:
    model_name = _PART_MODEL_NAMES.get(part_id)
    if not model_name:
        return None
    import database.models as models

    return getattr(models, model_name, None)
