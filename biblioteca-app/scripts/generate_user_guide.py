"""Generează ghid PDF de o pagină pentru bibliotecari."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer  # noqa: E402

from core.version import APP_VERSION  # noqa: E402
from ui.export.pdf_fonts import register_pdf_fonts  # noqa: E402

_SECTIONS = [
    (
        "Instalare",
        "Descărcați <b>RegistruDigital_Setup</b> de pe GitHub Releases și rulați instalatorul. "
        "La final, porniți aplicația din Meniu Start sau de pe desktop.",
    ),
    (
        "Prima pornire",
        "Completați asistentul: numele bibliotecii, localitatea, personalul responsabil și "
        "range-urile pentru generare automată. Urmați turul rapid (5 pași) dacă apare.",
    ),
    (
        "Lucru zilnic",
        "Deschideți o parte din meniul stâng (I–XIV). Alegeți <b>anul</b> și <b>luna</b>. "
        "Apăsați <b>Regenerează zilele</b>, apoi completați tabelul sau folosiți "
        "<b>Generează automat</b>. Datele se salvează automat.",
    ),
    (
        "Panou Acasă",
        "Butonul <b>Acasă</b> (Ctrl+H) arată progresul pe an, luni incomplete și ultimul backup. "
        "Folosiți <b>Continuă unde am rămas</b> pentru a relua ultima sesiune.",
    ),
    (
        "Backup și siguranță",
        "La fiecare pornire se creează o copie automată. Manual: "
        "<b>Fișier → Salvează copie registru</b>. Restaurare din același meniu.",
    ),
    (
        "Export și arhivă",
        "<b>Ctrl+E</b> exportă pagina curentă (Word, PDF, Excel). "
        "<b>Ctrl+R</b> deschide registrul complet. "
        "<b>Asistent închidere an</b> verifică lunile goale înainte de arhivare.",
    ),
    (
        "Scurtături utile",
        "Ctrl+S salvare · Ctrl+Z undo · Ctrl+F căutare în tabel · F1 ajutor · Ctrl+, setări",
    ),
]


def generate_user_guide_pdf(out_path: Path | None = None) -> Path:
    font, font_bold = register_pdf_fonts()
    out = out_path or (ROOT / "app" / "resources" / "guides" / "ghid_bibliotecar.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GuideTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.HexColor("#1e3a5f"),
    )
    subtitle_style = ParagraphStyle(
        "GuideSubtitle",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor("#64748b"),
    )
    heading_style = ParagraphStyle(
        "GuideHeading",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=10,
        leading=13,
        spaceBefore=6,
        spaceAfter=2,
        textColor=colors.HexColor("#1e40af"),
    )
    body_style = ParagraphStyle(
        "GuideBody",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        spaceAfter=2,
        textColor=colors.HexColor("#334155"),
    )

    story = [
        Paragraph("Registru Digital Bibliotecă", title_style),
        Paragraph(f"Ghid rapid pentru bibliotecar · versiunea {APP_VERSION}", subtitle_style),
        Spacer(1, 2 * mm),
    ]
    for title, body in _SECTIONS:
        story.append(Paragraph(title, heading_style))
        story.append(Paragraph(body, body_style))

    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Suport: consultați <b>Ajutor → Scurtături tastatură</b> (F1) în aplicație.",
            body_style,
        )
    )

    doc.build(story)
    return out


if __name__ == "__main__":
    path = generate_user_guide_pdf()
    print(f"Ghid generat: {path}")
