"""Legătura Copii până la 16 ani = Preșcolari + Elevi (Partea I)."""

from __future__ import annotations

from typing import Any

COPII_PANA_16 = "copii_pana_16"
PRESCOLARI = "prescolari"
ELEVI = "elevi"
COPII_SPLIT_KEYS = (COPII_PANA_16, PRESCOLARI, ELEVI)


def copii_split_sum(row: dict[str, Any]) -> int:
    return max(0, int(row.get(PRESCOLARI) or 0)) + max(0, int(row.get(ELEVI) or 0))


def reconcile_copii_row(row: dict[str, Any]) -> bool:
    """Ajustează rândul inconsistent: copii = preșcolari + elevi (păstrează copii dacă e posibil)."""
    copii = max(0, int(row.get(COPII_PANA_16) or 0))
    prescolari = max(0, int(row.get(PRESCOLARI) or 0))
    elevi = max(0, int(row.get(ELEVI) or 0))
    if prescolari + elevi == copii:
        return False
    if copii >= prescolari:
        row[ELEVI] = max(0, copii - prescolari)
    else:
        row[COPII_PANA_16] = prescolari + elevi
    return True


def apply_copii_split_edit(row: dict[str, Any], edited_key: str) -> bool:
    """
    Propagă editarea între copii / preșcolari / elevi.

    - Elevi sau Copii: copii = preșcolari + elevi
    - Preșcolari: copii rămâne, elevi = copii − preșcolari
    """
    if edited_key not in COPII_SPLIT_KEYS:
        return False

    prescolari = max(0, int(row.get(PRESCOLARI) or 0))
    elevi = max(0, int(row.get(ELEVI) or 0))
    copii = max(0, int(row.get(COPII_PANA_16) or 0))
    changed = False

    if edited_key == PRESCOLARI:
        prescolari = max(0, int(row.get(PRESCOLARI) or 0))
        if copii > 0:
            new_elevi = max(0, copii - prescolari)
            if elevi != new_elevi:
                row[ELEVI] = new_elevi
                changed = True
        else:
            new_copii = prescolari + elevi
            if copii != new_copii:
                row[COPII_PANA_16] = new_copii
                changed = True
    elif edited_key == ELEVI:
        elevi = max(0, int(row.get(ELEVI) or 0))
        new_copii = prescolari + elevi
        if copii != new_copii:
            row[COPII_PANA_16] = new_copii
            changed = True
    elif edited_key == COPII_PANA_16:
        copii = max(0, int(row.get(COPII_PANA_16) or 0))
        new_elevi = max(0, copii - prescolari)
        if elevi != new_elevi:
            row[ELEVI] = new_elevi
            changed = True

    return changed


def validate_copii_split_value(
    row: dict[str, Any], column_key: str, new_value: int
) -> tuple[bool, str]:
    if column_key not in COPII_SPLIT_KEYS:
        return True, ""
    try:
        num = max(0, int(new_value))
    except (TypeError, ValueError):
        return False, "Doar numere întregi ≥ 0"

    trial = dict(row)
    trial[column_key] = num
    if column_key == PRESCOLARI:
        copii = max(0, int(trial.get(COPII_PANA_16) or 0))
        if copii > 0 and num > copii:
            return (
                False,
                f"Preșcolari ({num}) nu poate depăși Copii până la 16 ani ({copii}).",
            )
    return True, ""
