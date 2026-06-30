"""Persistență sesiune — ultima parte, an și lună deschise."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from database.db_manager import DATA_DIR

logger = logging.getLogger(__name__)

SESSION_PATH = DATA_DIR / "session.json"


def load_session() -> dict:
    try:
        if SESSION_PATH.exists():
            data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError, TypeError):
        logger.warning("Nu s-a putut citi session.json", exc_info=True)
    return {}


def save_session(
    *,
    part_id: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> None:
    data = load_session()
    if part_id is not None:
        data["part_id"] = part_id
    if year is not None:
        data["year"] = year
    if month is not None:
        data["month"] = month
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        logger.warning("Nu s-a putut salva session.json", exc_info=True)
