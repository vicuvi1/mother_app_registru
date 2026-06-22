"""Copiere backup în folder sincronizat (OneDrive / Dropbox etc.)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from database.db_manager import get_setting, set_setting

logger = logging.getLogger(__name__)

KEY_ENABLED = "cloud_backup_enabled"
KEY_TARGET = "cloud_backup_target"
KEY_KEEP = "cloud_backup_keep_count"
DEFAULT_KEEP = 10


def is_cloud_backup_enabled() -> bool:
    return get_setting(KEY_ENABLED, "0") == "1"


def set_cloud_backup_enabled(enabled: bool) -> None:
    set_setting(KEY_ENABLED, "1" if enabled else "0")


def get_cloud_backup_target() -> str:
    return get_setting(KEY_TARGET, "") or ""


def set_cloud_backup_target(path: str) -> None:
    set_setting(KEY_TARGET, str(path).strip())


def get_cloud_backup_keep_count() -> int:
    try:
        return max(1, int(get_setting(KEY_KEEP, str(DEFAULT_KEEP)) or DEFAULT_KEEP))
    except (TypeError, ValueError):
        return DEFAULT_KEEP


def set_cloud_backup_keep_count(count: int) -> None:
    set_setting(KEY_KEEP, str(max(1, int(count))))


def maybe_sync_backup(backup_path: Path) -> Path | None:
    """Copiază backup-ul în folderul cloud dacă e activat. Returnează destinația sau None."""
    if not is_cloud_backup_enabled():
        return None
    target = get_cloud_backup_target().strip()
    if not target:
        logger.warning("Cloud backup activat dar fără folder țintă")
        return None
    dest_dir = Path(target)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / backup_path.name
        shutil.copy2(backup_path, dest)
        _prune_cloud_backups(dest_dir, backup_path.suffix)
        logger.info("Backup sincronizat în cloud folder: %s", dest)
        return dest
    except OSError:
        logger.exception("Sincronizare cloud backup eșuată: %s", dest_dir)
        return None


def _prune_cloud_backups(dest_dir: Path, suffix: str) -> None:
    keep = get_cloud_backup_keep_count()
    patterns = ("biblioteca_*.db", "biblioteca_*.db.enc")
    files: list[Path] = []
    for pat in patterns:
        files.extend(dest_dir.glob(pat))
    files = sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            logger.warning("Nu s-a putut șterge backup cloud vechi: %s", old)
