"""Înregistrare fonturi Unicode pentru export PDF (diacritice românești)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

FONT_REGULAR = "AppFont"
FONT_BOLD = "AppFont-Bold"
_registered = False


def _app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _candidate_fonts() -> list[tuple[str, str]]:
    root = _app_root()
    bundled = root / "resources" / "fonts"
    candidates: list[tuple[str, str]] = [
        (str(bundled / "DejaVuSans.ttf"), str(bundled / "DejaVuSans-Bold.ttf")),
    ]
    windir = os.environ.get("WINDIR", r"C:\Windows")
    win_fonts = Path(windir) / "Fonts"
    for regular, bold in [
        ("segoeui.ttf", "segoeuib.ttf"),
        ("arial.ttf", "arialbd.ttf"),
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ]:
        candidates.append((str(win_fonts / regular), str(win_fonts / bold)))
    return candidates


def register_pdf_fonts() -> tuple[str, str]:
    global _registered
    if _registered:
        return FONT_REGULAR, FONT_BOLD

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular_path, bold_path in _candidate_fonts():
        reg = Path(regular_path)
        bol = Path(bold_path)
        if not reg.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(reg)))
            if bol.is_file():
                pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bol)))
            else:
                pdfmetrics.registerFont(TTFont(FONT_BOLD, str(reg)))
            _registered = True
            logger.info("PDF font: %s", reg)
            return FONT_REGULAR, FONT_BOLD
        except Exception:
            logger.warning("Nu s-a putut înregistra fontul PDF: %s", reg, exc_info=True)

    logger.warning("Folosesc Helvetica pentru PDF — diacriticele pot lipsi")
    _registered = True
    return "Helvetica", "Helvetica-Bold"
