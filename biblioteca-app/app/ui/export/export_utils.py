"""Utilitare comune pentru export — validare, formatare, escapare."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_DATA_PAGE_KEYS = ("headers", "groups", "col_keys", "rows", "total_rows", "meta")


def escape_reportlab(text: Any) -> str:
    """Escapează text pentru ReportLab Paragraph (subset XML)."""
    s = "" if text is None else str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def escape_html(text: Any) -> str:
    """Escapează text pentru HTML (previzualizare print)."""
    return html.escape("" if text is None else str(text))


def format_cell_value(val: Any) -> str:
    """Formatează o valoare de celulă pentru export."""
    if isinstance(val, bool):
        return "✓" if val else ""
    if val is None:
        return ""
    return str(val)


def format_total_value(val: Any) -> str:
    """Formatează o valoare numerică din rândurile de total."""
    if val is None or val == "":
        return ""
    if isinstance(val, bool):
        return ""
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return str(val)
    if isinstance(val, str):
        stripped = val.strip()
        if not stripped:
            return ""
        try:
            num = float(stripped.replace(",", "."))
            if num == int(num):
                return str(int(num))
            return str(num)
        except ValueError:
            return ""
    return ""


def validate_page_dict(page: dict, *, index: int | None = None) -> None:
    """Validează structura unui dict de pagină înainte de export."""
    if not isinstance(page, dict):
        prefix = _page_label(index)
        raise ValueError(f"{prefix}Pagina nu este un dicționar valid.")

    if page.get("type") == "cover":
        return

    prefix = _page_label(index)
    missing = [k for k in _DATA_PAGE_KEYS if k not in page]
    if missing:
        raise ValueError(f"{prefix}Lipsesc câmpurile: {', '.join(missing)}.")

    headers = page["headers"]
    groups = page["groups"]
    col_keys = page["col_keys"]
    rows = page["rows"]
    total_rows = page["total_rows"]
    meta = page["meta"]

    if not isinstance(headers, list) or not headers:
        raise ValueError(f"{prefix}Anteturile tabelului lipsesc sau sunt goale.")
    if not isinstance(groups, list):
        raise ValueError(f"{prefix}Grupurile de antet nu sunt valide.")
    if not isinstance(col_keys, list) or len(col_keys) != len(headers):
        raise ValueError(
            f"{prefix}Numărul de coloane ({len(col_keys)}) nu corespunde anteturilor ({len(headers)})."
        )
    if len(groups) != len(headers):
        raise ValueError(
            f"{prefix}Numărul de grupuri ({len(groups)}) nu corespunde anteturilor ({len(headers)})."
        )
    if not isinstance(rows, list):
        raise ValueError(f"{prefix}Rândurile de date nu sunt valide.")
    if not isinstance(total_rows, list):
        raise ValueError(f"{prefix}Rândurile de total nu sunt valide.")
    if not isinstance(meta, dict):
        raise ValueError(f"{prefix}Metadatele paginii lipsesc.")


def validate_pages(pages: list[dict]) -> None:
    """Validează toate paginile dintr-un export."""
    if not pages:
        raise ValueError("Nu există pagini de exportat.")
    for i, page in enumerate(pages):
        validate_page_dict(page, index=i)


def verify_export_file(out_path: Path | str) -> None:
    """Verifică că fișierul exportat există și nu este gol."""
    path = Path(out_path)
    if not path.exists():
        raise OSError(f"Fișierul nu a fost creat: {path}")
    if path.stat().st_size == 0:
        raise OSError(f"Fișierul exportat este gol: {path}")


def _page_label(index: int | None) -> str:
    if index is None:
        return ""
    return f"Pagina {index + 1}: "
