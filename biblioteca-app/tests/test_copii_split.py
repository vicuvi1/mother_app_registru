from core.copii_split import (
    apply_copii_split_edit,
    copii_split_sum,
    reconcile_copii_row,
    validate_copii_split_value,
)


def test_elevi_updates_copii_when_prescolari_zero():
    row = {"copii_pana_16": 0, "prescolari": 0, "elevi": 0}
    row["elevi"] = 12
    apply_copii_split_edit(row, "elevi")
    assert row["copii_pana_16"] == 12
    assert row["elevi"] == 12


def test_copii_updates_elevi_when_prescolari_zero():
    row = {"copii_pana_16": 15, "prescolari": 0, "elevi": 0}
    apply_copii_split_edit(row, "copii_pana_16")
    assert row["elevi"] == 15
    assert copii_split_sum(row) == 15


def test_prescolari_subtracts_from_elevi_keeps_copii():
    row = {"copii_pana_16": 20, "prescolari": 0, "elevi": 20}
    row["prescolari"] = 5
    apply_copii_split_edit(row, "prescolari")
    assert row["copii_pana_16"] == 20
    assert row["elevi"] == 15
    assert copii_split_sum(row) == 20


def test_prescolari_cannot_exceed_copii():
    row = {"copii_pana_16": 10, "prescolari": 0, "elevi": 10}
    ok, msg = validate_copii_split_value(row, "prescolari", 12)
    assert not ok
    assert "depăși" in msg


def test_reconcile_fixes_inconsistent_row():
    row = {"copii_pana_16": 3, "prescolari": 0, "elevi": 16}
    assert reconcile_copii_row(row)
    assert row["elevi"] == 3
    assert row["copii_pana_16"] == 3


def test_gen_part01_prescolari_zero_elevi_equals_copii():
    from core.random_engine import _gen_part01_row

    for _ in range(30):
        row = _gen_part01_row({})
        assert row["prescolari"] == 0
        assert row["elevi"] == row["copii_pana_16"]
