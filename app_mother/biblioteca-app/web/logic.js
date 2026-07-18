// ============================================================================
// Logică pură, testabilă (fără DOM / Supabase). Folosită de app.js și testată
// de logic.test.js. Rulează atât în browser (window.RegistruLogic) cât și în
// Node (module.exports) pentru CI.
// ============================================================================
(function () {
  const pad2 = (n) => String(n).padStart(2, "0");

  // Zilele lucrătoare (Luni–Vineri) ale lunii, ca "DD.MM".
  function weekdays(year, month) {
    const out = [], d = new Date(year, month - 1, 1);
    while (d.getMonth() === month - 1) { const wd = d.getDay(); if (wd >= 1 && wd <= 5) out.push(pad2(d.getDate()) + "." + pad2(month)); d.setDate(d.getDate() + 1); }
    return out;
  }

  // Redistribuie proporțional CZU-urile ca să însumeze `total` (largest-remainder).
  function rebalanceCZU(cur, total) {
    const sum = cur.reduce((a, b) => a + b, 0);
    if (sum <= total || total <= 0) return cur.slice();
    const exact = cur.map((v) => (v * total) / sum), fl = exact.map((v) => Math.floor(v));
    let rem = total - fl.reduce((a, b) => a + b, 0);
    const order = cur.map((v, i) => i).sort((a, b) => (exact[b] - fl[b]) - (exact[a] - fl[a]));
    for (let i = 0; i < rem; i++) fl[order[i % order.length]]++;
    return fl;
  }

  // Split gen: feminin = total // 2, masculin = restul.
  function genderSplit(total) { total = Math.max(0, total | 0); const f = Math.floor(total / 2); return { f, m: total - f }; }

  // Split copii (Partea I): copii_pana_16 = prescolari + elevi, cu propagare.
  function copiiSplit(P, E, C, changed) {
    P = +P || 0; E = +E || 0; C = +C || 0;
    if (changed === "elevi") C = P + E;
    else if (changed === "copii_pana_16") E = Math.max(0, C - P);
    else if (changed === "prescolari") { if (C > 0) E = Math.max(0, C - P); else C = P + E; }
    return { prescolari: P, elevi: E, copii_pana_16: C };
  }

  // Split pe limbi (Partea III): o carte e fie în limba română, fie în altă
  // limbă, deci „Limba română" = „Cărți" − „Alte limbi" (implicit tot restul e
  // în română; minim 0 dacă „Alte limbi" ar depăși „Cărți").
  function docLangSplit(carti, alteLimbi) {
    carti = Math.max(0, +carti || 0); alteLimbi = Math.max(0, +alteLimbi || 0);
    return { limba_romana: Math.max(0, carti - alteLimbi) };
  }

  // Categoria-rest CZU (Partea IV): „8 Limbi" (literatură) absoarbe restul, deci
  // = Total împrumuturi − Σ(celelalte categorii CZU). Minim 0 dacă celelalte ar
  // depăși totalul. `others` = valorile celorlalte categorii (fără czu_8_limbi).
  function czuRemainder(total, others) {
    total = Math.max(0, +total || 0);
    const s = (others || []).reduce((a, v) => a + Math.max(0, +v || 0), 0);
    return Math.max(0, total - s);
  }

  // Split în pereche dintr-un total (Partea IX: Fete/Băieți, Preșcolari/Elevi):
  // membrul editat rămâne, celălalt = max(0, Total − editat). `changed`: "m"
  // păstrează m și recalculează f; altfel păstrează f și recalculează m.
  function pairSplit(total, f, m, changed) {
    total = Math.max(0, +total || 0); f = Math.max(0, +f || 0); m = Math.max(0, +m || 0);
    if (changed === "m") f = Math.max(0, total - m);
    else m = Math.max(0, total - f);
    return { f, m };
  }

  // Sume pe coloane: int → sumă; bool cu ct → număr de bifate.
  function sumCols(cols, rows) {
    const acc = {};
    cols.forEach((c) => { const [k, l, t, o] = c; if (t === "int") acc[k] = rows.reduce((s, r) => s + (+r[k] || 0), 0); else if (t === "bool" && o && o.ct) acc[k] = rows.reduce((s, r) => s + (r[k] ? 1 : 0), 0); });
    return acc;
  }

  const api = { weekdays, rebalanceCZU, genderSplit, copiiSplit, docLangSplit, czuRemainder, pairSplit, sumCols };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.RegistruLogic = api;
})();
