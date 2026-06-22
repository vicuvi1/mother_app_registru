"""Teste Sprint II — progres părți, badge-uri, onboarding."""

import pytest

from core import part_progress as pp_mod
from core.part_progress import (
    STATUS_ATTENTION,
    STATUS_COMPLETE,
    STATUS_EMPTY,
    PartProgress,
    compute_part_progress,
    count_summary,
)
from core.register_audit import IncompleteSlot


def test_part_progress_badges():
    assert PartProgress("p", "I", "Ev", STATUS_COMPLETE, 0, 12).badge == "✓"
    assert PartProgress("p", "II", "Ev", STATUS_ATTENTION, 3, 12).badge == "⚠"
    assert PartProgress("p", "III", "Ev", STATUS_EMPTY, 12, 12).badge == "·"


def test_count_summary():
    progress = {
        "a": PartProgress("a", "I", "A", STATUS_COMPLETE, 0, 12),
        "b": PartProgress("b", "II", "B", STATUS_ATTENTION, 2, 12),
        "c": PartProgress("c", "III", "C", STATUS_EMPTY, 12, 12),
        "d": PartProgress("d", "IV", "D", STATUS_COMPLETE, 0, 1),
    }
    assert count_summary(progress) == (2, 1, 1)


def test_compute_part_progress_daily_complete(monkeypatch):
    monkeypatch.setattr(pp_mod, "find_incomplete_months", lambda _year: [])
    progress = compute_part_progress(2026)
    part01 = progress.get("part_01")
    assert part01 is not None
    assert part01.status == STATUS_COMPLETE
    assert part01.badge == "✓"


def test_compute_part_progress_daily_attention(monkeypatch):
    slots = [
        IncompleteSlot(
            part_id="part_01",
            roman="I",
            title="Evidența utilizatorilor",
            month=1,
            category=None,
            label="Ian 2026",
            reason="missing",
        )
    ]
    monkeypatch.setattr(pp_mod, "find_incomplete_months", lambda _year: slots)
    progress = compute_part_progress(2026)
    assert progress["part_01"].status == STATUS_ATTENTION


def test_compute_part_progress_daily_empty(monkeypatch):
    slots = [
        IncompleteSlot(
            part_id="part_01",
            roman="I",
            title="Evidența utilizatorilor",
            month=m,
            category=None,
            label=f"Luna {m}",
            reason="missing",
        )
        for m in range(1, 13)
    ]
    monkeypatch.setattr(pp_mod, "find_incomplete_months", lambda _year: slots)
    progress = compute_part_progress(2026)
    assert progress["part_01"].status == STATUS_EMPTY


def test_onboarding_setting_roundtrip(monkeypatch):
    store: dict[str, str] = {}

    monkeypatch.setattr(
        "core.onboarding.get_setting",
        lambda key, default="0": store.get(key, default),
    )
    monkeypatch.setattr(
        "core.onboarding.set_setting",
        lambda key, value: store.update({key: value}),
    )

    from core.onboarding import is_onboarding_completed, mark_onboarding_completed

    assert is_onboarding_completed() is False
    mark_onboarding_completed()
    assert is_onboarding_completed() is True


def test_onboarding_tour_has_five_steps(qapp):
    from ui.onboarding_tour import OnboardingTourDialog, _STEPS

    assert len(_STEPS) == 5
    dlg = OnboardingTourDialog()
    assert dlg._stack.count() == 5
