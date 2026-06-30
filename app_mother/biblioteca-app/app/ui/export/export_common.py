"""Texte și formatare comune pentru export."""

from ui.export.export_utils import escape_html, escape_reportlab

REGISTER_TITLE = "Registru de evidență a activității bibliotecii"


def format_part_heading(meta: dict) -> str:
    partea = f"Partea {meta.get('parte_roman', '')}. {meta.get('title', '')}"
    if meta.get("luna_name"):
        partea += f" în luna {meta['luna_name']} anul {meta.get('an', '')}"
    elif meta.get("an"):
        partea += f" — anul {meta.get('an', '')}"
    return partea


def format_biblioteca_line(meta: dict) -> str:
    if not meta.get("nume_biblioteca"):
        return ""
    loc = f", {meta['localitate']}" if meta.get("localitate") else ""
    return f"{meta['nume_biblioteca']}{loc}"


def format_part_heading_html(meta: dict) -> str:
    return escape_html(format_part_heading(meta))


def format_biblioteca_line_reportlab(meta: dict) -> str:
    line = format_biblioteca_line(meta)
    if not line:
        return ""
    return f"<b>{escape_reportlab(line)}</b>"


def format_part_heading_reportlab(meta: dict) -> str:
    return escape_reportlab(format_part_heading(meta))
