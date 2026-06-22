"""Teste pentru export PDF — caractere speciale și rânduri goale."""

import tempfile
from pathlib import Path

from ui.export.export_pdf import export_to_pdf


def _sample_page(*, rows=None, meta=None, total_rows=None):
    return {
        "headers": ["Data", "Adulți"],
        "groups": ["", ""],
        "col_keys": ["data", "adulti"],
        "rows": rows if rows is not None else [{"data": "01.01", "adulti": 5}],
        "total_rows": total_rows if total_rows is not None else [("Total", {"adulti": 5})],
        "meta": meta or {
            "nume_biblioteca": "Biblioteca <Test> & Co",
            "localitate": "București",
            "parte_roman": "I",
            "title": "Evidența utilizatorilor",
            "luna_name": "Ianuarie",
            "an": 2025,
        },
    }


def test_export_pdf_special_characters_in_meta():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.pdf"
        export_to_pdf(out, [_sample_page()])
        assert out.exists()
        assert out.stat().st_size > 0


def test_export_pdf_empty_rows():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "empty.pdf"
        export_to_pdf(out, [_sample_page(rows=[], total_rows=[("Total", {"adulti": 0})])])
        assert out.exists()
        assert out.stat().st_size > 0


def test_export_pdf_float_total():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "float.pdf"
        page = _sample_page(
            rows=[{"data": "01.01", "adulti": 3}],
            meta={
                "parte_roman": "I",
                "title": "Test",
                "an": 2025,
            },
        )
        page["total_rows"] = [("Total", {"adulti": 12.5})]
        export_to_pdf(out, [page])
        assert out.exists()
