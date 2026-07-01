"""Ecran de pornire animat — afișat în timpul inițializării aplicației."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QProgressBar, QVBoxLayout, QWidget


class SplashScreen(QWidget):
    """Splash frameless cu animație puncte și bară de progres."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(480, 320)
        self.setObjectName("splashScreen")
        self.setStyleSheet(
            """
            QWidget#splashScreen {
                background-color: #1e3a5f;
                border-radius: 16px;
                border: 1px solid #334155;
            }
            QLabel#splashLogo { font-size: 52px; }
            QLabel#splashTitle {
                color: #f8fafc;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#splashSubtitle {
                color: #94a3b8;
                font-size: 13px;
            }
            QLabel#splashStatus {
                color: #cbd5e1;
                font-size: 12px;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #334155;
                height: 6px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: #60a5fa;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 32)
        layout.setSpacing(8)

        logo = QLabel("📚")
        logo.setObjectName("splashLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("Registru Digital")
        title.setObjectName("splashTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Evidența activității bibliotecii")
        subtitle.setObjectName("splashSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(24)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._status = QLabel("Se pornește aplicația")
        self._status.setObjectName("splashStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        self._base_message = "Se pornește aplicația"
        self._dot_index = 0
        self._timer = QTimer(self)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._tick_dots)
        self._timer.start()

    def _tick_dots(self) -> None:
        self._dot_index = (self._dot_index + 1) % 4
        dots = "." * self._dot_index
        self._status.setText(f"{self._base_message}{dots}")
        QApplication.processEvents()

    def set_message(self, text: str) -> None:
        self._base_message = text.rstrip(".")
        self._status.setText(self._base_message)
        QApplication.processEvents()

    def set_progress(self, value: int, maximum: int = 100) -> None:
        if maximum <= 0:
            self._progress.setRange(0, 0)
        else:
            self._progress.setRange(0, maximum)
            self._progress.setValue(value)
        QApplication.processEvents()

    def finish(self, window: QMainWindow) -> None:
        self._timer.stop()
        self.set_message("Gata")
        self.set_progress(100, 100)
        window.show()
        window.raise_()
        window.activateWindow()
        self.close()
