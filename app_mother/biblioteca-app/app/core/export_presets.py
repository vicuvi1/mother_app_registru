"""Preseturi export și print — folder, orientare."""

from __future__ import annotations

from pathlib import Path

from database.db_manager import get_setting, set_setting

KEY_EXPORT_FOLDER = "export_last_folder"
KEY_PRINT_ORIENTATION = "print_orientation"


def get_export_folder() -> str:
    return get_setting(KEY_EXPORT_FOLDER, "") or ""


def set_export_folder(path: str | Path) -> None:
    folder = Path(path)
    if folder.is_file():
        folder = folder.parent
    set_setting(KEY_EXPORT_FOLDER, str(folder.resolve()))


def suggest_export_path(filename: str) -> str:
    folder = get_export_folder()
    if folder:
        return str(Path(folder) / filename)
    return filename


def get_print_orientation() -> str:
    val = (get_setting(KEY_PRINT_ORIENTATION, "landscape") or "landscape").lower()
    return "portrait" if val == "portrait" else "landscape"


def set_print_orientation(orientation: str) -> None:
    val = "portrait" if orientation.lower() == "portrait" else "landscape"
    set_setting(KEY_PRINT_ORIENTATION, val)
