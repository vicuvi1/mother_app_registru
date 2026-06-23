"""Sincronizare date între Părți ale registrului."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, select

from database.db_manager import get_session
from database.models import DocumenteInregistrate

PART03_IMPRUMUT_KEYS = (
    "total_imprumuturi",
    "consultare_pe_loc",
    "imprumut_pe_loc",
    "imprumut_la_domiciliu",
    "imprumut_inter_bibliotecar",
)


def part03_has_imprumut_data(row: dict[str, Any] | None) -> bool:
    """True dacă Partea III are date în secțiunea total împrumuturi."""
    if not row:
        return False
    return any(int(row.get(k) or 0) > 0 for k in PART03_IMPRUMUT_KEYS)


def _part03_total(row: dict[str, Any]) -> int:
    stored = int(row.get("total_imprumuturi") or 0)
    if stored > 0:
        return stored
    return sum(int(row.get(k) or 0) for k in PART03_IMPRUMUT_KEYS[1:])


def load_part03_by_date(
    categorie: str | None,
    year: int,
    month: int,
) -> dict[str, dict[str, Any]]:
    """Încarcă rândurile Părții III indexate după dată (DD.MM)."""
    with get_session() as session:
        filters = [
            DocumenteInregistrate.an == year,
            DocumenteInregistrate.luna == month,
        ]
        if categorie:
            filters.append(DocumenteInregistrate.categorie_varsta == categorie)
        rows = session.scalars(
            select(DocumenteInregistrate).where(and_(*filters)).order_by(DocumenteInregistrate.data)
        ).all()

    by_date: dict[str, dict[str, Any]] = {}
    for rec in rows:
        d = dict(rec.__dict__)
        d.pop("_sa_instance_state", None)
        by_date[rec.data] = d
    return by_date


def apply_part04_totals(
    rows: list[dict[str, Any]],
    part03_by_date: dict[str, dict[str, Any]],
    czu_keys: list[str],
) -> None:
    """Setează total împrumuturi în Partea IV din Partea III când există date acolo."""
    for row in rows:
        date = row.get("data")
        p3 = part03_by_date.get(date) if date else None
        if part03_has_imprumut_data(p3):
            row["total_imprumuturi"] = _part03_total(p3 or {})
            row["_sync_total_from_part03"] = True
        else:
            row["_sync_total_from_part03"] = False
            row["total_imprumuturi"] = sum(int(row.get(k) or 0) for k in czu_keys)
