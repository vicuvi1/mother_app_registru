"""Ghid rapid PDF pentru bibliotecari — generare și deschidere."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from core.paths import get_bundle_root, get_install_root

logger = logging.getLogger(__name__)

GUIDE_FILENAME = "ghid_bibliotecar.pdf"


def guide_output_path() -> Path:
    """Locația unde se generează ghidul în surse."""
    return get_bundle_root() / "resources" / "guides" / GUIDE_FILENAME


def get_user_guide_path() -> Path | None:
    """Returnează calea către ghid dacă există (instalat sau dev)."""
    candidates = [
        get_install_root() / "docs" / GUIDE_FILENAME,
        get_bundle_root() / "resources" / "guides" / GUIDE_FILENAME,
    ]
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_file():
            return path
    return None


def open_user_guide(parent=None) -> bool:
    """Deschide ghidul PDF în aplicația implicită. Returnează True la succes."""
    path = get_user_guide_path()
    if path is None:
        if parent is not None:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(
                parent,
                "Ghid bibliotecar",
                "Ghidul PDF nu a fost găsit.\n\n"
                "Reinstalați aplicația sau rulați scripts/generate_user_guide.py.",
            )
        return False

    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except OSError as exc:
        logger.warning("Nu s-a putut deschide ghidul: %s", exc)
        if parent is not None:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.warning(parent, "Ghid bibliotecar", f"Nu s-a putut deschide fișierul:\n{exc}")
        return False
