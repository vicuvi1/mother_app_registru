"""Salvare periodică și la schimbare de pagină."""

from PyQt6.QtCore import QObject, QTimer


class AutosaveManager(QObject):
    def __init__(self, main_window, interval_seconds: int = 60) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._timer = QTimer(self)
        self._timer.setInterval(interval_seconds * 1000)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start()

    def _on_timer(self) -> None:
        if getattr(self._main_window, "_export_in_progress", False):
            return
        page = self._current_part_page()
        if page is not None and hasattr(page, "save_all"):
            page.save_all(show_status=True)

    def on_page_changed(self) -> None:
        if getattr(self._main_window, "_export_in_progress", False):
            return
        page = self._current_part_page()
        if page is not None and hasattr(page, "save_all"):
            if hasattr(page, "_debounce") and page._debounce.isActive():
                page._debounce.stop()
                page.save_all(show_status=True)
            elif getattr(page, "_dirty", False):
                page.save_all(show_status=True)

    def _current_part_page(self):
        stack = self._main_window._content_stack
        widget = stack.currentWidget()
        return widget

    def set_interval(self, seconds: int) -> None:
        self._timer.setInterval(max(10, seconds) * 1000)
