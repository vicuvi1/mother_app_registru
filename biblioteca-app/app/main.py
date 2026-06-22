"""Punct de pornire — inițializează DB și UI."""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import QApplication

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.logging_config import setup_logging  # noqa: E402
from database.db_manager import init_database, is_first_run  # noqa: E402
from database.integrity import check_database_integrity, offer_restore_on_corruption  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.setup_wizard import SetupWizard  # noqa: E402
from ui.splash_screen import SplashScreen  # noqa: E402


def _load_stylesheet(app: QApplication) -> None:
    qss_path = APP_ROOT / "resources" / "stylesheet.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def _center_on_screen(widget) -> None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    frame = widget.frameGeometry()
    frame.moveCenter(geo.center())
    widget.move(frame.topLeft())


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Registru Digital Bibliotecă")
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)
    _load_stylesheet(app)

    splash = SplashScreen()
    _center_on_screen(splash)
    splash.show()
    app.processEvents()

    splash.set_message("Inițializare jurnal")
    setup_logging()

    splash.set_message("Pregătire bază de date")
    splash.set_progress(25, 100)
    init_database(seed=True)

    splash.set_message("Verificare integritate")
    splash.set_progress(35, 100)
    ok, detail = check_database_integrity()
    if not ok:
        splash.hide()
        if not offer_restore_on_corruption():
            return 0
        splash.show()
        _center_on_screen(splash)
        app.processEvents()

    if is_first_run():
        splash.hide()
        wizard = SetupWizard(first_run=True)
        if wizard.exec() != wizard.DialogCode.Accepted:
            return 0
        splash.show()
        _center_on_screen(splash)
        app.processEvents()

    splash.set_message("Construire interfață")
    splash.set_progress(55, 100)
    window = MainWindow(load_first_part=False)

    splash.set_message("Încărcare registru")
    splash.set_progress(80, 100)
    window.load_initial_part()
    app.processEvents()

    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
