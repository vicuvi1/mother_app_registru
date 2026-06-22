"""Dialog scurtături tastatură."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout


SHORTCUTS_TEXT = """
<h3>Scurtături tastatură</h3>
<table cellspacing="6">
<tr><td><b>Ctrl+S</b></td><td>Salvează pagina curentă</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Exportă pagina curentă</td></tr>
<tr><td><b>Ctrl+R</b></td><td>Registru complet (overview)</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Anulează ultima editare (celulă)</td></tr>
<tr><td><b>Ctrl+,</b></td><td>Setări bibliotecă</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Ieșire</td></tr>
<tr><td><b>Ctrl+← / Ctrl+→</b></td><td>Luna anterioară / următoare</td></tr>
<tr><td><b>Ctrl+D</b></td><td>Duplică rând (părți evenimente)</td></tr>
</table>
<p style="color:#64748b">Datele se salvează automat la 60s și la schimbarea părții.</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajutor — scurtături")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        label = QLabel(SHORTCUTS_TEXT)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)
