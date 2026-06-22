"""Punct de pornire — inițializează DB și UI."""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.logging_config import setup_logging  # noqa: E402
from database.db_manager import init_database, is_first_run  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.setup_wizard import SetupWizard  # noqa: E402


def _load_stylesheet(app: QApplication) -> None:
    qss_path = APP_ROOT / "resources" / "stylesheet.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    setup_logging()
    init_database(seed=True)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Registru Digital Bibliotecă")
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)
    _load_stylesheet(app)

    if is_first_run():
        wizard = SetupWizard(first_run=True)
        if wizard.exec() != wizard.DialogCode.Accepted:
            return 0

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
