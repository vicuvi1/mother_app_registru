"""Progres pe parte pentru un an — badge-uri sidebar și panou Acasă."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from core.part_models import get_part_model
from core.parts_registry import PART_ENTRIES
from core.register_audit import find_incomplete_months
from database.db_manager import get_session

STATUS_COMPLETE = "complete"
STATUS_ATTENTION = "attention"
STATUS_EMPTY = "empty"

_BADGE = {
    STATUS_COMPLETE: "✓",
    STATUS_ATTENTION: "⚠",
    STATUS_EMPTY: "·",
}


@dataclass(frozen=True)
class PartProgress:
    part_id: str
    roman: str
    short: str
    status: str
    incomplete_slots: int
    total_slots: int

    @property
    def badge(self) -> str:
        return _BADGE.get(self.status, "·")


def _total_slots_for_entry(entry: dict) -> int:
    if entry["mode"] == "crud":
        return 1
    cats = 2 if entry["has_copii_adulti"] else 1
    return 12 * cats


def _crud_status(model) -> str:
    with get_session() as session:
        count = session.scalar(select(func.count()).select_from(model)) or 0
    return STATUS_COMPLETE if count > 0 else STATUS_EMPTY


def compute_part_progress(year: int) -> dict[str, PartProgress]:
    """Calculează starea fiecărei părți pentru anul dat."""
    incomplete = find_incomplete_months(year)
    by_part: dict[str, list] = defaultdict(list)
    for slot in incomplete:
        by_part[slot.part_id].append(slot)

    result: dict[str, PartProgress] = {}
    for entry in PART_ENTRIES:
        part_id = entry["part_id"]
        model = get_part_model(part_id)
        if model is None:
            continue

        if entry["mode"] == "crud":
            status = _crud_status(model)
            result[part_id] = PartProgress(
                part_id=part_id,
                roman=entry["roman"],
                short=entry["short"],
                status=status,
                incomplete_slots=0 if status == STATUS_COMPLETE else 1,
                total_slots=1,
            )
            continue

        total = _total_slots_for_entry(entry)
        inc = len(by_part.get(part_id, []))
        if inc == 0:
            status = STATUS_COMPLETE
        elif inc >= total:
            status = STATUS_EMPTY
        else:
            status = STATUS_ATTENTION

        result[part_id] = PartProgress(
            part_id=part_id,
            roman=entry["roman"],
            short=entry["short"],
            status=status,
            incomplete_slots=inc,
            total_slots=total,
        )

    return result


def count_summary(progress: dict[str, PartProgress]) -> tuple[int, int, int]:
    """Returnează (complete, attention, empty)."""
    complete = attention = empty = 0
    for p in progress.values():
        if p.status == STATUS_COMPLETE:
            complete += 1
        elif p.status == STATUS_ATTENTION:
            attention += 1
        else:
            empty += 1
    return complete, attention, empty
