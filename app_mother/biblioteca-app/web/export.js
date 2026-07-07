// ============================================================================
// Export Word (.doc) și PDF pentru o parte — 100% în browser, fără backend.
// PDF: pdfmake (CDN). Word: HTML compatibil Microsoft Word (deschide + editabil).
// Excel per-parte este în app.js (SheetJS); backup complet în backup.js.
// ============================================================================
(function () {
  const LUNI = ["ianuarie","februarie","martie","aprilie","mai","iunie","iulie",
    "august","septembrie","octombrie","noiembrie","decembrie"];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(v, t) {
    if (t === "bool") return v ? "✓" : "";
    return v == null ? "" : String(v);
  }
  function subtitle(part, ctx) {
    if (part.period === "crud") return "";
    let s = `Anul ${ctx.an}`;
    if (part.period !== "crud") s += `, luna ${LUNI[ctx.luna - 1] || ctx.luna}`;
    if (part.categorie) s += `, categorie: ${ctx.cat === "adulti" ? "Adulți" : "Copii"}`;
    return s;
  }
  function baseName(part, ctx) {
    let n = `partea_${part.nr}`;
    if (part.period !== "crud") n += `_${ctx.an}_${String(ctx.luna).padStart(2, "0")}`;
    if (part.categorie) n += `_${ctx.cat}`;
    return n;
  }
  function download(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  const headers = (part) => part.cols.map((c) => c[1]);
  const rowText = (part, r) => part.cols.map(([k, l, t]) => fmt(r[k], t));

  // ---- PDF (pdfmake) --------------------------------------------------------
  function exportPDF(part, rows, ctx) {
    if (!window.pdfMake) { ctx.toast && ctx.toast("PDF indisponibil (rețea?)"); return; }
    const body = [headers(part).map((h) => ({ text: h, bold: true, fontSize: 6, fillColor: "#eef2f7" }))];
    rows.forEach((r) => body.push(rowText(part, r).map((x) => ({ text: x, fontSize: 6 }))));
    if (!rows.length) body.push([{ text: "— fără date —", colSpan: part.cols.length, alignment: "center", fontSize: 8 }]);
    const dd = {
      pageOrientation: "landscape", pageSize: "A4", pageMargins: [16, 24, 16, 20],
      content: [
        { text: `Partea ${part.nr} — ${part.title}`, bold: true, fontSize: 12, margin: [0, 0, 0, 2] },
        { text: subtitle(part, ctx), fontSize: 9, color: "#555", margin: [0, 0, 0, 8] },
        { table: { headerRows: 1, body }, layout: "lightHorizontalLines" },
      ],
      defaultStyle: { fontSize: 6 },
    };
    window.pdfMake.createPdf(dd).download(baseName(part, ctx) + ".pdf");
  }

  // ---- Word (.doc prin HTML) ------------------------------------------------
  function exportWord(part, rows, ctx) {
    const th = headers(part).map((h) => `<th>${esc(h)}</th>`).join("");
    const trs = rows.map((r) =>
      `<tr>${rowText(part, r).map((x) => `<td>${esc(x)}</td>`).join("")}</tr>`).join("");
    const html =
      `<html xmlns:o='urn:schemas-microsoft-com:office:office' ` +
      `xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>` +
      `<head><meta charset='utf-8'>` +
      `<style>@page{size:A4 landscape} body{font-family:'Segoe UI',Arial,sans-serif}` +
      `table{border-collapse:collapse;width:100%} td,th{border:1px solid #555;padding:3px;font-size:9px}` +
      `th{background:#eef2f7}</style></head><body>` +
      `<h3>Partea ${esc(part.nr)} — ${esc(part.title)}</h3>` +
      `<p>${esc(subtitle(part, ctx))}</p>` +
      `<table><tr>${th}</tr>${trs || `<tr><td colspan='${part.cols.length}'>— fără date —</td></tr>`}</table>` +
      `</body></html>`;
    download(new Blob(["﻿", html], { type: "application/msword" }), baseName(part, ctx) + ".doc");
  }

  window.RegistruExport = { exportPDF, exportWord };
})();
