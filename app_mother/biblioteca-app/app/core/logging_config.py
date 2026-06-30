"""Configurare logging — fișier rotativ în data/."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from core.paths import get_data_dir

LOG_DIR = get_data_dir()
LOG_FILE = LOG_DIR / "biblioteca.log"


def setup_logging() -> None:
    """Inițializează logging la pornirea aplicației."""
    level_name = os.environ.get("BIBLIOTECA_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    logging.getLogger(__name__).info("Logging inițializat (%s)", LOG_FILE)
