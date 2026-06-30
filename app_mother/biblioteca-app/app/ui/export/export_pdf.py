"""Export PDF cu reportlab — pagini numerotate, grilă completă, anteturi de grup."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ui.export.export_common import (
    REGISTER_TITLE,
    format_biblioteca_line_reportlab,
    format_part_heading_reportlab,
)
from ui.export.export_html import group_spans
from ui.export.export_utils import (
    escape_reportlab,
    format_cell_value,
    format_total_value,
    validate_pages,
)
from ui.export.pdf_fonts import register_pdf_fonts

_FONT, _FONT_BOLD = register_pdf_fonts()


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 8)
    w, _h = landscape(A4)
    canvas.drawRightString(w - 10 * mm, 6 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def export_to_pdf(out_path: Path, pages: list[dict]) -> Path:
    validate_pages(pages)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=landscape(A4),
        leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    if _FONT != "Helvetica":
        styles["Normal"].fontName = _FONT
        styles["Title"].fontName = _FONT_BOLD
        styles["Heading3"].fontName = _FONT_BOLD
    story = []

    for pi, page in enumerate(pages):
        if pi > 0:
            story.append(PageBreak())
        if page.get("type") == "cover":
            story.extend(_cover_flowables(page, styles))
        else:
            story.extend(_page_flowables(page, styles))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return out_path


def _cover_flowables(page: dict, styles) -> list:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle

    def ps(name, size, space):
        return ParagraphStyle(name, parent=styles["Normal"], alignment=TA_CENTER,
                              fontSize=size, leading=size + 4, spaceAfter=space,
                              fontName=_FONT_BOLD)

    flow = [Spacer(1, 90 * mm * 0.5)]
    if page.get("institutie_1"):
        flow.append(Paragraph(escape_reportlab(page["institutie_1"]), ps("i1", 15, 4)))
    if page.get("institutie_2"):
        flow.append(Paragraph(escape_reportlab(page["institutie_2"]), ps("i2", 15, 30)))
    if page.get("titlu"):
        flow.append(Paragraph(escape_reportlab(page["titlu"]), ps("t", 26, 18)))
    if page.get("biblioteca"):
        flow.append(Paragraph(escape_reportlab(page["biblioteca"]), ps("b", 22, 10)))
    if page.get("localitate"):
        flow.append(Paragraph(escape_reportlab(page["localitate"]), ps("l", 17, 36)))
    if page.get("an"):
        flow.append(Paragraph(escape_reportlab(page["an"]), ps("a", 19, 10)))
    return flow


def _page_flowables(page: dict, styles) -> list:
    headers = page["headers"]
    groups = page["groups"]
    col_keys = page["col_keys"]
    rows = page["rows"]
    total_rows = page["total_rows"]
    meta = page["meta"]

    flow = []
    bib_line = format_biblioteca_line_reportlab(meta)
    if bib_line:
        flow.append(Paragraph(bib_line, styles["Normal"]))
    flow.append(Paragraph(f"<b>{escape_reportlab(REGISTER_TITLE)}</b>", styles["Title"]))
    partea = format_part_heading_reportlab(meta)
    flow.append(Paragraph(f"<b>{partea}</b>", styles["Heading3"]))
    flow.append(Spacer(1, 6))

    has_groups = any(groups)
    spans = group_spans(groups)
    ncols = len(headers)

    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#555555")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    data: list[list[str]] = []
    if has_groups:
        grp_row = [""] * ncols
        lbl_row = [""] * ncols
        for start, end, g in spans:
            if g:
                grp_row[start] = g
                style_cmds.append(("SPAN", (start, 0), (end, 0)))
                for c in range(start, end + 1):
                    lbl_row[c] = headers[c]
            else:
                grp_row[start] = headers[start]
                style_cmds.append(("SPAN", (start, 0), (start, 1)))
        data.append(grp_row)
        data.append(lbl_row)
        header_rows = 2
    else:
        data.append(list(headers))
        header_rows = 1

    style_cmds.append(("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#DBE3EE")))
    style_cmds.append(("FONTNAME", (0, 0), (-1, header_rows - 1), _FONT_BOLD))

    for row in rows:
        line = []
        for k in col_keys:
            line.append(format_cell_value(row.get(k, "")))
        data.append(line)

    if rows:
        style_cmds.append(
            ("FONTNAME", (0, header_rows), (0, header_rows + len(rows) - 1), _FONT_BOLD)
        )

    for label, sums in total_rows:
        line = [label]
        for k in col_keys[1:]:
            line.append(format_total_value(sums.get(k, "")))
        data.append(line)

    total_start = header_rows + len(rows)
    style_cmds.append(("BACKGROUND", (0, total_start), (-1, -1), colors.HexColor("#E2E8F0")))
    style_cmds.append(("FONTNAME", (0, total_start), (-1, -1), _FONT_BOLD))

    if len(data) > header_rows:
        t = Table(data, repeatRows=header_rows)
        t.setStyle(TableStyle(style_cmds))
        flow.append(t)
    return flow
