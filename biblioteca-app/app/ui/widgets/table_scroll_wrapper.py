"""Înveliș pentru tabele late: bară orizontală sus + jos, butoane stânga/dreapta."""

from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class TableScrollWrapper(QWidget):
    """Derulare orizontală pe tabelul nativ (QTableView) — bare sincronizate sus/jos."""

    ANIM_MS = 280
    WHEEL_FACTOR = 4

    def __init__(self, table, parent=None) -> None:
        super().__init__(parent)
        self._table = table
        self._scroll_anim: QPropertyAnimation | None = None

        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self._btn_left = QPushButton("◀  Stânga")
        self._btn_right = QPushButton("Dreapta  ▶")
        self._btn_end = QPushButton("La sfârșit ▶▶")
        self._btn_left.setObjectName("btnGhost")
        self._btn_right.setObjectName("btnGhost")
        self._btn_end.setObjectName("btnGhost")
        self._btn_left.setToolTip("Derulează spre stânga")
        self._btn_right.setToolTip("Derulează spre dreapta")
        self._btn_end.setToolTip("Arată ultimele coloane (După vârstă, Maturi după sex)")
        for btn in (self._btn_left, self._btn_right):
            btn.setAutoRepeat(True)
            btn.setAutoRepeatDelay(350)
            btn.setAutoRepeatInterval(120)
        hint = QLabel(
            "Tabel lat — folosiți barele de derulare (sus/jos), butoanele Stânga/Dreapta, "
            "La sfârșit, sau Shift + rotița mouse deasupra tabelului"
        )
        hint.setObjectName("scrollHint")
        hint.setWordWrap(True)
        nav.addWidget(self._btn_left)
        nav.addWidget(self._btn_right)
        nav.addWidget(self._btn_end)
        nav.addWidget(hint, stretch=1)
        layout.addLayout(nav)

        self._top_bar = QScrollBar(Qt.Orientation.Horizontal)
        self._top_bar.setObjectName("tableHScrollTop")
        self._top_bar.setTracking(True)
        layout.addWidget(self._top_bar)

        layout.addWidget(table, stretch=1)

        self._bottom_bar = QScrollBar(Qt.Orientation.Horizontal)
        self._bottom_bar.setObjectName("tableHScrollBottom")
        self._bottom_bar.setTracking(True)
        layout.addWidget(self._bottom_bar)

        self._hbar = table.horizontalScrollBar()
        self._hbar.setTracking(True)

        for extra in (self._top_bar, self._bottom_bar):
            extra.valueChanged.connect(lambda v, bar=extra: self._on_extra_bar_changed(bar, v))
        self._hbar.valueChanged.connect(self._on_hbar_changed)
        self._hbar.rangeChanged.connect(self._sync_extra_bars)

        self._btn_left.clicked.connect(lambda: self._nudge(-self._page_scroll_step(), animate=True))
        self._btn_right.clicked.connect(lambda: self._nudge(self._page_scroll_step(), animate=True))
        self._btn_end.clicked.connect(self.scroll_to_end)

        header = table.horizontalHeader()
        if header is not None:
            header.sectionResized.connect(self._on_table_layout_changed)
            header.geometriesChanged.connect(self._on_table_layout_changed)

        model = table.model()
        if model is not None:
            model.layoutChanged.connect(self._on_table_layout_changed)
            model.modelReset.connect(self._on_table_layout_changed)

        table.viewport().installEventFilter(self)
        QShortcut(QKeySequence(Qt.Key.Key_End), self, self.scroll_to_end)
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, self.scroll_to_start)
        QTimer.singleShot(50, self._refresh_scroll_steps)

    def scroll_to_end(self) -> None:
        self._refresh_scroll_steps()
        self._animate_to(self._hbar.maximum())

    def scroll_to_start(self) -> None:
        self._refresh_scroll_steps()
        self._animate_to(self._hbar.minimum())

    def _page_scroll_step(self) -> int:
        viewport_w = self._table.viewport().width() if self._table.viewport() else self.width()
        return max(140, viewport_w * 2 // 3)

    def _on_table_layout_changed(self, *_args) -> None:
        QTimer.singleShot(0, self._refresh_scroll_steps)

    def _refresh_scroll_steps(self) -> None:
        page = self._page_scroll_step()
        single = max(12, page // 12)
        for bar in (self._hbar, self._top_bar, self._bottom_bar):
            bar.setPageStep(page)
            bar.setSingleStep(single)
        self._sync_extra_bars(self._hbar.minimum(), self._hbar.maximum())

    def _on_extra_bar_changed(self, source: QScrollBar, value: int) -> None:
        if self._hbar.value() == value:
            return
        self._hbar.blockSignals(True)
        self._hbar.setValue(value)
        self._hbar.blockSignals(False)
        for bar in (self._top_bar, self._bottom_bar):
            if bar is not source and bar.value() != value:
                bar.blockSignals(True)
                bar.setValue(value)
                bar.blockSignals(False)

    def _on_hbar_changed(self, value: int) -> None:
        for bar in (self._top_bar, self._bottom_bar):
            if bar.value() != value:
                bar.blockSignals(True)
                bar.setValue(value)
                bar.blockSignals(False)

    def _clamp(self, value: int) -> int:
        return max(self._hbar.minimum(), min(self._hbar.maximum(), value))

    def _nudge(self, delta: int, *, animate: bool) -> None:
        if self._hbar.maximum() <= 0:
            return
        target = self._clamp(self._hbar.value() + delta)
        if animate:
            self._animate_to(target)
        else:
            self._hbar.setValue(target)

    def _animate_to(self, target: int) -> None:
        target = self._clamp(target)
        if target == self._hbar.value():
            return
        if self._scroll_anim is None:
            self._scroll_anim = QPropertyAnimation(self._hbar, b"value", self)
            self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        elif self._scroll_anim.state() == QAbstractAnimation.State.Running:
            self._scroll_anim.stop()
        self._scroll_anim.setDuration(self.ANIM_MS)
        self._scroll_anim.setStartValue(self._hbar.value())
        self._scroll_anim.setEndValue(target)
        self._scroll_anim.start()

    def _scroll_wheel_pixels(self, pixels: int) -> None:
        if pixels == 0 or self._hbar.maximum() <= 0:
            return
        self._hbar.setValue(self._clamp(self._hbar.value() - pixels // self.WHEEL_FACTOR))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_scroll_steps()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(50, self._after_show)

    def _after_show(self) -> None:
        if hasattr(self._table, "refresh_horizontal_layout"):
            self._table.refresh_horizontal_layout()
        self._refresh_scroll_steps()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table.viewport():
            if event.type() == QEvent.Type.Wheel:
                delta_x = event.angleDelta().x()
                delta_y = event.angleDelta().y()
                if self._hbar.maximum() > 0:
                    if delta_x != 0:
                        self._scroll_wheel_pixels(delta_x)
                        event.accept()
                        return True
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and delta_y != 0:
                        self._scroll_wheel_pixels(delta_y)
                        event.accept()
                        return True
        return super().eventFilter(obj, event)

    def _sync_extra_bars(self, minimum: int, maximum: int) -> None:
        can_scroll = maximum > 0
        for bar in (self._top_bar, self._bottom_bar):
            bar.blockSignals(True)
            bar.setRange(minimum, maximum)
            bar.setPageStep(self._hbar.pageStep())
            bar.setSingleStep(self._hbar.singleStep())
            bar.setValue(self._hbar.value())
            bar.setEnabled(can_scroll)
            bar.blockSignals(False)
        self._btn_left.setEnabled(can_scroll)
        self._btn_right.setEnabled(can_scroll)
        self._btn_end.setEnabled(can_scroll)
