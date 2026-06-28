"""Repartizare automată Masculin/Feminin după numărul total de participanți."""

from __future__ import annotations

from typing import Any

OVERRIDE_PARTICIPANTI_GENDER = "_override_participanti_gender"


def default_gender_split(total: int) -> tuple[int, int]:
    """Împarte participanții: jumătate (rotunjit) feminin, restul masculin."""
    total = max(0, int(total))
    feminin = total // 2
    masculin = total - feminin
    return masculin, feminin


def participant_gender_sum(row: dict[str, Any], m_key: str, f_key: str) -> int:
    return max(0, int(row.get(m_key) or 0)) + max(0, int(row.get(f_key) or 0))


def validate_participant_gender_value(
    row: dict[str, Any],
    column_key: str,
    new_value: int,
    *,
    total_key: str,
    m_key: str,
    f_key: str,
) -> tuple[bool, str]:
    """Masculin + Feminin nu poate depăși numărul total de participanți."""
    if column_key not in (m_key, f_key):
        return True, ""
    try:
        num = max(0, int(new_value))
    except (TypeError, ValueError):
        return False, "Doar numere întregi ≥ 0"

    trial = dict(row)
    trial[column_key] = num
    total = max(0, int(trial.get(total_key) or 0))
    if total <= 0:
        return True, ""
    gender_sum = participant_gender_sum(trial, m_key, f_key)
    if gender_sum <= total:
        return True, ""
    return (
        False,
        f"Suma Masculin + Feminin ({gender_sum}) depășește numărul participanți ({total}).",
    )


def apply_participant_gender_split(
    row: dict[str, Any],
    *,
    total_key: str,
    m_key: str,
    f_key: str,
) -> bool:
    """Completează M/F din total. Returnează True dacă s-a modificat rândul."""
    total = max(0, int(row.get(total_key) or 0))
    if total <= 0:
        return False
    masculin, feminin = default_gender_split(total)
    if int(row.get(m_key) or 0) == masculin and int(row.get(f_key) or 0) == feminin:
        return False
    row[m_key] = masculin
    row[f_key] = feminin
    return True
