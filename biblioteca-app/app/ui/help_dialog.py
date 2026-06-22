"""Dialog scurtături tastatură."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout

from core.autosave import get_autosave_interval


def _autosave_hint() -> str:
    sec = get_autosave_interval()
    if sec <= 0:
        text = "Autosalvarea este dezactivată"
    elif sec < 60:
        text = f"Datele se salvează automat la {sec}s și la schimbarea părții"
    elif sec % 60 == 0:
        text = f"Datele se salvează automat la {sec // 60} min și la schimbarea părții"
    else:
        text = f"Datele se salvează automat la {sec}s și la schimbarea părții"
    return f"<p style='color:#64748b'>{text}.</p>"


SHORTCUTS_HEADER = """
<h3>Scurtături tastatură</h3>
<table cellspacing="6">
<tr><td><b>Ctrl+S</b></td><td>Salvează pagina curentă</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Exportă pagina curentă</td></tr>
<tr><td><b>Ctrl+R</b></td><td>Registru complet (overview)</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Anulează ultimele editări (până la 10 pași)</td></tr>
<tr><td><b>Ctrl+,</b></td><td>Setări bibliotecă</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Ieșire</td></tr>
<tr><td><b>Ctrl+← / Ctrl+→</b></td><td>Luna anterioară / următoare</td></tr>
<tr><td><b>Ctrl+D</b></td><td>Duplică rând (părți evenimente)</td></tr>
</table>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajutor — scurtături")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        label = QLabel(SHORTCUTS_HEADER + _autosave_hint())
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)
