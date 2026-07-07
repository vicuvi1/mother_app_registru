"""Gestionare centralizată a erorilor la export."""

from __future__ import annotations

import errno
import logging
from pathlib import Path
from typing import Callable

from ui.export.export_utils import validate_pages, verify_export_file

logger = logging.getLogger(__name__)

_EXPORTERS: dict[str, Callable] | None = None


def _get_exporters() -> dict[str, Callable]:
    global _EXPORTERS
    if _EXPORTERS is None:
        from ui.export.export_excel import export_to_excel
        from ui.export.export_pdf import export_to_pdf
        from ui.export.export_word import export_to_word

        _EXPORTERS = {
            "excel": export_to_excel,
            "word": export_to_word,
            "pdf": export_to_pdf,
        }
    return _EXPORTERS


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


def run_export(
    fmt: str,
    out_path: Path | str,
    pages: list[dict],
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> Path:
    """Validează, exportă și verifică fișierul rezultat."""
    if progress_callback:
        progress_callback("Validare pagini…")
    validate_pages(pages)
    exporters = _get_exporters()
    exporter = exporters.get(fmt)
    if exporter is None:
        raise ValueError(f"Format necunoscut: {fmt}")

    path = Path(out_path)
    logger.info("Export %s -> %s (%d pagini)", fmt, path, len(pages))
    try:
        if progress_callback:
            progress_callback(f"Generare {fmt.upper()}…")
        result = exporter(path, pages)
        if progress_callback:
            progress_callback("Verificare fișier…")
        verify_export_file(result)
        logger.info("Export reușit: %s (%d bytes)", result, result.stat().st_size)
        return result
    except Exception:
        logger.exception("Export eșuat: %s -> %s", fmt, path)
        raise


def run_export_with_progress(
    parent,
    fmt: str,
    out_path: Path | str,
    pages: list[dict],
    *,
    main_window=None,
    title: str = "Export",
) -> Path:
    """Export cu dialog de progres (blocare UI minimă)."""
    from PyQt5.QtWidgets import QApplication, QProgressDialog

    if main_window is not None:
        main_window._export_in_progress = True

    progress = None
    try:
        progress = QProgressDialog("Se generează exportul…", None, 0, 0, parent)
        progress.setWindowTitle(title)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        def on_progress(msg: str) -> None:
            if progress is not None:
                progress.setLabelText(msg)
                QApplication.processEvents()

        return run_export(fmt, out_path, pages, progress_callback=on_progress)
    finally:
        if progress is not None:
            progress.close()
        if main_window is not None:
            main_window._export_in_progress = False
