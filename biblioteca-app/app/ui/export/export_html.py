"""Construire HTML pentru print (tabel cu grilă, anteturi de grup, pagini numerotate)."""

from ui.export.export_utils import escape_html, format_cell_value, format_total_value


def group_spans(groups: list[str]) -> list[tuple[int, int, str]]:
    spans = []
    i = 0
    n = len(groups)
    while i < n:
        g = groups[i]
        if g:
            j = i
            while j < n and groups[j] == g:
                j += 1
            spans.append((i, j - 1, g))
            i = j
        else:
            spans.append((i, i, ""))
            i += 1
    return spans


def _cover_html(page: dict) -> str:
    def line(text, size, bold=True, gap=10):
        if not text:
            return ""
        weight = "bold" if bold else "normal"
        return (
            f"<div style='font-size:{size}px; font-weight:{weight}; margin:{gap}px 0;'>"
            f"{escape_html(text)}</div>"
        )

    return (
        "<div style='text-align:center; margin-top:120px;'>"
        + line(page.get("institutie_1"), 16, True, 4)
        + line(page.get("institutie_2"), 16, True, 24)
        + line(page.get("titlu"), 30, True, 18)
        + line(page.get("biblioteca"), 26, True, 10)
        + line(page.get("localitate"), 20, True, 40)
        + line(page.get("an"), 22, True, 10)
        + "</div>"
    )


def _page_html(page: dict, page_number: int, total_pages: int) -> str:
    if page.get("type") == "cover":
        return _cover_html(page)
    headers = page["headers"]
    groups = page["groups"]
    col_keys = page["col_keys"]
    rows = page["rows"]
    total_rows = page["total_rows"]
    meta = page["meta"]

    has_groups = any(groups)
    spans = group_spans(groups)

    head = "<div style='text-align:center'>"
    if meta.get("nume_biblioteca"):
        loc = f", {meta['localitate']}" if meta.get("localitate") else ""
        head += f"<b>{escape_html(meta['nume_biblioteca'])}{escape_html(loc)}</b><br>"
    head += "<b style='font-size:14px'>Registru de evidență a activității bibliotecii</b><br>"
    partea = f"Partea {meta['parte_roman']}. {meta['title']}"
    if meta.get("luna_name"):
        partea += f" în luna {meta['luna_name']} anul {meta['an']}"
    elif meta.get("an"):
        partea += f" — anul {meta['an']}"
    head += f"<b>{escape_html(partea)}</b></div>"

    cell = "border:1px solid #333; padding:3px; text-align:center;"
    date_cell = cell + " font-weight:bold;"
    th = cell + " background:#dbe3ee; font-weight:bold;"

    html = [head, "<table style='border-collapse:collapse; width:100%; font-size:9px;'>"]

    if has_groups:
        html.append("<tr>")
        for start, end, g in spans:
            if g:
                html.append(
                    f"<th style='{th}' colspan='{end - start + 1}'>{escape_html(g)}</th>"
                )
            else:
                html.append(f"<th style='{th}' rowspan='2'>{escape_html(headers[start])}</th>")
        html.append("</tr><tr>")
        for start, end, g in spans:
            if g:
                for c in range(start, end + 1):
                    html.append(f"<th style='{th}'>{escape_html(headers[c])}</th>")
        html.append("</tr>")
    else:
        html.append("<tr>")
        for h in headers:
            html.append(f"<th style='{th}'>{escape_html(h)}</th>")
        html.append("</tr>")

    for row in rows:
        html.append("<tr>")
        for ci, k in enumerate(col_keys):
            v = format_cell_value(row.get(k, ""))
            style = date_cell if ci == 0 else cell
            html.append(f"<td style='{style}'>{escape_html(v)}</td>")
        html.append("</tr>")

    for label, sums in total_rows:
        html.append("<tr>")
        for i, k in enumerate(col_keys):
            if i == 0:
                v = label
            else:
                v = format_total_value(sums.get(k, ""))
            html.append(f"<td style='{cell} background:#e2e8f0; font-weight:bold;'>{escape_html(v)}</td>")
        html.append("</tr>")

    html.append("</table>")
    html.append(
        f"<div style='text-align:right; font-size:8px; color:#64748b; margin-top:4px;'>"
        f"Pagina {page_number} din {total_pages}</div>"
    )
    return "".join(html)


def build_pages_html(pages: list[dict]) -> str:
    total = len(pages)
    parts = []
    for idx, page in enumerate(pages, 1):
        if idx > 1:
            parts.append("<div style='page-break-before:always'></div>")
        parts.append(_page_html(page, idx, total))
    return "<html><body>" + "".join(parts) + "</body></html>"
