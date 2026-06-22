"""Backup și restaurare bază de date SQLite (+ criptare opțională, cloud)."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from core.backup_crypto import decrypt_file, encrypt_file, is_encrypted_backup
from core.cloud_backup import maybe_sync_backup
from database.db_manager import DATA_DIR, DB_PATH, get_engine, get_setting

logger = logging.getLogger(__name__)

BACKUP_DIR = DATA_DIR / "backups"
MAX_AUTO_BACKUPS = 5
SETTING_ENCRYPT = "backup_encrypt_enabled"


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def is_encrypt_backups_enabled() -> bool:
    return get_setting(SETTING_ENCRYPT, "0") == "1"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _checkpoint_wal() -> None:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            conn.commit()
    except OSError:
        logger.warning("Checkpoint WAL eșuat", exc_info=True)


def _copy_database_safe(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _checkpoint_wal()
        with sqlite3.connect(str(source)) as src_conn:
            with sqlite3.connect(str(dest)) as dest_conn:
                src_conn.backup(dest_conn)
        return
    except (sqlite3.Error, OSError):
        logger.warning("Backup SQLite API eșuat pentru %s — fallback copy2", source, exc_info=True)
    shutil.copy2(source, dest)


def create_backup(label: str = "manual", *, passphrase: str | None = None) -> Path:
    """Salvează biblioteca.db în backups/. Opțional criptat (.db.enc)."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Baza de date nu există: {DB_PATH}")

    ensure_backup_dir()
    use_encrypt = bool(passphrase) or (
        passphrase is None and is_encrypt_backups_enabled() and label in ("manual", "year_end")
    )
    if use_encrypt and not passphrase:
        raise ValueError("Parola necesară pentru backup criptat.")

    ext = "db.enc" if use_encrypt else "db"
    dest = BACKUP_DIR / f"biblioteca_{label}_{_timestamp()}.{ext}"

    if use_encrypt:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _copy_database_safe(DB_PATH, tmp_path)
            encrypt_file(tmp_path, dest, passphrase or "")
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        _copy_database_safe(DB_PATH, dest)

    logger.info("Backup creat: %s", dest)
    maybe_sync_backup(dest)
    return dest


def auto_backup_on_startup() -> Path | None:
    if not DB_PATH.exists():
        return None
    try:
        path = create_backup("auto")
        _prune_old_backups("auto")
        return path
    except (OSError, ValueError):
        logger.exception("Backup automat eșuat")
        return None


def _prune_old_backups(prefix: str) -> None:
    files = sorted(
        list(BACKUP_DIR.glob(f"biblioteca_{prefix}_*.db"))
        + list(BACKUP_DIR.glob(f"biblioteca_{prefix}_*.db.enc")),
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
    files = list(BACKUP_DIR.glob("biblioteca_*.db")) + list(BACKUP_DIR.glob("biblioteca_*.db.enc"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(backup_path: Path, *, passphrase: str | None = None) -> Path | None:
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(str(backup_path))

    source_db = backup_path
    temp_plain: Path | None = None
    if is_encrypted_backup(backup_path) or backup_path.suffix == ".enc":
        if not passphrase:
            raise ValueError("Parola necesară pentru restaurare din backup criptat.")
        temp_plain = Path(tempfile.mkstemp(suffix=".db")[1])
        decrypt_file(backup_path, temp_plain, passphrase)
        source_db = temp_plain

    engine = get_engine()
    engine.dispose()

    pre_restore: Path | None = None
    if DB_PATH.exists():
        pre_restore = BACKUP_DIR / f"biblioteca_prerestore_{_timestamp()}.db"
        ensure_backup_dir()
        _copy_database_safe(DB_PATH, pre_restore)
        logger.info("Copie pre-restaurare: %s", pre_restore)

    try:
        _copy_database_safe(source_db, DB_PATH)
        logger.info("Bază de date restaurată din %s", backup_path)
        return pre_restore
    finally:
        if temp_plain is not None:
            temp_plain.unlink(missing_ok=True)
