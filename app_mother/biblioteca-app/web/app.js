// ============================================================================
// Motorul aplicației web — dashboard, taburi lună/categorie, generare automată
// zile lucrătoare, copiere lună, totaluri, sincronizare, validări (range_config),
// etichete custom, presets, export, backup automat, setări.
// ============================================================================
(function () {
  const $ = (id) => document.getElementById(id);
  const PARTS = window.REGISTRU_PARTS, MAX5 = window.REGISTRU_MAX5, partCols = window.partCols;
  const HOME = { key: "__home" }, STAFF = { key: "__staff" }, IMPORT = { key: "__import" };
  const LUNI = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"];

  if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) $("authErr").textContent = "Lipsește config.js.";
  const sb = window.supabase.createClient(window.SUPABASE_URL || "", window.SUPABASE_ANON_KEY || "");

  const state = { part: null, an: 2026, luna: 7, cat: "copii", rows: [], staff: [], prior: null,
    aux: {}, presets: {}, labels: {}, ranges: {}, settings: {}, badges: {} };
  let channel = null;

  const P3_DIN = ["consultare_pe_loc", "imprumut_pe_loc", "imprumut_la_domiciliu", "imprumut_inter_bibliotecar"];
  const P2_INTR = ["imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii"];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const toInt = (v) => Math.max(0, parseInt(v, 10) || 0);
  const ddmm = (d, m) => `${pad2(d)}.${pad2(m)}`;
  function toast(m) { const t = $("toast"); t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 1500); }
  const effCols = () => partCols(state.part, state.cat);
  const isPart = () => state.part && state.part.key && state.part.key.indexOf("__") !== 0;

  function weekdays(year, month) {
    const out = [], d = new Date(year, month - 1, 1);
    while (d.getMonth() === month - 1) { const wd = d.getDay(); if (wd >= 1 && wd <= 5) out.push(ddmm(d.getDate(), month)); d.setDate(d.getDate() + 1); }
    return out;
  }
  function todayStr() { const d = new Date(); return { d: ddmm(d.getDate(), d.getMonth() + 1), y: d.getFullYear(), m: d.getMonth() + 1 }; }

  // ---- Autentificare --------------------------------------------------------
  async function login() {
    $("authErr").textContent = "";
    const { error } = await sb.auth.signInWithPassword({ email: $("email").value.trim(), password: $("password").value });
    if (error) { $("authErr").textContent = error.message; return; }
    onLoggedIn();
  }
  async function onLoggedIn() {
    const { data } = await sb.auth.getUser(); if (!data.user) return;
    $("auth").classList.add("hidden"); $("app").classList.remove("hidden");
    $("who").textContent = data.user.email; $("who2").textContent = data.user.email;
    initSelectors(); await loadSettings(); await loadStaff(); renderNav();
    selectPart("__home"); refreshBackupInfo(); maybeAutoBackup();
  }

  function initSelectors() {
    if ($("an").options.length) return;
    for (let y = 2023; y <= 2027; y++) $("an").add(new Option(y, y, false, y === state.an));
    $("an").onchange = () => { state.an = +$("an").value; state.part === HOME ? renderHome() : (!special() && loadData()); };
  }
  const special = () => state.part === STAFF || state.part === IMPORT || state.part === HOME;

  // ---- Setări ---------------------------------------------------------------
  async function loadSettings() {
    const { data } = await sb.from("app_settings").select("*");
    state.settings = {}; (data || []).forEach((r) => (state.settings[r.cheie] = r.valoare));
    const nm = state.settings.library_name || "Biblioteca", loc = state.settings.library_loc || "";
    $("brandsub").textContent = nm + (loc ? " · " + loc : "");
  }
  function openSettings() {
    const s = state.settings;
    $("settings").innerHTML = `<div class="box"><h3>⚙ Setări</h3>
      <label>Numele bibliotecii</label><input id="st_name" value="${esc(s.library_name || "")}">
      <label>Localitate</label><input id="st_loc" value="${esc(s.library_loc || "")}">
      <label>Backup automat — la câte zile (0 = dezactivat)</label><input id="st_bk" type="number" min="0" value="${esc(s.backup_days || "3")}">
      <div class="actions"><button class="ghost" id="st_cancel">Renunță</button><button class="ok" id="st_save">Salvează</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("st_cancel").onclick = () => $("settings").classList.add("hidden");
    $("st_save").onclick = async () => {
      const rows = [
        { cheie: "library_name", valoare: $("st_name").value.trim() },
        { cheie: "library_loc", valoare: $("st_loc").value.trim() },
        { cheie: "backup_days", valoare: String(toInt($("st_bk").value)) },
      ];
      const { error } = await sb.from("app_settings").upsert(rows, { onConflict: "cheie" });
      if (error) { toast("Eroare: " + error.message); return; }
      await loadSettings(); $("settings").classList.add("hidden");
      if (state.part === HOME) renderHome(); toast("Setări salvate");
    };
  }

  // ---- Navigație + badges ---------------------------------------------------
  function badge(st) { return st === "ok" ? '<span class="b" style="color:#4ade80">✓</span>' : st === "warn" ? '<span class="b" style="color:#fbbf24">⚠</span>' : ""; }
  function renderNav() {
    $("nav").innerHTML =
      `<button class="nav" data-key="__home">🏠 Acasă</button>` +
      PARTS.map((p) => `<button class="nav" data-key="${p.key}">${p.nr}. ${esc(p.title.split(" ").slice(0, 2).join(" "))}${badge(state.badges[p.key])}</button>`).join("") +
      `<div class="navsep"></div><button class="nav" data-key="__staff">👤 Personal</button>` +
      `<button class="nav" data-key="__import">⬆ Import / Migrare</button>`;
    $("nav").querySelectorAll("button.nav").forEach((b) => (b.onclick = () => selectPart(b.dataset.key)));
    markActive(state.part ? state.part.key : "__home");
  }
  function markActive(key) { document.querySelectorAll("#nav button.nav").forEach((b) => b.classList.toggle("active", b.dataset.key === key)); }

  function selectPart(key) {
    if (channel) { sb.removeChannel(channel); channel = null; }
    if (key === "__home") { state.part = HOME; updateChrome(); renderHome(); return; }
    if (key === "__staff") { state.part = STAFF; updateChrome(); renderStaff(); subscribe("personal"); return; }
    if (key === "__import") { state.part = IMPORT; updateChrome(); renderImport(); return; }
    state.part = PARTS.find((p) => p.key === key);
    if (!state.part.categorie) state.cat = "copii";
    updateChrome(); loadData(); subscribe(state.part.key);
  }

  function updateChrome() {
    const p = state.part, sp = special();
    markActive(p.key);
    $("hbadge").textContent = p === HOME ? "🏠" : p === STAFF ? "👤" : p === IMPORT ? "⬆" : p.nr;
    $("title").textContent = p === HOME ? "Acasă" : p === STAFF ? "Personal (responsabili)" : p === IMPORT ? "Import / Migrare date" : `Partea ${p.nr}. ${p.title}`;
    $("subtitle").textContent = isPart() && p.period !== "crud" ? `${LUNI[state.luna - 1]} ${state.an}` : "";
    $("anWrap").style.display = (p === HOME || (isPart() && p.period !== "crud")) ? "" : "none";
    buildToolbar();
    // taburi
    const showMonths = isPart() && p.period !== "crud";
    $("tabs").classList.toggle("hidden", !showMonths);
    if (showMonths) $("tabs").innerHTML = LUNI.map((m, i) => `<button class="${i + 1 === state.luna ? "active" : ""}" data-l="${i + 1}">${m}</button>`).join("");
    $("tabs").querySelectorAll("button").forEach((b) => (b.onclick = () => { state.luna = +b.dataset.l; loadData(); updateChrome(); }));
    const showCat = isPart() && p.categorie;
    $("cattabs").classList.toggle("hidden", !showCat);
    if (showCat) {
      $("cattabs").innerHTML = [["copii", "Copii"], ["adulti", "Adulți"]].map(([v, l]) => `<button class="${v === state.cat ? "active" : ""}" data-c="${v}">${l}</button>`).join("");
      $("cattabs").querySelectorAll("button").forEach((b) => (b.onclick = () => { state.cat = b.dataset.c; loadData(); updateChrome(); }));
    }
    $("hintbar").classList.toggle("hidden", !isPart());
  }

  function buildToolbar() {
    const p = state.part, tb = $("toolbar");
    if (!isPart()) { tb.innerHTML = ""; tb.style.display = "none"; return; }
    tb.style.display = "flex";
    const btns = [];
    if (p.period === "zi") { btns.push(["genDays", "🗓 Generează zilele", "ghost"], ["copyPrev", "⧉ Copiază luna trecută", "ghost"], ["addRow", "+ Zi", "ghost"]); }
    else if (p.period === "luna") { btns.push(["genDays", "🗓 Creează luna", "ghost"], ["copyPrev", "⧉ Copiază luna trecută", "ghost"]); }
    else if (p.period === "lista") { btns.push(["addRow", "+ Rând", "ghost"], ["copyPrev", "⧉ Copiază luna trecută", "ghost"]); }
    else { btns.push(["addRow", "+ Rând", "ghost"]); }
    if (p.period !== "crud") btns.push(["ranges", "⚖ Range-uri", "ghost"]);
    btns.push(["sp", "", ""], ["exportXls", "⬇ Excel", "ghost"], ["exportPdf", "⬇ PDF", "ghost"], ["exportDoc", "⬇ Word", "ghost"], ["printBtn", "🖶 Printează", "ghost"]);
    tb.innerHTML = btns.map(([id, l, c]) => id === "sp" ? '<span style="flex:1"></span>' : `<button id="${id}" class="${c}">${l}</button>`).join("");
    const bind = (id, fn) => { const el = $(id); if (el) el.onclick = fn; };
    bind("genDays", autoGenerate); bind("copyPrev", copyLastMonth); bind("addRow", addRow); bind("ranges", openRanges);
    bind("exportXls", exportCurrent);
    bind("exportPdf", () => window.RegistruExport.exportPDF(p, state.rows, exCtx()));
    bind("exportDoc", () => window.RegistruExport.exportWord(p, state.rows, exCtx()));
    bind("printBtn", printCurrent);
  }
  const exCtx = () => ({ an: state.an, luna: state.luna, cat: state.cat, cols: effCols(), toast });

  // ---- Încărcare + meta -----------------------------------------------------
  async function loadData() {
    const p = state.part;
    let q = sb.from(p.key).select("*");
    if (p.period !== "crud") q = q.eq("an", state.an).eq("luna", state.luna);
    if (p.categorie) q = q.eq("categorie_varsta", state.cat);
    q = p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true });
    const { data, error } = await q;
    if (error) { toast("Eroare: " + error.message); return; }
    state.rows = data || [];
    await syncIn(p); await loadMeta(p);
    state.prior = null;
    if (p.cumulative) {
      let pq = sb.from(p.key).select("*").eq("an", state.an).lt("luna", state.luna);
      if (p.categorie) pq = pq.eq("categorie_varsta", state.cat);
      const { data: pd } = await pq; state.prior = computeAcc(effCols(), pd || []);
    }
    renderGrid();
  }
  async function loadMeta(p) {
    state.presets = {}; state.labels = {}; state.ranges = {};
    const [lab, pre, rng] = await Promise.all([
      sb.from("etichete_custom").select("camp,eticheta_custom").eq("parte", p.pid),
      sb.from("text_presets").select("camp,valoare").eq("parte", p.pid),
      sb.from("range_config").select("coloana,valoare_min,valoare_max").eq("parte", p.pid),
    ]);
    (lab.data || []).forEach((r) => { if (r.eticheta_custom) state.labels[r.camp] = r.eticheta_custom; });
    (pre.data || []).forEach((r) => { (state.presets[r.camp] = state.presets[r.camp] || []).push(r.valoare); });
    (rng.data || []).forEach((r) => { state.ranges[r.coloana] = { min: r.valoare_min, max: r.valoare_max }; });
  }
  const label = (c) => state.labels[c[0]] || c[1];
  const colRange = (p, key) => state.ranges[key] || { min: 0, max: MAX5.has(p.key) ? 5 : 30 };

  // ---- Antet + celule -------------------------------------------------------
  function spanRow(cols, keyFn) {
    let html = "", i = 0;
    while (i < cols.length) { const k = keyFn(cols[i]); if (k == null) { html += "<th></th>"; i++; continue; }
      let j = i + 1; while (j < cols.length && keyFn(cols[j]) === k) j++; html += `<th colspan="${j - i}">${esc(k)}</th>`; i = j; }
    return html;
  }
  function buildHead(cols) {
    const hasSG = cols.some((c) => c[3] && c[3].sg), hasG = cols.some((c) => c[3] && c[3].g); let h = "";
    if (hasSG) h += `<tr>${spanRow(cols, (c) => (c[3] && c[3].sg) || null)}<th></th></tr>`;
    if (hasG || hasSG) h += `<tr>${spanRow(cols, (c) => (c[3] && c[3].g) || null)}<th></th></tr>`;
    h += `<tr>${cols.map((c) => `<th data-col="${c[0]}" title="Dublu-clic: redenumire">${esc(label(c))}</th>`).join("")}<th></th></tr>`;
    return h;
  }
  function inputHtml(p, r, c) {
    const [k, l, t, o = {}] = c;
    const attr = `data-id="${r.id}" data-col="${k}" data-type="${t}" ${o.req ? 'data-req="1"' : ""}`;
    const v = r[k];
    if (t === "int") {
      const rg = colRange(p, k), oor = !o.ro && ((+v || 0) > rg.max || (+v || 0) < rg.min);
      return `<input class="num${o.ro ? " calc" : ""}${oor ? " oor" : ""}" type="number" ${o.ro ? "readonly" : `data-min="${rg.min}" data-max="${rg.max}"`} value="${esc(v == null ? 0 : v)}" ${attr}>`;
    }
    if (t === "bool") return `<input type="checkbox" ${v ? "checked" : ""} ${attr}>`;
    if (t === "date") return `<input class="date" type="text" placeholder="ZZ.LL" value="${esc(v)}" ${attr}>`;
    if (t === "staff") return `<input class="txt" type="text" list="staffList" value="${esc(v)}" ${attr}>`;
    if (t === "txt") return `<input class="txt wide" type="text" list="pl_${k}" value="${esc(v)}" ${attr}>`;
    return `<input class="txt" type="text" list="pl_${k}" value="${esc(v)}" ${attr}>`;
  }
  function presetDatalists(cols) {
    return cols.filter((c) => c[2] === "text" || c[2] === "txt").map((c) =>
      `<datalist id="pl_${c[0]}">${(state.presets[c[0]] || []).map((v) => `<option value="${esc(v)}">`).join("")}</datalist>`).join("");
  }

  function renderGrid() {
    const p = state.part, cols = effCols(), tk = todayStr(), showToday = p.period === "zi" && tk.y === state.an && tk.m === state.luna;
    const body = state.rows.map((r) => {
      const isToday = showToday && r[p.dateField] === tk.d;
      const tds = cols.map((c) => `<td>${inputHtml(p, r, c)}</td>`).join("");
      return `<tr class="${isToday ? "today" : ""}">${tds}<td><button class="del" data-id="${r.id}" title="Șterge">✕</button></td></tr>`;
    }).join("");
    const hintMsg = p.period === "zi" ? "Apăsați butonul Generează zilele." : "Apăsați butonul + Rând.";
    const empty = `<tr><td colspan="${cols.length + 1}" style="padding:16px;color:var(--muted)">Niciun rând. ${hintMsg}</td></tr>`;
    $("content").innerHTML = presetDatalists(cols) +
      `<div class="tablebox"><table><thead>${buildHead(cols)}</thead><tbody>${state.rows.length ? body : empty}</tbody><tfoot id="gridFoot"></tfoot></table></div>`;
    $("content").querySelectorAll("thead tr:last-child th[data-col]").forEach((th) => { th.style.cursor = "pointer"; th.ondblclick = () => renameCol(th.dataset.col, cols.find((c) => c[0] === th.dataset.col)); });
    $("content").querySelectorAll("tbody input").forEach((inp) => {
      inp.addEventListener("change", saveCell);
      if (inp.type !== "checkbox" && !inp.readOnly) {
        inp.addEventListener("input", () => inp.classList.add("dirty"));
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); moveDown(inp); } });
      }
    });
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteRow(+b.dataset.id)));
    renderFooter();
  }
  function moveDown(inp) {
    const col = inp.dataset.col, all = [...$("content").querySelectorAll(`tbody input[data-col="${col}"]`)];
    const i = all.indexOf(inp); if (i >= 0 && i < all.length - 1) all[i + 1].focus(); else inp.blur();
  }

  function computeAcc(cols, rows) {
    const acc = {};
    cols.forEach(([k, l, t, o]) => { if (t === "int") acc[k] = rows.reduce((s, r) => s + (+r[k] || 0), 0); else if (t === "bool" && o && o.ct) acc[k] = rows.reduce((s, r) => s + (r[k] ? 1 : 0), 0); });
    return acc;
  }
  function footerRow(label2, acc, cols, cls) {
    return "<tr>" + cols.map((c, i) => i === 0 ? `<td class="totlbl">${esc(label2)}</td>` : `<td class="${cls}">${acc[c[0]] == null ? "" : acc[c[0]]}</td>`).join("") + `<td class="${cls}"></td></tr>`;
  }
  function renderFooter() {
    const cols = effCols(), acc = computeAcc(cols, state.rows);
    let html = footerRow("Total", acc, cols, "totalrow");
    if (state.part.cumulative && state.prior) {
      const cum = {}; cols.forEach(([k, l, t, o]) => { if (t === "int" || (t === "bool" && o && o.ct)) cum[k] = (state.prior[k] || 0) + (acc[k] || 0); });
      html += footerRow("Total de la început", cum, cols, "cumrow");
    }
    const f = $("gridFoot"); if (f) f.innerHTML = html;
  }

  // ---- Reguli intra-rând ----------------------------------------------------
  function deriveRow(part, row, col) {
    const cols = effCols(), affected = new Set([col]);
    if (part.key === "evidenta_utilizatori") {
      const P = +row.prescolari || 0, E = +row.elevi || 0, C = +row.copii_pana_16 || 0;
      if (col === "elevi") { row.copii_pana_16 = P + E; affected.add("copii_pana_16"); }
      else if (col === "copii_pana_16") { row.elevi = Math.max(0, C - P); affected.add("elevi"); }
      else if (col === "prescolari") { if (C > 0) { row.elevi = Math.max(0, C - P); affected.add("elevi"); } else { row.copii_pana_16 = P + E; affected.add("copii_pana_16"); } }
    }
    if (part.split && col === part.split.total) { const t = +row[part.split.total] || 0; if (t > 0) { const f = Math.floor(t / 2); row[part.split.f] = f; row[part.split.m] = t - f; affected.add(part.split.f); affected.add(part.split.m); } }
    const oldTotal = part.key === "documente_inregistrate" ? (+row.total_imprumuturi || 0) : null;
    cols.forEach(([k, l, t, o]) => { if (o && o.sum) { const s = o.sum.reduce((a, x) => a + (+row[x] || 0), 0); if ((+row[k] || 0) !== s) { row[k] = s; affected.add(k); } } });
    if (part.key === "documente_inregistrate" && affected.has("total_imprumuturi")) {
      const nt = +row.total_imprumuturi || 0;
      ["carti", "limba_romana"].forEach((f) => { const cur = +row[f] || 0; if (cur === 0 || cur === oldTotal) { if (row[f] !== nt) { row[f] = nt; affected.add(f); } } });
    }
    if (part.key === "documente_continut_czu" && state.aux && state.aux.p3) {
      const p3 = state.aux.p3[row.data] || 0; if (p3 > 0 && (+row.total_imprumuturi || 0) !== p3) { row.total_imprumuturi = p3; affected.add("total_imprumuturi"); }
    }
    return affected;
  }

  function markOOR(inp) { const mx = inp.dataset.max; if (mx == null) return; const v = +inp.value || 0; inp.classList.toggle("oor", v > +mx || v < +(inp.dataset.min || 0)); }

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
    if ((type === "text" || type === "txt") && row[col]) {
      const arr = state.presets[col] || (state.presets[col] = []);
      if (!arr.includes(row[col])) { arr.push(row[col]); const dl = $("pl_" + col); if (dl) dl.insertAdjacentHTML("beforeend", `<option value="${esc(row[col])}">`); sb.from("text_presets").upsert({ parte: state.part.pid, camp: col, valoare: row[col] }, { onConflict: "parte,camp,valoare", ignoreDuplicates: true }).then(() => {}, () => {}); }
    }
    affected.forEach((k) => { if (k === col) return; const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`); if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else inp.value = row[k] == null ? "" : row[k]; markOOR(inp); } });
    renderFooter();
  }

  async function addRow() {
    const p = state.part, base = {};
    if (p.period !== "crud") { base.an = state.an; base.luna = state.luna; }
    if (p.categorie) base.categorie_varsta = state.cat;
    if (p.period === "zi") { const d = prompt("Data (ZZ.LL):", ddmm(1, state.luna)); if (!d) return; base[p.dateField] = d; }
    else if (p.period === "lista" && p.dateField) base[p.dateField] = ddmm(1, state.luna);
    p.cols.forEach(([k, l, t, o]) => { if (o && o.req && (t === "text" || t === "txt") && base[k] === undefined) base[k] = ""; });
    const { error } = await sb.from(p.key).insert(base); if (error) { toast("Eroare: " + error.message); return; }
    await loadData();
  }
  async function deleteRow(id) {
    if (!confirm("Ștergeți acest rând?")) return;
    const { error } = await sb.from(state.part.key).delete().eq("id", id); if (error) { toast("Eroare: " + error.message); return; }
    await loadData();
  }

  // ---- Generare automată zile lucrătoare + copiere lună ---------------------
  async function autoGenerate() {
    const p = state.part;
    if (p.period === "luna") {
      if (state.rows.length) { toast("Rândul lunii există deja"); return; }
      await sb.from(p.key).insert({ an: state.an, luna: state.luna, categorie_varsta: state.cat });
      await loadData(); return;
    }
    const have = new Set(state.rows.map((r) => r[p.dateField]));
    const toAdd = weekdays(state.an, state.luna).filter((d) => !have.has(d)).map((d) => {
      const o = { an: state.an, luna: state.luna, [p.dateField]: d }; if (p.categorie) o.categorie_varsta = state.cat; return o;
    });
    if (!toAdd.length) { toast("Zilele lucrătoare există deja"); return; }
    const { error } = await sb.from(p.key).insert(toAdd); if (error) { toast("Eroare: " + error.message); return; }
    toast(`${toAdd.length} zile adăugate`); await loadData();
  }
  async function copyLastMonth() {
    const p = state.part, pm = state.luna === 1 ? 12 : state.luna - 1, py = state.luna === 1 ? state.an - 1 : state.an;
    let q = sb.from(p.key).select("*").eq("an", py).eq("luna", pm); if (p.categorie) q = q.eq("categorie_varsta", state.cat);
    const { data } = await q; if (!data || !data.length) { toast("Luna trecută nu are date"); return; }
    const valCols = effCols().map((c) => c[0]).filter((k) => k !== p.dateField && !["an", "luna", "categorie_varsta"].includes(k));
    if (p.period === "zi" || p.period === "luna") {
      // Actualizează rândurile existente (evită conflictul cu constrângerea unică)
      if (!state.rows.length) { toast("Generați întâi zilele lunii"); return; }
      const map = {};
      if (p.period === "zi") data.forEach((r) => { if (r[p.dateField]) map[String(r[p.dateField]).slice(0, 2)] = r; });
      else map._ = data[0];
      let n = 0;
      for (const r of state.rows) {
        const src = map[p.period === "zi" ? String(r[p.dateField]).slice(0, 2) : "_"]; if (!src) continue;
        const upd = {}; valCols.forEach((k) => (upd[k] = src[k]));
        await sb.from(p.key).update(upd).eq("id", r.id); n++;
      }
      toast(`${n} rânduri actualizate din luna trecută`); await loadData();
    } else {
      const rows = data.map((r) => { const o = {}; Object.keys(r).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = r[k]; }); o.an = state.an; o.luna = state.luna; if (p.dateField && /^\d{2}\.\d{2}$/.test(o[p.dateField] || "")) o[p.dateField] = o[p.dateField].slice(0, 3) + pad2(state.luna); return o; });
      const { error } = await sb.from(p.key).insert(rows); if (error) { toast("Eroare: " + error.message); return; }
      toast(`${rows.length} rânduri copiate`); await loadData();
    }
  }

  // ---- Range-uri (validare) -------------------------------------------------
  function openRanges() {
    const p = state.part, cols = effCols().filter((c) => c[2] === "int" && !(c[3] && c[3].ro));
    const rowsHtml = cols.map((c) => { const rg = colRange(p, c[0]); return `<div class="row" style="margin:4px 0"><div style="flex:1">${esc(label(c))}</div>
      <input type="number" id="rmin_${c[0]}" value="${rg.min}" style="width:80px"> – <input type="number" id="rmax_${c[0]}" value="${rg.max}" style="width:80px"></div>`; }).join("");
    $("settings").innerHTML = `<div class="box"><h3>⚖ Range-uri (min / max) — Partea ${p.nr}</h3>
      <p class="status">Valorile din afara intervalului sunt evidențiate cu roșu.</p>${rowsHtml}
      <div class="actions"><button class="ghost" id="rg_cancel">Renunță</button><button class="ok" id="rg_save">Salvează</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("rg_cancel").onclick = () => $("settings").classList.add("hidden");
    $("rg_save").onclick = async () => {
      const up = cols.map((c) => ({ parte: p.pid, coloana: c[0], valoare_min: toInt($("rmin_" + c[0]).value), valoare_max: toInt($("rmax_" + c[0]).value) }));
      const { error } = await sb.from("range_config").upsert(up, { onConflict: "parte,coloana" });
      if (error) { toast("Eroare: " + error.message); return; }
      $("settings").classList.add("hidden"); await loadData(); toast("Range-uri salvate");
    };
  }

  // ---- Sincronizare între părți ---------------------------------------------
  async function syncIn(p) {
    state.aux = {};
    try {
      if (p.key === "documente_continut_czu") {
        const { data } = await sb.from("documente_inregistrate").select("*").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const map = {}; (data || []).forEach((r) => { const t = (+r.total_imprumuturi || 0) || P3_DIN.reduce((a, k) => a + (+r[k] || 0), 0); if (r.data) map[r.data] = t; });
        state.aux.p3 = map; const czuKeys = effCols().find((c) => c[0] === "total_imprumuturi")[3].sum;
        for (const r of state.rows) { const czu = czuKeys.reduce((a, k) => a + (+r[k] || 0), 0); const total = (map[r.data] || 0) > 0 ? map[r.data] : czu; if ((+r.total_imprumuturi || 0) !== total) { r.total_imprumuturi = total; await sb.from(p.key).update({ total_imprumuturi: total }).eq("id", r.id); } }
      } else if (p.key === "evidenta_utilizatori_copii_adulti") {
        const q = (t) => sb.from(t).select("data,total_participanti").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const [ix, xi] = await Promise.all([q("instruiri"), q("activitati_culturale")]);
        const im = {}, xm = {}; (ix.data || []).forEach((r) => { if (r.data) im[r.data] = (im[r.data] || 0) + (+r.total_participanti || 0); }); (xi.data || []).forEach((r) => { if (r.data) xm[r.data] = (xm[r.data] || 0) + (+r.total_participanti || 0); });
        for (const r of state.rows) { const u = {}; const ins = im[r.data] || 0, act = xm[r.data] || 0;
          if ((+r.instruiri || 0) !== ins) { r.instruiri = ins; u.instruiri = ins; } if ((+r.activitati_culturale_stiintifice || 0) !== act) { r.activitati_culturale_stiintifice = act; u.activitati_culturale_stiintifice = act; }
          const it = P2_INTR.reduce((a, k) => a + (+r[k] || 0), 0); if ((+r.intrari_total_zi || 0) !== it) { r.intrari_total_zi = it; u.intrari_total_zi = it; }
          if (Object.keys(u).length) await sb.from(p.key).update(u).eq("id", r.id); }
      }
    } catch (e) { /* nu bloca */ }
  }

  // ---- Dashboard ------------------------------------------------------------
  async function computeBadges() {
    for (const p of PARTS) {
      let q = sb.from(p.key).select(p.period === "crud" ? "id" : "luna,categorie_varsta");
      if (p.period !== "crud") q = q.eq("an", state.an);
      const { data } = await q; const rows = data || [];
      if (p.period === "crud") { state.badges[p.key] = rows.length ? "ok" : "empty"; continue; }
      const need = p.categorie ? 24 : 12, seen = new Set();
      rows.forEach((r) => seen.add(p.categorie ? `${r.luna}|${r.categorie_varsta}` : String(r.luna)));
      state.badges[p.key] = seen.size === 0 ? "empty" : seen.size >= need ? "ok" : "warn";
    }
  }
  async function renderHome() {
    updateChrome();
    $("content").innerHTML = `<div class="status">Se încarcă…</div>`;
    await computeBadges(); renderNav();
    const done = PARTS.filter((p) => state.badges[p.key] === "ok").length;
    const warn = PARTS.filter((p) => state.badges[p.key] === "warn").length;
    const empty = PARTS.filter((p) => state.badges[p.key] === "empty").length;
    const pct = Math.round((done / PARTS.length) * 100);
    const nm = state.settings.library_name || "Biblioteca", loc = state.settings.library_loc || "";
    const todo = PARTS.filter((p) => state.badges[p.key] !== "ok").map((p) => `<div>Partea ${p.nr}. ${esc(p.title)} — <b>${state.badges[p.key] === "empty" ? "neîncepută" : "parțială"}</b></div>`).join("") || `<div>Toate părțile sunt complete 🎉</div>`;
    $("content").innerHTML = `
      <div style="margin-bottom:14px"><h2 style="margin:0">Bun venit</h2>
        <div style="font-size:16px;color:var(--accent);font-weight:600">${esc(nm)}</div>
        <div class="status">${esc(loc)} · anul ${state.an}</div></div>
      <div class="cards">
        <div class="card"><h3>Progres registru ${state.an}</h3>
          <div class="progress"><div style="width:${pct}%"></div><span>${pct}% părți complete</span></div>
          <div class="kpis"><div><b style="color:var(--ok)">${done}</b>complete</div><div><b style="color:var(--warn)">${warn}</b>cu atenție</div><div><b>${empty}</b>neîncepute</div></div>
          <h3 style="margin-top:16px">De completat</h3><div class="todo">${todo}</div>
        </div>
        <div class="card"><h3>Backup</h3>
          <p class="status" id="homeBk">—</p>
          <button id="homeBackup" style="width:100%;margin-bottom:8px">⬇ Salvează copie acum</button>
          <p class="status">Copia locală (Excel + SQLite) rămâne pe acest calculator.</p>
          <h3 style="margin-top:16px">Setări</h3>
          <button class="ghost" id="homeSettings" style="width:100%">⚙ Nume bibliotecă, backup automat…</button>
        </div>
      </div>`;
    const h = window.RegistruBackup.hoursSinceBackup();
    $("homeBk").textContent = h === null ? "Nu există încă copii de rezervă." : h > 24 ? `Ultimul backup acum ${Math.floor(h / 24)} zi(le).` : "Backup local recent ✔";
    $("homeBackup").onclick = doBackup; $("homeSettings").onclick = openSettings;
  }

  // ---- Personal / Import (neschimbate în esență) ----------------------------
  async function loadStaff() {
    const { data } = await sb.from("personal").select("*").order("nume_prenume");
    state.staff = data || []; $("staffList").innerHTML = state.staff.filter((s) => s.activ).map((s) => `<option value="${esc(s.nume_prenume)}">`).join("");
  }
  function renderStaff() {
    const rows = state.staff.map((s) => `<tr><td class="txtcell" style="text-align:left">${esc(s.nume_prenume)}</td><td><input type="checkbox" ${s.activ ? "checked" : ""} class="sa" data-sid="${s.id}"></td><td><button class="del" data-sid="${s.id}">✕</button></td></tr>`).join("");
    $("content").innerHTML = `<div class="tablebox" style="max-width:520px"><table><thead><tr><th style="text-align:left">Nume și prenume</th><th>Activ</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="3" style="padding:16px;color:var(--muted)">Nicio persoană încă.</td></tr>`}</tbody></table></div>
      <div style="margin-top:12px;display:flex;gap:8px;max-width:520px"><input id="newStaff" placeholder="Nume și prenume nou" style="flex:1"><button id="addStaff">+ Adaugă</button></div>`;
    $("addStaff").onclick = addStaff;
    $("content").querySelectorAll(".sa").forEach((c) => (c.onchange = () => toggleStaff(+c.dataset.sid, c.checked)));
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteStaff(+b.dataset.sid)));
  }
  async function addStaff() { const n = $("newStaff").value.trim(); if (!n) return; const { error } = await sb.from("personal").insert({ nume_prenume: n, activ: true }); if (error) { toast("Eroare: " + error.message); return; } await loadStaff(); renderStaff(); }
  async function toggleStaff(id, activ) { await sb.from("personal").update({ activ }).eq("id", id); await loadStaff(); }
  async function deleteStaff(id) { if (!confirm("Ștergeți persoana?")) return; await sb.from("personal").delete().eq("id", id); await loadStaff(); renderStaff(); }

  function renderImport() {
    $("content").innerHTML = `<div style="max-width:720px"><h3 style="margin-top:0">Migrare din aplicația desktop (SQLite)</h3>
      <p class="status">Alegeți fișierul <b>biblioteca.db</b> din aplicația desktop (folderul <code>app\\data</code>).</p>
      <input type="file" id="sqliteFile" accept=".db,.sqlite,.sqlite3"><button id="doSqlite">Importă din SQLite</button>
      <hr style="margin:20px 0;border:0;border-top:1px solid var(--line)"><h3>Import din Excel (backup)</h3>
      <input type="file" id="xlsxFile" accept=".xlsx"><button id="doXlsx">Importă din Excel</button>
      <pre id="importLog" style="margin-top:16px;background:#0f172a;color:#cbd5e1;padding:12px;border-radius:8px;max-height:320px;overflow:auto;font-size:12px;white-space:pre-wrap"></pre>
      <p class="status">⚠ Importul adaugă rânduri. Rulați o singură dată per fișier.</p></div>`;
    const logEl = $("importLog"), log = (m) => { logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; };
    const run = async (btnId, fileId, fn) => { const f = $(fileId).files[0]; if (!f) { toast("Alegeți un fișier"); return; } logEl.textContent = ""; $(btnId).disabled = true; try { await fn(sb, f, log); await loadStaff(); } catch (e) { log("✗ " + e.message); } finally { $(btnId).disabled = false; } };
    $("doSqlite").onclick = () => run("doSqlite", "sqliteFile", window.RegistruImport.migrateSqlite);
    $("doXlsx").onclick = () => run("doXlsx", "xlsxFile", window.RegistruImport.importExcel);
  }

  // ---- Export / print / backup ----------------------------------------------
  function exportCurrent() { const p = state.part; if (!isPart() || !state.rows.length) { toast("Nimic de exportat"); return; } const ws = XLSX.utils.json_to_sheet(state.rows); const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, `Partea ${p.nr}`.slice(0, 31)); XLSX.writeFile(wb, `partea_${p.nr}_${state.an}_${pad2(state.luna)}.xlsx`); }
  function printCurrent() {
    const p = state.part, cols = effCols();
    const head = `<tr>${cols.map((c) => `<th>${esc(label(c))}</th>`).join("")}</tr>`;
    const body = state.rows.map((r) => `<tr>${cols.map(([k, l, t]) => `<td>${t === "bool" ? (r[k] ? "✓" : "") : esc(r[k])}</td>`).join("")}</tr>`).join("");
    const w = window.open("", "_blank");
    w.document.write(`<html><head><meta charset="utf-8"><title>Partea ${p.nr}</title><style>@page{size:A4 landscape}body{font:11px Segoe UI,sans-serif}h3{margin:0 0 8px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:3px;text-align:center}th{background:#eef2f7}</style></head><body><h3>Partea ${p.nr}. ${esc(p.title)} — ${LUNI[state.luna - 1]} ${state.an}${p.categorie ? " (" + state.cat + ")" : ""}</h3><table>${head}${body}</table><script>window.onload=function(){window.print()}<\/script></body></html>`);
    w.document.close();
  }
  function refreshBackupInfo() { const h = window.RegistruBackup.hoursSinceBackup(), info = $("backupInfo"); info.textContent = h === null ? "fără backup" : h > 24 ? `backup acum ${Math.floor(h / 24)}z` : "backup recent ✔"; }
  async function doBackup() { await window.RegistruBackup.runBackup(sb, { note: (m) => ($("backupInfo").textContent = m) }); refreshBackupInfo(); if (state.part === HOME) renderHome(); }
  async function maybeAutoBackup() {
    const days = toInt(state.settings.backup_days || "0"); if (!days) return;
    const h = window.RegistruBackup.hoursSinceBackup(); if (h !== null && h < days * 24) return;
    toast("Backup automat…"); await doBackup();
  }

  // ---- Etichete + realtime --------------------------------------------------
  async function renameCol(camp, col) {
    const nv = prompt("Etichetă coloană:", state.labels[camp] || col[1]); if (nv == null) return;
    const { error } = await sb.from("etichete_custom").upsert({ parte: state.part.pid, camp, eticheta_default: col[1], eticheta_custom: nv }, { onConflict: "parte,camp" });
    if (error) { toast("Eroare: " + error.message); return; } state.labels[camp] = nv; renderGrid();
  }
  function subscribe(table) {
    if (channel) sb.removeChannel(channel);
    channel = sb.channel("rt-" + table).on("postgres_changes", { event: "*", schema: "public", table }, () => { if (state.part === STAFF) loadStaff().then(renderStaff); else if (isPart()) loadData(); })
      .subscribe((st) => { const ok = st === "SUBSCRIBED"; $("live").textContent = ok ? "live" : "offline"; $("live").classList.toggle("live", ok); });
  }

  // ---- Legături -------------------------------------------------------------
  $("loginBtn").onclick = login;
  $("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
  $("settingsBtn").onclick = openSettings;
  $("logout").onclick = async () => { await sb.auth.signOut(); location.reload(); };
  sb.auth.getSession().then(({ data }) => { if (data.session) onLoggedIn(); });
})();
