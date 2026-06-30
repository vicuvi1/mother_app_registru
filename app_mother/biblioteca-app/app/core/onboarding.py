"""Stare tur ghidat prima utilizare."""

from database.db_manager import get_setting, set_setting

SETTING_KEY = "onboarding_tour_completed"


def is_onboarding_completed() -> bool:
    return get_setting(SETTING_KEY, "0") == "1"


def mark_onboarding_completed() -> None:
    set_setting(SETTING_KEY, "1")
