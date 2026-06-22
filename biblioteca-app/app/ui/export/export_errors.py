"""Gestionare centralizată a erorilor la export."""

from __future__ import annotations

import errno
import logging
from pathlib import Path
from typing import Callable

from ui.export.export_excel import export_to_excel
from ui.export.export_pdf import export_to_pdf
from ui.export.export_utils import validate_pages, verify_export_file
from ui.export.export_word import export_to_word

logger = logging.getLogger(__name__)

_EXPORTERS: dict[str, Callable] = {
    "excel": export_to_excel,
    "word": export_to_word,
    "pdf": export_to_pdf,
}


def format_export_error(exc: BaseException) -> str:
    """Transformă o excepție într-un mesaj clar pentru utilizator."""
    if isinstance(exc, PermissionError):
        return "Fișierul este deschis în alt program. Închideți-l și încercați din nou."
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, OSError):
        if getattr(exc, "errno", None) == errno.ENOSPC:
            return "Spațiu insuficient pe disc. Eliberați spațiu și încercați din nou."
        msg = str(exc).strip()
        if msg:
            return msg
        return "Nu s-a putut scrie fișierul pe disc."
    return f"Nu s-a putut exporta:\n{exc}"


def run_export(fmt: str, out_path: Path | str, pages: list[dict]) -> Path:
    """Validează, exportă și verifică fișierul rezultat."""
    validate_pages(pages)
    exporter = _EXPORTERS.get(fmt)
    if exporter is None:
        raise ValueError(f"Format necunoscut: {fmt}")

    path = Path(out_path)
    logger.info("Export %s -> %s (%d pagini)", fmt, path, len(pages))
    try:
        result = exporter(path, pages)
        verify_export_file(result)
        logger.info("Export reușit: %s (%d bytes)", result, result.stat().st_size)
        return result
    except Exception:
        logger.exception("Export eșuat: %s -> %s", fmt, path)
        raise
