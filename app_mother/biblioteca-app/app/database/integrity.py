"""Verificare integritate SQLite și recuperare din backup."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox

from database.backup import list_backups, restore_backup
from database.db_manager import DB_PATH

logger = logging.getLogger(__name__)


def check_database_integrity() -> tuple[bool, str]:
    """Rulează PRAGMA integrity_check. Returnează (ok, mesaj)."""
    if not DB_PATH.exists():
        return True, "ok"
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            msg = row[0] if row else "unknown"
    except sqlite3.Error as exc:
        logger.exception("integrity_check eșuat")
        return False, str(exc)
    return msg == "ok", msg


def offer_restore_on_corruption(parent=None) -> bool:
    """Dialog: restaurare din ultimul backup auto sau ieșire. True = continuă."""
    backups = [p for p in list_backups() if "auto" in p.name]
    if not backups:
        backups = list_backups()
    latest = backups[0] if backups else None

    if latest is None:
        reply = QMessageBox.critical(
            parent,
            "Bază de date deteriorată",
            "Verificarea integrității a eșuat și nu există copii de rezervă.\n\n"
            "Aplicația nu poate continua în siguranță.",
            QMessageBox.Ok,
        )
        return False

    reply = QMessageBox.warning(
        parent,
        "Bază de date deteriorată",
        "Verificarea integrității bazei de date a eșuat.\n\n"
        f"Restaurați din ultima copie automată?\n{latest.name}\n\n"
        "Aplicația va reporni după restaurare.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if reply != QMessageBox.Yes:
        return False

    try:
        restore_backup(latest)
    except OSError as exc:
        QMessageBox.critical(
            parent,
            "Restaurare eșuată",
            f"Nu s-a putut restaura copia:\n{exc}",
        )
        return False

    from core.app_restart import restart_application

    restart_application()
    return False
