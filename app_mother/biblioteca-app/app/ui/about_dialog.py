"""Dialog Despre aplicație."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout

from core.constants_manager import APP_AUTHOR, APP_CREDIT
from core.version import APP_VERSION, BUILD_DATE


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Despre")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Registru Digital de Evidență a Activității Bibliotecii")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        version = QLabel(f"Versiune {APP_VERSION} · {BUILD_DATE}")
        version.setStyleSheet("color: #64748b;")
        layout.addWidget(version)

        body = QLabel(
            "<p>Aplicație desktop offline pentru evidența activității bibliotecilor publice "
            "(12 părți ale registrului, export Word/PDF/Excel, backup automat).</p>"
            f"<p>{APP_CREDIT}</p>"
            f"<p style='color:#64748b'>© {APP_AUTHOR}</p>"
        )
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setOpenExternalLinks(True)
        layout.addWidget(body)
