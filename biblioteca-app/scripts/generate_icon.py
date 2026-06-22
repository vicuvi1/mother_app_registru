"""Generează app/resources/registru.ico și registru.png (PyQt6)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
OUT_PNG = ROOT / "app" / "resources" / "registru.png"
OUT_ICO = ROOT / "app" / "resources" / "registru.ico"


def _render_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", int(size * 0.46), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "R")
    painter.end()
    return pm


def _write_ico(path: Path, pixmap: QPixmap) -> None:
    icon = QIcon(pixmap)
    if not icon.isNull():
        icon.pixmap(256, 256).save(str(path), "ICO")


def main() -> None:
    app = QApplication(sys.argv)
    pm = _render_pixmap(256)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    pm.save(str(OUT_PNG), "PNG")

  # Fallback ICO: embed PNG manually if Qt ICO save fails on some builds
    try:
        _write_ico(OUT_ICO, pm)
        if not OUT_ICO.exists() or OUT_ICO.stat().st_size < 100:
            raise OSError("ICO too small")
    except OSError:
        png_bytes = OUT_PNG.read_bytes()
        header = struct.pack("<HHH", 0, 1, 1)
        entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 256, 256, len(png_bytes), 22)
        OUT_ICO.write_bytes(header + entry + png_bytes)

    print(f"Created {OUT_PNG} and {OUT_ICO}")
    app.quit()


if __name__ == "__main__":
    main()
