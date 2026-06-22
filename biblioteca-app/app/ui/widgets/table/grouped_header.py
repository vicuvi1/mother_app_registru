"""Antet tabel cu grupuri de coloane."""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QHeaderView

HEADER_BG = QColor("#eef2f7")
GROUP_BG = QColor("#dbe3ee")
HEADER_BORDER = QColor("#b6c2d4")
HEADER_TEXT = QColor("#1e293b")


class GroupedHeaderView(QHeaderView):
    """Antet pe două niveluri: bandă de grup (subgrupă) deasupra etichetei coloanei."""

    GROUP_H = 30

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._labels: list[str] = []
        self._groups: list[str] = []
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_model_groups(self, labels: list[str], groups: list[str]) -> None:
        self._labels = list(labels)
        self._groups = list(groups)
        self.updateGeometries()
        self.viewport().update()

    def has_groups(self) -> bool:
        return any(self._groups)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        h = 54
        if self.has_groups():
            h += self.GROUP_H
        return QSize(base.width(), h)

    def _draw_cell(self, painter: QPainter, rect: QRect, text: str, bg, bold: bool) -> None:
        painter.fillRect(rect, bg)
        pen = QPen(HEADER_BORDER)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        font = QFont(self.font())
        font.setBold(bold)
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QPen(HEADER_TEXT))
        painter.drawText(
            rect.adjusted(4, 3, -4, -3),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            text,
        )

    def paintEvent(self, event) -> None:
        if not self.has_groups():
            super().paintEvent(event)
            return

        painter = QPainter(self.viewport())
        total_h = self.height()
        group_h = self.GROUP_H
        label_h = total_h - group_h
        count = self.count()

        i = 0
        while i < count:
            grp = self._groups[i] if i < len(self._groups) else ""
            if grp:
                j = i
                span_w = 0
                while j < count and (self._groups[j] if j < len(self._groups) else "") == grp:
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(painter, QRect(gx, 0, span_w, group_h), grp, GROUP_BG, True)
                for k in range(i, j):
                    lx = self.sectionViewportPosition(k)
                    lw = self.sectionSize(k)
                    lbl = self._labels[k] if k < len(self._labels) else ""
                    self._draw_cell(painter, QRect(lx, group_h, lw, label_h), lbl, HEADER_BG, False)
                i = j
            else:
                x = self.sectionViewportPosition(i)
                w = self.sectionSize(i)
                lbl = self._labels[i] if i < len(self._labels) else ""
                self._draw_cell(painter, QRect(x, 0, w, total_h), lbl, HEADER_BG, True)
                i += 1
        painter.end()
