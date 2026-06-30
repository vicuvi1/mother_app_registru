"""Antet tabel cu grupuri de coloane."""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QHeaderView

HEADER_BG = QColor("#eef2f7")
GROUP_BG = QColor("#dbe3ee")
SUPER_BG = QColor("#c8d4e4")
HEADER_BORDER = QColor("#b6c2d4")
HEADER_TEXT = QColor("#1e293b")


def header_label_width(text: str, *, padding: int = 18) -> int:
    """Lățimea necesară pentru eticheta antetului pe un singur rând."""
    font = QFont()
    font.setPointSize(8)
    metrics = QFontMetrics(font)
    return metrics.horizontalAdvance(text or " ") + padding


class GroupedHeaderView(QHeaderView):
    """Antet pe 2–3 niveluri: super-grup, grup, etichetă coloană."""

    GROUP_H = 30
    SUPER_GROUP_H = 28

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._labels: list[str] = []
        self._groups: list[str] = []
        self._super_groups: list[str] = []
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_model_groups(
        self,
        labels: list[str],
        groups: list[str],
        super_groups: list[str] | None = None,
    ) -> None:
        self._labels = list(labels)
        self._groups = list(groups)
        self._super_groups = list(super_groups or [])
        self.updateGeometries()
        self.viewport().update()

    def has_groups(self) -> bool:
        return any(self._groups)

    def has_super_groups(self) -> bool:
        return any(self._super_groups)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        h = 54
        if self.has_groups():
            h += self.GROUP_H
        if self.has_super_groups():
            h += self.SUPER_GROUP_H
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
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextSingleLine),
            text,
        )

    def _sg(self, i: int) -> str:
        return self._super_groups[i] if i < len(self._super_groups) else ""

    def _grp(self, i: int) -> str:
        return self._groups[i] if i < len(self._groups) else ""

    def _lbl(self, i: int) -> str:
        return self._labels[i] if i < len(self._labels) else ""

    def _paint_two_level(self, painter: QPainter, total_h: int, group_h: int, label_h: int, count: int) -> None:
        i = 0
        while i < count:
            grp = self._grp(i)
            if grp:
                j = i
                span_w = 0
                while j < count and self._grp(j) == grp:
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(painter, QRect(gx, 0, span_w, group_h), grp, GROUP_BG, True)
                for k in range(i, j):
                    lx = self.sectionViewportPosition(k)
                    lw = self.sectionSize(k)
                    self._draw_cell(painter, QRect(lx, group_h, lw, label_h), self._lbl(k), HEADER_BG, False)
                i = j
            else:
                x = self.sectionViewportPosition(i)
                w = self.sectionSize(i)
                self._draw_cell(painter, QRect(x, 0, w, total_h), self._lbl(i), HEADER_BG, True)
                i += 1

    def _paint_three_level(
        self, painter: QPainter, super_h: int, group_h: int, label_h: int, count: int
    ) -> None:
        i = 0
        while i < count:
            sg = self._sg(i)
            if sg:
                j = i
                span_w = 0
                while j < count and self._sg(j) == sg:
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(painter, QRect(gx, 0, span_w, super_h), sg, SUPER_BG, True)
                i = j
            else:
                i += 1

        i = 0
        while i < count:
            grp = self._grp(i)
            sg = self._sg(i)
            if grp and sg:
                j = i
                span_w = 0
                while j < count and self._grp(j) == grp and self._sg(j) == sg:
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(painter, QRect(gx, super_h, span_w, group_h), grp, GROUP_BG, True)
                i = j
            elif grp and not sg:
                j = i
                span_w = 0
                while j < count and self._grp(j) == grp and not self._sg(j):
                    span_w += self.sectionSize(j)
                    j += 1
                gx = self.sectionViewportPosition(i)
                self._draw_cell(
                    painter, QRect(gx, 0, span_w, super_h + group_h), grp, GROUP_BG, True
                )
                i = j
            elif not grp:
                x = self.sectionViewportPosition(i)
                w = self.sectionSize(i)
                self._draw_cell(
                    painter,
                    QRect(x, 0, w, super_h + group_h + label_h),
                    self._lbl(i),
                    HEADER_BG,
                    True,
                )
                i += 1
            else:
                i += 1

        for k in range(count):
            if self._grp(k):
                x = self.sectionViewportPosition(k)
                w = self.sectionSize(k)
                self._draw_cell(
                    painter,
                    QRect(x, super_h + group_h, w, label_h),
                    self._lbl(k),
                    HEADER_BG,
                    False,
                )

    def paintEvent(self, event) -> None:
        if not self.has_groups() and not self.has_super_groups():
            super().paintEvent(event)
            return

        painter = QPainter(self.viewport())
        total_h = self.height()
        count = self.count()

        if self.has_super_groups():
            super_h = self.SUPER_GROUP_H
            group_h = self.GROUP_H if self.has_groups() else 0
            label_h = total_h - super_h - group_h
            self._paint_three_level(painter, super_h, group_h, label_h, count)
        else:
            group_h = self.GROUP_H
            label_h = total_h - group_h
            self._paint_two_level(painter, total_h, group_h, label_h, count)

        painter.end()
