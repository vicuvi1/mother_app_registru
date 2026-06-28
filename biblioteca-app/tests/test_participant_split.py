from core.participant_split import (
    apply_participant_gender_split,
    default_gender_split,
    validate_participant_gender_value,
)


def test_default_gender_split_even():
    assert default_gender_split(10) == (5, 5)
    assert default_gender_split(11) == (6, 5)
    assert default_gender_split(0) == (0, 0)


def test_apply_participant_gender_split_updates_row():
    row = {"numar_participanti": 7, "participanti_masculin": 0, "participanti_feminin": 0}
    assert apply_participant_gender_split(
        row,
        total_key="numar_participanti",
        m_key="participanti_masculin",
        f_key="participanti_feminin",
    )
    assert row["participanti_masculin"] + row["participanti_feminin"] == 7


def test_validate_participant_gender_rejects_overflow():
    row = {"numar_participanti": 5, "participanti_masculin": 3, "participanti_feminin": 2}
    ok, msg = validate_participant_gender_value(
        row,
        "participanti_feminin",
        3,
        total_key="numar_participanti",
        m_key="participanti_masculin",
        f_key="participanti_feminin",
    )
    assert not ok
    assert "depășește" in msg


def test_validate_participant_gender_allows_when_total_zero():
    row = {"numar_participanti": 0, "participanti_masculin": 0, "participanti_feminin": 0}
    ok, _ = validate_participant_gender_value(
        row,
        "participanti_masculin",
        4,
        total_key="numar_participanti",
        m_key="participanti_masculin",
        f_key="participanti_feminin",
    )
    assert ok
