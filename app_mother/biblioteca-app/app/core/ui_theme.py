"""Temă UI — light / dark, persistată în app_settings."""

from __future__ import annotations

from pathlib import Path

from database.db_manager import get_setting, set_setting

SETTING_KEY = "ui_theme"
THEMES = ("light", "dark")


def get_ui_theme() -> str:
    theme = (get_setting(SETTING_KEY, "light") or "light").strip().lower()
    return theme if theme in THEMES else "light"


def set_ui_theme(theme: str) -> None:
    theme = theme.strip().lower()
    if theme not in THEMES:
        theme = "light"
    set_setting(SETTING_KEY, theme)


def stylesheet_path(app_root: Path) -> Path:
    theme = get_ui_theme()
    name = "stylesheet_dark.qss" if theme == "dark" else "stylesheet.qss"
    return app_root / "resources" / name


def load_stylesheet(app, app_root: Path) -> None:
    path = stylesheet_path(app_root)
    if not path.exists() and theme_is_dark():
        path = app_root / "resources" / "stylesheet.qss"
    if path.exists():
        app.setStyleSheet(path.read_text(encoding="utf-8"))


def theme_is_dark() -> bool:
    return get_ui_theme() == "dark"
