"""Configurare QPrinter și previzualizare printare."""

from __future__ import annotations

from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument
from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PyQt6.QtWidgets import QWidget

from core.export_presets import get_print_orientation
from ui.export.export_html import build_pages_html


def configure_printer(printer: QPrinter | None = None) -> QPrinter:
    printer = printer or QPrinter(QPrinter.PrinterMode.HighResolution)
    orientation = get_print_orientation()
    if orientation == "portrait":
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    else:
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    return printer


def show_print_preview(parent: QWidget, pages: list[dict], title: str = "Previzualizare printare") -> None:
    printer = configure_printer()
    document = QTextDocument()
    document.setHtml(build_pages_html(pages))
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle(title)
    preview.paintRequested.connect(document.print)
    preview.exec()
