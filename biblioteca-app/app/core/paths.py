"""Căi aplicație — mod portabil (USB) și bundle PyInstaller."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_bundle_root() -> Path:
    """Resurse read-only (QSS, fonturi) — în exe: _internal sau _MEIPASS."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).parent / "_internal"
    return Path(__file__).resolve().parent.parent


def get_install_root() -> Path:
    """Folderul aplicației — lângă RegistruDigital.exe (portabil USB)."""
    if is_frozen():
        return Path(sys.executable).parent.resolve()
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """Date utilizator: biblioteca.db, backups/, session.json — lângă exe când e frozen."""
    override = os.environ.get("BIBLIOTECA_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return get_install_root() / "data"


def is_portable_mode() -> bool:
    """True când datele stau în data/ lângă executabil."""
    return get_data_dir().parent == get_install_root()
