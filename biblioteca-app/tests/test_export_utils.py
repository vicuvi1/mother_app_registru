"""Teste pentru export_utils."""

import pytest

from ui.export.export_utils import (
    escape_html,
    escape_reportlab,
    format_cell_value,
    format_total_value,
    validate_page_dict,
    validate_pages,
)


def test_escape_reportlab_special_chars():
    assert escape_reportlab("A & B < C > D") == "A &amp; B &lt; C &gt; D"


def test_escape_html_special_chars():
    assert escape_html("<script>") == "&lt;script&gt;"


def test_format_cell_value_bool():
    assert format_cell_value(True) == "✓"
    assert format_cell_value(False) == ""


def test_format_total_value_types():
    assert format_total_value(42) == "42"
    assert format_total_value(42.0) == "42"
    assert format_total_value(3.5) == "3.5"
    assert format_total_value("12") == "12"
    assert format_total_value("12,5") == "12.5"
    assert format_total_value("") == ""
    assert format_total_value("abc") == ""


def test_validate_page_dict_missing_keys():
    with pytest.raises(ValueError, match="Lipsesc câmpurile"):
        validate_page_dict({})


def test_validate_page_dict_column_mismatch():
    page = {
        "headers": ["A", "B"],
        "groups": ["", ""],
        "col_keys": ["a"],
        "rows": [],
        "total_rows": [],
        "meta": {},
    }
    with pytest.raises(ValueError, match="nu corespunde"):
        validate_page_dict(page, index=0)


def test_validate_pages_empty():
    with pytest.raises(ValueError, match="Nu există pagini"):
        validate_pages([])


def test_validate_cover_page_ok():
    validate_page_dict({"type": "cover", "titlu": "Test"})
