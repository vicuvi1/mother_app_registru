"""Teste pentru date_engine."""

from datetime import date

from core.date_engine import (
    format_dd_mm,
    get_working_days,
    is_working_day,
    sort_dates_dd_mm,
    validate_date_format,
)


def test_validate_date_format_valid():
    assert validate_date_format("01.01")
    assert validate_date_format("29.02")  # valid format (day check uses neutral year)


def test_validate_date_format_invalid():
    assert not validate_date_format("32.01")
    assert not validate_date_format("01.13")
    assert not validate_date_format("1.1")
    assert not validate_date_format("abc")


def test_is_working_day():
    assert is_working_day(date(2025, 6, 16))  # Monday
    assert not is_working_day(date(2025, 6, 21))  # Saturday


def test_get_working_days_excludes_weekends():
    days = get_working_days(2025, 1)
    for d in days:
        day, month = map(int, d.split("."))
        assert date(2025, month, day).weekday() < 5


def test_get_working_days_excludes_custom():
    days = get_working_days(2025, 1, excluded_dates=["02.01"])
    assert "02.01" not in days


def test_sort_dates_dd_mm():
    assert sort_dates_dd_mm(["15.03", "01.02", "10.01"], 2025) == ["10.01", "01.02", "15.03"]


def test_format_dd_mm():
    assert format_dd_mm(date(2025, 3, 5)) == "05.03"
