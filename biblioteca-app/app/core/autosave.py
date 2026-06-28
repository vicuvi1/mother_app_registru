"""Salvare periodică și la schimbare de pagină."""

from PyQt6.QtCore import QObject, QTimer

from database.db_manager import get_setting, set_setting

SETTING_KEY = "autosave_interval_seconds"
DEFAULT_INTERVAL = 60


def get_autosave_interval() -> int:
    """Secunde între autosalvari; 0 = dezactivat."""
    raw = get_setting(SETTING_KEY, str(DEFAULT_INTERVAL))
    try:
        return max(0, int(raw or DEFAULT_INTERVAL))
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL


def save_autosave_interval(seconds: int) -> None:
    set_setting(SETTING_KEY, str(max(0, int(seconds))))


class AutosaveManager(QObject):
    def __init__(self, main_window, interval_seconds: int | None = None) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._interval = interval_seconds if interval_seconds is not None else get_autosave_interval()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self.apply_interval(self._interval)

    def apply_interval(self, seconds: int) -> None:
        self._interval = max(0, int(seconds))
        if self._interval <= 0:
            self._timer.stop()
        else:
            self._timer.setInterval(self._interval * 1000)
            if not self._timer.isActive():
                self._timer.start()

    def set_interval(self, seconds: int) -> None:
        save_autosave_interval(seconds)
        self.apply_interval(seconds)

    def stop(self) -> None:
        self._timer.stop()

    def _on_timer(self) -> None:
        if getattr(self._main_window, "_export_in_progress", False):
            return
        page = self._current_part_page()
        if page is not None and hasattr(page, "save_all"):
            if not page.save_all(show_status=True):
                if hasattr(self._main_window, "show_save_error"):
                    self._main_window.show_save_error(
                        "Autosalvarea a eșuat. Apăsați Ctrl+S pentru a reîncerca."
                    )

    def save_leaving_page(self, page) -> None:
        """Salvează pagina părăsită (înainte de schimbarea din stack)."""
        if page is None or getattr(self._main_window, "_export_in_progress", False):
            return
        if hasattr(page, "flush_pending_save"):
            if not page.flush_pending_save():
                if hasattr(self._main_window, "show_save_error"):
                    self._main_window.show_save_error(
                        "Nu s-au putut salva modificările la schimbarea părții."
                    )
            return
        if hasattr(page, "_debounce") and page._debounce.isActive():
            page._debounce.stop()
            if hasattr(page, "save_all") and not page.save_all(show_status=True):
                if hasattr(self._main_window, "show_save_error"):
                    self._main_window.show_save_error(
                        "Nu s-au putut salva modificările la schimbarea părții."
                    )
        elif getattr(page, "_dirty", False) and hasattr(page, "save_all"):
            if not page.save_all(show_status=True):
                if hasattr(self._main_window, "show_save_error"):
                    self._main_window.show_save_error(
                        "Nu s-au putut salva modificările la schimbarea părții."
                    )

    def on_page_changed(self) -> None:
        """Compatibilitate — salvează pagina curentă (folosiți save_leaving_page înainte de switch)."""
        self.save_leaving_page(self._current_part_page())

    def _current_part_page(self):
        stack = self._main_window._content_stack
        widget = stack.currentWidget()
        return widget
