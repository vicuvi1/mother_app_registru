"""Repornire aplicație (după restaurare DB etc.)."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def _restart_command() -> tuple[str, list[str]]:
    if getattr(sys, "frozen", False):
        return sys.executable, sys.argv[1:]
    return sys.executable, sys.argv


def restart_application() -> None:
    """Pornește o nouă instanță și închide procesul curent."""
    from PyQt6.QtCore import QProcess
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return

    program, args = _restart_command()
    if QProcess.startDetached(program, args):
        logger.info("Repornire aplicație: %s %s", program, args)
        app.quit()
        return

    logger.warning("QProcess.startDetached a eșuat — fallback os.execv")
    try:
        import os

        os.execv(program, [program, *args])
    except OSError:
        logger.exception("Repornire aplicație eșuată")
