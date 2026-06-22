"""Backup și restaurare bază de date SQLite."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from database.db_manager import DATA_DIR, DB_PATH, get_engine

logger = logging.getLogger(__name__)

BACKUP_DIR = DATA_DIR / "backups"
MAX_AUTO_BACKUPS = 5


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup(label: str = "manual") -> Path:
    """Copiază biblioteca.db în folderul backups/."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Baza de date nu există: {DB_PATH}")

    ensure_backup_dir()
    dest = BACKUP_DIR / f"biblioteca_{label}_{_timestamp()}.db"
    shutil.copy2(DB_PATH, dest)
    logger.info("Backup creat: %s", dest)
    return dest


def auto_backup_on_startup() -> Path | None:
    """Backup automat la pornire (păstrează ultimele MAX_AUTO_BACKUPS)."""
    if not DB_PATH.exists():
        return None
    try:
        path = create_backup("auto")
        _prune_old_backups("auto")
        return path
    except OSError:
        logger.exception("Backup automat eșuat")
        return None


def _prune_old_backups(prefix: str) -> None:
    files = sorted(
        BACKUP_DIR.glob(f"biblioteca_{prefix}_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[MAX_AUTO_BACKUPS:]:
        try:
            old.unlink()
            logger.info("Backup vechi șters: %s", old)
        except OSError:
            logger.warning("Nu s-a putut șterge backup: %s", old)


def list_backups() -> list[Path]:
    ensure_backup_dir()
    return sorted(BACKUP_DIR.glob("biblioteca_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(backup_path: Path) -> None:
    """Restaurează din copie (închide conexiunile active mai întâi)."""
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(str(backup_path))

    engine = get_engine()
    engine.dispose()

    if DB_PATH.exists():
        pre_restore = BACKUP_DIR / f"biblioteca_prerestore_{_timestamp()}.db"
        ensure_backup_dir()
        shutil.copy2(DB_PATH, pre_restore)

    shutil.copy2(backup_path, DB_PATH)
    logger.info("Bază de date restaurată din %s", backup_path)
