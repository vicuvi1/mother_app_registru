"""Tur ghidat scurt după prima configurare."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.onboarding import mark_onboarding_completed

_STEPS = [
    (
        "Părțile registrului",
        "Selectați o parte din meniul stâng (I–XIV). "
        "Fiecare parte corespunde unei secțiuni din registrul fizic.",
    ),
    (
        "Anul și luna",
        "Sus găsiți selectorul de an și bara cu lunile (Ian–Dec). "
        "Folosiți Ctrl+← / Ctrl+→ pentru navigare rapidă.",
    ),
    (
        "Completare zilnică",
        "„Regenerează zilele” creează rânduri pentru zilele lucrătoare. "
        "„Generează automat” completează valori în range-urile setate.",
    ),
    (
        "Salvare și export",
        "Datele se salvează automat. Ctrl+S salvează manual. "
        "Ctrl+E exportă în Word, PDF sau Excel.",
    ),
    (
        "Panou Acasă și backup",
        "Butonul „Acasă” arată progresul pe an. "
        "Din Fișier → Salvează copie registru păstrați o copie de siguranță.",
    ),
]


class OnboardingTourDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tur rapid — Registru Digital")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)

        self._stack = QStackedWidget()
        for i, (title, body) in enumerate(_STEPS):
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setSpacing(12)
            h = QLabel(f"Pasul {i + 1} din {len(_STEPS)}: {title}")
            h.setObjectName("tourStepTitle")
            h.setWordWrap(True)
            pl.addWidget(h)
            text = QLabel(body)
            text.setWordWrap(True)
            text.setObjectName("tourStepBody")
            pl.addWidget(text)
            pl.addStretch()
            self._stack.addWidget(page)
        layout.addWidget(self._stack, stretch=1)

        self._chk_hide = QCheckBox("Nu mai arăta acest tur")
        self._chk_hide.setChecked(True)
        layout.addWidget(self._chk_hide)

        nav = QHBoxLayout()
        self._btn_back = QPushButton("Înapoi")
        self._btn_back.clicked.connect(self._back)
        nav.addWidget(self._btn_back)
        nav.addStretch()
        self._btn_next = QPushButton("Înainte")
        self._btn_next.setObjectName("btnPrimary")
        self._btn_next.clicked.connect(self._next)
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)

        self._update_nav()

    def _back(self) -> None:
        idx = self._stack.currentIndex()
        if idx > 0:
            self._stack.setCurrentIndex(idx - 1)
        self._update_nav()

    def _next(self) -> None:
        idx = self._stack.currentIndex()
        if idx < self._stack.count() - 1:
            self._stack.setCurrentIndex(idx + 1)
            self._update_nav()
            return
        if self._chk_hide.isChecked():
            mark_onboarding_completed()
        self.accept()

    def _update_nav(self) -> None:
        idx = self._stack.currentIndex()
        last = idx >= self._stack.count() - 1
        self._btn_back.setEnabled(idx > 0)
        self._btn_next.setText("Gata" if last else "Înainte")
