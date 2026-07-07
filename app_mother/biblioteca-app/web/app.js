// ============================================================================
// Motorul aplicației web — toate părțile din REGISTRU_PARTS.
// Autentificare + tabele editabile + antete grupate + coloane calculate +
// reguli intra-rând (split copii, oglindă Partea III, split gen) + rânduri
// „Total" / „Total de la început" + validare + realtime + export + backup.
// ============================================================================
(function () {
  const $ = (id) => document.getElementById(id);
  const PARTS = window.REGISTRU_PARTS;
  const MAX5 = window.REGISTRU_MAX5;
  const STAFF = { key: "__staff" };
  const IMPORT = { key: "__import" };
  const LUNI = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Noi","Dec"];

  if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) {
    $("authErr").textContent = "Lipsește config.js (URL + cheie Supabase).";
  }
  const sb = window.supabase.createClient(window.SUPABASE_URL || "", window.SUPABASE_ANON_KEY || "");

  const state = { part: null, an: 2026, luna: 7, cat: "copii", rows: [], staff: [], prior: null, aux: {} };
  let channel = null;

  // Chei folosite de sincronizarea între părți
  const P3_DIN = ["consultare_pe_loc", "imprumut_pe_loc", "imprumut_la_domiciliu", "imprumut_inter_bibliotecar"];
  const P2_INTR = ["imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii"];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const toInt = (v) => Math.max(0, parseInt(v, 10) || 0);
  function toast(m) { const t = $("toast"); t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 1400); }
  const effCols = () => window.partCols(state.part, state.cat);

  // ---- Autentificare --------------------------------------------------------
  async function login() {
    $("authErr").textContent = "";
    const { error } = await sb.auth.signInWithPassword({ email: $("email").value.trim(), password: $("password").value });
    if (error) { $("authErr").textContent = error.message; return; }
    onLoggedIn();
  }
  async function onLoggedIn() {
    const { data } = await sb.auth.getUser();
    if (!data.user) return;
    $("auth").classList.add("hidden"); $("app").classList.remove("hidden");
    $("who").textContent = data.user.email;
    initSelectors(); renderNav(); await loadStaff();
    selectPart(PARTS[0].key); refreshBackupInfo();
  }

  // ---- Selectoare -----------------------------------------------------------
  function initSelectors() {
    if ($("an").options.length) return;
    for (let y = 2023; y <= 2027; y++) $("an").add(new Option(y, y, false, y === state.an));
    LUNI.forEach((m, i) => $("luna").add(new Option(m, i + 1, false, i + 1 === state.luna)));
    $("an").onchange = () => { state.an = +$("an").value; if (!special()) loadData(); };
    $("luna").onchange = () => { state.luna = +$("luna").value; if (!special()) loadData(); };
    $("cat").onchange = () => { state.cat = $("cat").value; if (!special()) loadData(); };
  }
  const special = () => state.part === STAFF || state.part === IMPORT;

  // ---- Navigație ------------------------------------------------------------
  function renderNav() {
    const nav = $("nav");
    nav.innerHTML = PARTS.map((p) => `<button class="nav" data-key="${p.key}">${p.nr}. ${esc(p.title)}</button>`).join("") +
      `<div class="navsep"></div><button class="nav" data-key="__staff">👤 Personal</button>` +
      `<button class="nav" data-key="__import">⬆ Import / Migrare</button>`;
    nav.querySelectorAll("button.nav").forEach((b) => (b.onclick = () => selectPart(b.dataset.key)));
  }
  function markActive(key) {
    document.querySelectorAll("#nav button.nav").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
  }
  function selectPart(key) {
    if (key === "__staff") { state.part = STAFF; updateHeader(); markActive(key); renderStaff(); subscribe("personal"); return; }
    if (key === "__import") { state.part = IMPORT; updateHeader(); markActive(key); if (channel) { sb.removeChannel(channel); channel = null; } renderImport(); return; }
    state.part = PARTS.find((p) => p.key === key);
    updateHeader(); markActive(key); loadData(); subscribe(state.part.key);
  }
  function updateHeader() {
    const p = state.part, sp = special();
    $("title").textContent = p === STAFF ? "Personal (responsabili)" : p === IMPORT ? "Import / Migrare date" : `Partea ${p.nr} — ${p.title}`;
    const showPeriod = !sp && p.period !== "crud";
    $("anWrap").style.display = showPeriod ? "" : "none";
    $("lunaWrap").style.display = showPeriod ? "" : "none";
    $("catWrap").style.display = !sp && p.categorie ? "" : "none";
    $("addRow").style.display = sp ? "none" : "";
    ["exportBtn", "pdfBtn", "wordBtn"].forEach((id) => ($(id).style.display = sp ? "none" : ""));
  }

  // ---- Încărcare ------------------------------------------------------------
  async function loadData() {
    const p = state.part;
    let q = sb.from(p.key).select("*");
    if (p.period !== "crud") q = q.eq("an", state.an).eq("luna", state.luna);
    if (p.categorie) q = q.eq("categorie_varsta", state.cat);
    q = p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true });
    const { data, error } = await q;
    if (error) { toast("Eroare: " + error.message); return; }
    state.rows = data || [];
    await syncIn(p);
    // Prior months (pentru „Total de la început")
    state.prior = null;
    if (p.cumulative) {
      let pq = sb.from(p.key).select("*").eq("an", state.an).lt("luna", state.luna);
      if (p.categorie) pq = pq.eq("categorie_varsta", state.cat);
      const { data: pd } = await pq;
      state.prior = computeAcc(effCols(), pd || []);
    }
    renderGrid();
  }

  // ---- Sincronizare între părți (forward) -----------------------------------
  // IV.total_imprumuturi ← III (pe dată+categorie); II.instruiri ← IX, II.activitati ← XI.
  // Se scriu valorile derivate în DB (self-heal) ca backup-ul/exportul să fie corecte.
  async function syncIn(p) {
    state.aux = {};
    try {
      if (p.key === "documente_continut_czu") {
        const { data } = await sb.from("documente_inregistrate").select("*")
          .eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const map = {};
        (data || []).forEach((r) => {
          const t = (+r.total_imprumuturi || 0) || P3_DIN.reduce((a, k) => a + (+r[k] || 0), 0);
          if (r.data) map[r.data] = t;
        });
        state.aux.p3 = map;
        const czuKeys = effCols().find((c) => c[0] === "total_imprumuturi")[3].sum;
        for (const r of state.rows) {
          const czu = czuKeys.reduce((a, k) => a + (+r[k] || 0), 0);
          const total = (map[r.data] || 0) > 0 ? map[r.data] : czu;
          if ((+r.total_imprumuturi || 0) !== total) {
            r.total_imprumuturi = total;
            await sb.from(p.key).update({ total_imprumuturi: total }).eq("id", r.id);
          }
        }
      } else if (p.key === "evidenta_utilizatori_copii_adulti") {
        const q = (tbl) => sb.from(tbl).select("data,total_participanti")
          .eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const [ix, xi] = await Promise.all([q("instruiri"), q("activitati_culturale")]);
        const ixMap = {}, xiMap = {};
        (ix.data || []).forEach((r) => { if (r.data) ixMap[r.data] = (ixMap[r.data] || 0) + (+r.total_participanti || 0); });
        (xi.data || []).forEach((r) => { if (r.data) xiMap[r.data] = (xiMap[r.data] || 0) + (+r.total_participanti || 0); });
        for (const r of state.rows) {
          const upd = {};
          const ins = ixMap[r.data] || 0, act = xiMap[r.data] || 0;
          if ((+r.instruiri || 0) !== ins) { r.instruiri = ins; upd.instruiri = ins; }
          if ((+r.activitati_culturale_stiintifice || 0) !== act) { r.activitati_culturale_stiintifice = act; upd.activitati_culturale_stiintifice = act; }
          const it = P2_INTR.reduce((a, k) => a + (+r[k] || 0), 0);
          if ((+r.intrari_total_zi || 0) !== it) { r.intrari_total_zi = it; upd.intrari_total_zi = it; }
          if (Object.keys(upd).length) await sb.from(p.key).update(upd).eq("id", r.id);
        }
      }
    } catch (e) { /* sincronizarea nu blochează afișarea */ }
  }

  // ---- Antet grupat ---------------------------------------------------------
  function spanRow(cols, keyFn) {
    let html = "", i = 0;
    while (i < cols.length) {
      const key = keyFn(cols[i]);
      if (key == null) { html += "<th></th>"; i++; continue; }
      let j = i + 1; while (j < cols.length && keyFn(cols[j]) === key) j++;
      html += `<th colspan="${j - i}">${esc(key)}</th>`; i = j;
    }
    return html;
  }
  function buildHead(cols) {
    const hasSG = cols.some((c) => c[3] && c[3].sg);
    const hasG = cols.some((c) => c[3] && c[3].g);
    let h = "";
    if (hasSG) h += `<tr>${spanRow(cols, (c) => (c[3] && c[3].sg) || null)}<th></th></tr>`;
    if (hasG || hasSG) h += `<tr>${spanRow(cols, (c) => (c[3] && c[3].g) || null)}<th></th></tr>`;
    h += `<tr>${cols.map((c) => `<th title="${c[0]}">${esc(c[1])}</th>`).join("")}<th></th></tr>`;
    return h;
  }

  // ---- Celule ---------------------------------------------------------------
  function inputHtml(part, r, c) {
    const [k, l, t, o = {}] = c;
    const attr = `data-id="${r.id}" data-col="${k}" data-type="${t}" ${o.req ? 'data-req="1"' : ""}`;
    const v = r[k];
    if (t === "int") {
      const max = MAX5.has(part.key) ? 5 : 30;
      const cls = "num" + (o.ro ? " calc" : "") + (!o.ro && (+v || 0) > max ? " oor" : "");
      return `<input class="${cls}" type="number" min="0" ${o.ro ? "readonly" : `data-max="${max}"`} value="${esc(v == null ? 0 : v)}" ${attr}>`;
    }
    if (t === "bool") return `<input type="checkbox" ${v ? "checked" : ""} ${attr}>`;
    if (t === "date") return `<input class="date" type="date" value="${esc(v)}" ${attr}>`;
    if (t === "staff") return `<input class="txt" type="text" list="staffList" value="${esc(v)}" ${attr}>`;
    if (t === "txt") return `<input class="txt wide" type="text" value="${esc(v)}" ${attr}>`;
    return `<input class="txt" type="text" value="${esc(v)}" ${attr}>`;
  }

  function renderGrid() {
    const p = state.part, cols = effCols();
    const body = state.rows.map((r) => {
      const tds = cols.map((c) => `<td>${inputHtml(p, r, c)}</td>`).join("");
      return `<tr>${tds}<td><button class="del" data-id="${r.id}" title="Șterge rândul">✕</button></td></tr>`;
    }).join("");
    const empty = `<tr><td colspan="${cols.length + 1}" style="padding:16px;color:var(--muted)">Niciun rând. Apăsați „+ Rând".</td></tr>`;
    $("content").innerHTML =
      `<div class="tablebox"><table>
        <thead>${buildHead(cols)}</thead>
        <tbody>${state.rows.length ? body : empty}</tbody>
        <tfoot id="gridFoot"></tfoot></table></div>`;
    $("content").querySelectorAll("tbody input").forEach((inp) => {
      inp.addEventListener("change", saveCell);
      if (inp.type !== "checkbox" && !inp.readOnly) {
        inp.addEventListener("input", () => inp.classList.add("dirty"));
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
      }
    });
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteRow(+b.dataset.id)));
    renderFooter();
  }

  // ---- Totaluri (footer) ----------------------------------------------------
  function computeAcc(cols, rows) {
    const acc = {};
    cols.forEach(([k, l, t, o]) => {
      if (t === "int") acc[k] = rows.reduce((s, r) => s + (+r[k] || 0), 0);
      else if (t === "bool" && o && o.ct) acc[k] = rows.reduce((s, r) => s + (r[k] ? 1 : 0), 0);
    });
    return acc;
  }
  function footerRow(label, acc, cols, cls) {
    const cells = cols.map((c, i) => i === 0
      ? `<td class="totlbl">${esc(label)}</td>`
      : `<td class="${cls}">${acc[c[0]] == null ? "" : acc[c[0]]}</td>`).join("");
    return `<tr>${cells}<td class="${cls}"></td></tr>`;
  }
  function renderFooter() {
    const cols = effCols(), acc = computeAcc(cols, state.rows);
    let html = footerRow("Total", acc, cols, "totalrow");
    if (state.part.cumulative && state.prior) {
      const cum = {};
      cols.forEach(([k, l, t, o]) => { if (t === "int" || (t === "bool" && o && o.ct)) cum[k] = (state.prior[k] || 0) + (acc[k] || 0); });
      html += footerRow("Total de la început", cum, cols, "cumrow");
    }
    const foot = $("gridFoot"); if (foot) foot.innerHTML = html;
  }

  // ---- Reguli intra-rând (portate din desktop) ------------------------------
  function deriveRow(part, row, col) {
    const cols = effCols(), affected = new Set([col]);
    // 1) Split copii (Partea I): copii_pana_16 = prescolari + elevi
    if (part.key === "evidenta_utilizatori") {
      const P = +row.prescolari || 0, E = +row.elevi || 0, C = +row.copii_pana_16 || 0;
      if (col === "elevi") { row.copii_pana_16 = P + E; affected.add("copii_pana_16"); }
      else if (col === "copii_pana_16") { row.elevi = Math.max(0, C - P); affected.add("elevi"); }
      else if (col === "prescolari") {
        if (C > 0) { row.elevi = Math.max(0, C - P); affected.add("elevi"); }
        else { row.copii_pana_16 = P + E; affected.add("copii_pana_16"); }
      }
    }
    // 2) Split gen (VI, XI): total → feminin/masculin (jumătate/jumătate)
    if (part.split && col === part.split.total) {
      const tot = +row[part.split.total] || 0;
      if (tot > 0) { const f = Math.floor(tot / 2); row[part.split.f] = f; row[part.split.m] = tot - f; affected.add(part.split.f); affected.add(part.split.m); }
    }
    // 3) Oglindă Partea III: carti/limba_romana = total_imprumuturi (dacă nu au fost modificate manual)
    const oldTotal = part.key === "documente_inregistrate" ? (+row.total_imprumuturi || 0) : null;
    // 4) Coloane calculate (sum) — recalcul pentru tot rândul
    cols.forEach(([k, l, t, o]) => {
      if (o && o.sum) { const s = o.sum.reduce((a, src) => a + (+row[src] || 0), 0); if ((+row[k] || 0) !== s) { row[k] = s; affected.add(k); } }
    });
    if (part.key === "documente_inregistrate" && affected.has("total_imprumuturi")) {
      const nt = +row.total_imprumuturi || 0;
      ["carti", "limba_romana"].forEach((f) => {
        const cur = +row[f] || 0;
        if (cur === 0 || cur === oldTotal) { if (row[f] !== nt) { row[f] = nt; affected.add(f); } }
      });
    }
    // Partea IV: dacă Partea III are total pentru acea dată, el are prioritate față de Σ CZU
    if (part.key === "documente_continut_czu" && state.aux && state.aux.p3) {
      const p3 = state.aux.p3[row.data] || 0;
      if (p3 > 0 && (+row.total_imprumuturi || 0) !== p3) { row.total_imprumuturi = p3; affected.add("total_imprumuturi"); }
    }
    return affected;
  }

  // ---- Salvare / adăugare / ștergere ---------------------------------------
  function markOOR(inp) { const mx = inp.dataset.max; if (mx == null) return; inp.classList.toggle("oor", (+inp.value || 0) > +mx); }

  async function saveCell(e) {
    const el = e.target, id = +el.dataset.id, col = el.dataset.col, type = el.dataset.type;
    const row = state.rows.find((r) => r.id === id); if (!row) return;
    if (type === "int") row[col] = toInt(el.value);
    else if (type === "bool") row[col] = el.checked;
    else row[col] = el.value === "" ? (el.dataset.req ? "" : null) : el.value;
    const affected = deriveRow(state.part, row, col);
    const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
    const { error } = await sb.from(state.part.key).update(payload).eq("id", id);
    if (error) { toast("Eroare salvare: " + error.message); return; }
    el.classList.remove("dirty"); markOOR(el);
    // reflectă valorile derivate în celelalte celule fără reîncărcare (păstrează focus)
    affected.forEach((k) => {
      if (k === col) return;
      const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`);
      if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else inp.value = row[k] == null ? "" : row[k]; markOOR(inp); }
    });
    renderFooter();
    toast("Salvat");
  }

  async function addRow() {
    const p = state.part, base = {};
    if (p.period !== "crud") { base.an = state.an; base.luna = state.luna; }
    if (p.categorie) base.categorie_varsta = state.cat;
    const firstDay = `${state.an}-${pad2(state.luna)}-01`;
    if (p.period === "zi") { const d = prompt("Data (AAAA-LL-ZZ):", firstDay); if (!d) return; base[p.dateField] = d; }
    else if (p.period === "lista" && p.dateField) base[p.dateField] = firstDay;
    p.cols.forEach(([k, l, t, o]) => { if (o && o.req && (t === "text" || t === "txt") && base[k] === undefined) base[k] = ""; });
    const { error } = await sb.from(p.key).insert(base);
    if (error) { toast("Eroare: " + error.message); return; }
    await loadData();
  }

  async function deleteRow(id) {
    if (!confirm("Ștergeți acest rând definitiv?")) return;
    const { error } = await sb.from(state.part.key).delete().eq("id", id);
    if (error) { toast("Eroare: " + error.message); return; }
    await loadData();
  }

  // ---- Export Excel (vizualizarea curentă) ----------------------------------
  function exportCurrent() {
    const p = state.part;
    if (special() || !state.rows.length) { toast("Nimic de exportat"); return; }
    const ws = XLSX.utils.json_to_sheet(state.rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, `Partea ${p.nr}`.slice(0, 31));
    XLSX.writeFile(wb, `partea_${p.nr}_${state.an}_${pad2(state.luna)}.xlsx`);
  }

  // ---- Personal -------------------------------------------------------------
  async function loadStaff() {
    const { data } = await sb.from("personal").select("*").order("nume_prenume");
    state.staff = data || [];
    $("staffList").innerHTML = state.staff.filter((s) => s.activ).map((s) => `<option value="${esc(s.nume_prenume)}">`).join("");
  }
  function renderStaff() {
    const rows = state.staff.map((s) =>
      `<tr><td class="txtcell" style="text-align:left">${esc(s.nume_prenume)}</td>
       <td><input type="checkbox" ${s.activ ? "checked" : ""} class="sa" data-sid="${s.id}"></td>
       <td><button class="del" data-sid="${s.id}">✕</button></td></tr>`).join("");
    $("content").innerHTML =
      `<div class="tablebox" style="max-width:520px"><table>
        <thead><tr><th style="text-align:left">Nume și prenume</th><th>Activ</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="3" style="padding:16px;color:var(--muted)">Nicio persoană încă.</td></tr>`}</tbody>
       </table></div>
       <div style="margin-top:12px;display:flex;gap:8px;max-width:520px">
         <input id="newStaff" placeholder="Nume și prenume nou" style="flex:1">
         <button id="addStaff">+ Adaugă</button></div>`;
    $("addStaff").onclick = addStaff;
    $("content").querySelectorAll(".sa").forEach((c) => (c.onchange = () => toggleStaff(+c.dataset.sid, c.checked)));
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteStaff(+b.dataset.sid)));
  }
  async function addStaff() {
    const n = $("newStaff").value.trim(); if (!n) return;
    const { error } = await sb.from("personal").insert({ nume_prenume: n, activ: true });
    if (error) { toast("Eroare: " + error.message); return; }
    await loadStaff(); renderStaff();
  }
  async function toggleStaff(id, activ) { await sb.from("personal").update({ activ }).eq("id", id); await loadStaff(); }
  async function deleteStaff(id) {
    if (!confirm("Ștergeți această persoană?")) return;
    await sb.from("personal").delete().eq("id", id); await loadStaff(); renderStaff();
  }

  // ---- Import / Migrare -----------------------------------------------------
  function renderImport() {
    $("content").innerHTML =
      `<div style="max-width:720px">
        <h3 style="margin-top:0">Migrare din aplicația desktop (SQLite)</h3>
        <p class="status">Alegeți fișierul <b>biblioteca.db</b> din aplicația desktop
          (de obicei în <code>app\\data</code>). Datele se adaugă în Supabase.</p>
        <input type="file" id="sqliteFile" accept=".db,.sqlite,.sqlite3">
        <button id="doSqlite">Importă din SQLite</button>
        <hr style="margin:20px 0;border:0;border-top:1px solid var(--line)">
        <h3>Import din Excel (backup al acestei aplicații)</h3>
        <input type="file" id="xlsxFile" accept=".xlsx">
        <button id="doXlsx">Importă din Excel</button>
        <pre id="importLog" style="margin-top:16px;background:#0f172a;color:#cbd5e1;padding:12px;border-radius:8px;max-height:320px;overflow:auto;font-size:12px;white-space:pre-wrap"></pre>
        <p class="status">⚠ Importul <b>adaugă</b> rânduri. Rulați o singură dată per fișier.</p>
      </div>`;
    const logEl = $("importLog"), log = (m) => { logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; };
    const run = async (btnId, fileId, fn) => {
      const f = $(fileId).files[0]; if (!f) { toast("Alegeți un fișier"); return; }
      logEl.textContent = ""; $(btnId).disabled = true;
      try { await fn(sb, f, log); await loadStaff(); } catch (e) { log("✗ " + e.message); } finally { $(btnId).disabled = false; }
    };
    $("doSqlite").onclick = () => run("doSqlite", "sqliteFile", window.RegistruImport.migrateSqlite);
    $("doXlsx").onclick = () => run("doXlsx", "xlsxFile", window.RegistruImport.importExcel);
  }

  // ---- Realtime -------------------------------------------------------------
  function subscribe(table) {
    if (channel) sb.removeChannel(channel);
    channel = sb.channel("rt-" + table)
      .on("postgres_changes", { event: "*", schema: "public", table }, () => { if (state.part === STAFF) loadStaff().then(renderStaff); else loadData(); })
      .subscribe((st) => { const ok = st === "SUBSCRIBED"; $("live").textContent = ok ? "live" : "offline"; $("live").classList.toggle("live", ok); });
  }

  // ---- Backup ---------------------------------------------------------------
  function refreshBackupInfo() {
    const h = window.RegistruBackup.hoursSinceBackup(), info = $("backupInfo"), btn = $("backup");
    if (h === null) { info.textContent = "fără backup local încă"; btn.style.background = "var(--accent)"; btn.style.color = "#fff"; }
    else if (h > 24) { info.textContent = `ultimul backup acum ${Math.floor(h / 24)} zi(le)`; btn.style.background = "var(--accent)"; btn.style.color = "#fff"; }
    else { info.textContent = "backup local recent ✔"; btn.style.background = ""; btn.style.color = ""; }
  }
  async function doBackup() { await window.RegistruBackup.runBackup(sb, { note: (m) => ($("backupInfo").textContent = m) }); refreshBackupInfo(); }

  // ---- Legături -------------------------------------------------------------
  $("loginBtn").onclick = login;
  $("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
  $("addRow").onclick = addRow;
  $("exportBtn").onclick = exportCurrent;
  $("pdfBtn").onclick = () => { if (!special()) window.RegistruExport.exportPDF(state.part, state.rows, { an: state.an, luna: state.luna, cat: state.cat, cols: effCols(), toast }); };
  $("wordBtn").onclick = () => { if (!special()) window.RegistruExport.exportWord(state.part, state.rows, { an: state.an, luna: state.luna, cat: state.cat, cols: effCols() }); };
  $("backup").onclick = doBackup;
  $("logout").onclick = async () => { await sb.auth.signOut(); location.reload(); };

  sb.auth.getSession().then(({ data }) => { if (data.session) onLoggedIn(); });
})();
