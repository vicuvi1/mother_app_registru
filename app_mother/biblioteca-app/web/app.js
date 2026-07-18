// ============================================================================
// Motorul aplicației web — dashboard, taburi lună/categorie, generare automată
// zile lucrătoare, copiere lună, totaluri, sincronizare, validări (range_config),
// etichete custom, presets, export, backup automat, setări.
// ============================================================================
(function () {
  const $ = (id) => document.getElementById(id);
  const PARTS = window.REGISTRU_PARTS, MAX5 = window.REGISTRU_MAX5, partCols = window.partCols;
  const HOME = { key: "__home" }, STAFF = { key: "__staff" }, IMPORT = { key: "__import" }, FINAL = { key: "__final" };
  function download(blob, name) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); }
  const LUNI = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"];

  if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) $("authErr").textContent = "Lipsește config.js.";
  const sb = window.supabase.createClient(window.SUPABASE_URL || "", window.SUPABASE_ANON_KEY || "");

  const NOW = new Date();
  const state = { part: null, an: NOW.getFullYear(), luna: NOW.getMonth() + 1, cat: "copii", rows: [], staff: [], prior: null,
    aux: {}, presets: {}, labels: {}, ranges: {}, settings: {}, badges: {} };
  let channel = null;

  const P3_DIN = ["consultare_pe_loc", "imprumut_pe_loc", "imprumut_la_domiciliu", "imprumut_inter_bibliotecar"];
  const P2_INTR = ["imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii"];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cellText = (r, k, t) => t === "bool" ? (r[k] ? "✓" : "") : t === "monthlabel" ? (LUNI[(+r[k] || 1) - 1] || "") : (r[k] == null ? "" : String(r[k]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const toInt = (v) => Math.max(0, parseInt(v, 10) || 0);
  const ddmm = (d, m) => `${pad2(d)}.${pad2(m)}`;
  function toast(m) { const t = $("toast"); t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 1500); }
  let busyCount = 0;
  function setBusy(b) { busyCount += b ? 1 : -1; if (busyCount < 0) busyCount = 0; const el = $("busy"); if (el) el.classList.toggle("hidden", busyCount === 0); }
  const effCols = () => partCols(state.part, state.cat);
  const isPart = () => state.part && state.part.key && state.part.key.indexOf("__") !== 0;

  const weekdays = (y, m) => window.RegistruLogic.weekdays(y, m);
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
    initSelectors(); await loadSettings(); const firstRun = await seedDefaults(); await loadStaff(); renderNav();
    selectPart("__home"); refreshBackupInfo(); maybeAutoBackup();
    const F = window.RegistruLocalFolder;
    if (firstRun && !state.settings.library_name) setTimeout(openSettings, 500);
    else if (F && F.supported && !(await F.hasFolder()) && !localStorage.getItem("folderPromptSeen")) { try { localStorage.setItem("folderPromptSeen", "1"); } catch (e) {} setTimeout(openFolderSetup, 700); }
  }

  function initSelectors() {
    if ($("an").options.length) return;
    for (let y = state.an - 3; y <= state.an + 1; y++) $("an").add(new Option(y, y, false, y === state.an));
    $("an").onchange = () => { state.an = +$("an").value; if (state.part === HOME) renderHome(); else if (state.part === FINAL) renderFinal(); else if (!special()) { loadData(); updateChrome(); } };
  }
  const special = () => state.part === STAFF || state.part === IMPORT || state.part === HOME || state.part === FINAL;

  // ---- Setări ---------------------------------------------------------------
  function applyTheme(t) { document.documentElement.setAttribute("data-theme", t === "dark" ? "dark" : "light"); }
  async function loadSettings() {
    const { data } = await sb.from("app_settings").select("*");
    state.settings = {}; (data || []).forEach((r) => (state.settings[r.cheie] = r.valoare));
    const nm = state.settings.library_name || "Biblioteca", loc = state.settings.library_loc || "";
    $("brandsub").textContent = nm + (loc ? " · " + loc : "");
    applyTheme(state.settings.ui_theme || "light");
  }
  // Liste implicite utile (o singură dată, la prima pornire).
  const SEED_PRESETS = {
    part_05: { statut_socio_profesional: ["Elev", "Student", "Profesor", "Cercetător", "Pensionar", "Angajat", "Șomer", "Alte categorii"] },
    part_06: { grup_tinta_subiect: ["Elevi", "Studenți", "Adulți", "Pensionari", "Copii"] },
    part_09: { tema_instruirii: ["Utilizarea catalogului online", "Căutarea în baze de date", "Cultura informației", "Alfabetizare digitală", "Utilizarea internetului"] },
    part_11: { tipul_activitatii: ["Expoziție", "Lansare de carte", "Atelier", "Concurs", "Oră de lectură", "Masă rotundă", "Prezentare"] },
    part_12: { tipul_activitatii: ["Expoziție virtuală", "Atelier online", "Prezentare online", "Concurs online"], platforma: ["Facebook", "Zoom", "YouTube", "Google Meet", "Instagram", "Microsoft Teams"] },
  };
  async function seedDefaults() {
    if (state.settings.seeded_v1 === "1") return false;
    const rows = [];
    for (const pid in SEED_PRESETS) for (const camp in SEED_PRESETS[pid]) SEED_PRESETS[pid][camp].forEach((v) => rows.push({ parte: pid, camp, valoare: v }));
    try { if (rows.length) await sb.from("text_presets").upsert(rows, { onConflict: "parte,camp,valoare", ignoreDuplicates: true }); } catch (e) {}
    const up = [{ cheie: "seeded_v1", valoare: "1" }];
    if (state.settings.backup_days == null) up.push({ cheie: "backup_days", valoare: "7" });
    try { await sb.from("app_settings").upsert(up, { onConflict: "cheie" }); } catch (e) {}
    await loadSettings();
    return true;
  }
  function openSettings() {
    const s = state.settings, dark = s.ui_theme === "dark";
    $("settings").innerHTML = `<div class="box"><h3>⚙ Setări</h3>
      <label>Numele bibliotecii</label><input id="st_name" value="${esc(s.library_name || "")}">
      <label>Localitate</label><input id="st_loc" value="${esc(s.library_loc || "")}">
      <label>Temă interfață</label><select id="st_theme"><option value="light"${dark ? "" : " selected"}>Deschis</option><option value="dark"${dark ? " selected" : ""}>Întunecat</option></select>
      <label>Orientare printare / PDF</label><select id="st_print"><option value="landscape"${(s.print_orientation || "landscape") === "landscape" ? " selected" : ""}>Peisaj (recomandat)</option><option value="portrait"${s.print_orientation === "portrait" ? " selected" : ""}>Portret</option></select>
      <label class="row" style="margin-top:10px"><input type="checkbox" id="st_strict" ${s.strict_validation === "1" ? "checked" : ""} style="width:auto;margin-right:8px">Validare strictă (respinge valori peste limite)</label>
      <label>Backup automat — la câte zile (0 = dezactivat)</label><input id="st_bk" type="number" min="0" value="${esc(s.backup_days || "3")}">
      <div style="margin-top:12px"><button class="ghost" id="st_folder" style="width:100%">📁 Folder local de siguranță „registru mother"…</button></div>
      <div style="display:flex;gap:8px;margin-top:10px"><button class="ghost" id="st_help">Ajutor (scurtături)</button><button class="ghost" id="st_about">Despre</button></div>
      <div class="actions"><button class="ghost" id="st_cancel">Renunță</button><button class="ok" id="st_save">Salvează</button></div></div>`;
    $("settings").classList.remove("hidden");
    applyTheme($("st_theme").value);
    $("st_theme").onchange = () => applyTheme($("st_theme").value);
    $("st_cancel").onclick = () => { applyTheme(s.ui_theme || "light"); $("settings").classList.add("hidden"); };
    $("st_help").onclick = openHelp; $("st_about").onclick = openAbout;
    $("st_folder").onclick = openFolderSetup;
    $("st_save").onclick = async () => {
      const rows = [
        { cheie: "library_name", valoare: $("st_name").value.trim() },
        { cheie: "library_loc", valoare: $("st_loc").value.trim() },
        { cheie: "ui_theme", valoare: $("st_theme").value },
        { cheie: "print_orientation", valoare: $("st_print").value },
        { cheie: "strict_validation", valoare: $("st_strict").checked ? "1" : "0" },
        { cheie: "backup_days", valoare: String(toInt($("st_bk").value)) },
      ];
      const { error } = await sb.from("app_settings").upsert(rows, { onConflict: "cheie" });
      if (error) { toast("Eroare: " + error.message); return; }
      await loadSettings(); $("settings").classList.add("hidden");
      if (state.part === HOME) renderHome(); toast("Setări salvate");
    };
  }
  function openHelp() {
    const rows = [["Ctrl+F", "Găsește în tabel"], ["Ctrl+Z", "Anulează ultima editare"], ["Ctrl+C / Ctrl+V", "Copiază / lipește (din Excel)"], ["Ctrl+D", "Duplică rândul (părți evenimente)"], ["Ctrl+Shift+M", "Copiază luna trecută"], ["Ctrl+← / Ctrl+→", "Luna anterioară / următoare"], ["Ctrl+S", "Salvare (automată oricum)"], ["Ctrl+E", "Export Excel"], ["Enter", "Celula de mai jos"], ["Tab", "Celula următoare"], ["F1", "Acest ajutor"]];
    $("settings").innerHTML = `<div class="box"><h3>⌨ Scurtături tastatură</h3>
      <table style="width:100%;border-collapse:collapse">${rows.map(([k, d]) => `<tr><td style="padding:5px 8px;font-weight:600;white-space:nowrap">${k}</td><td style="padding:5px 8px;color:var(--muted)">${d}</td></tr>`).join("")}</table>
      <p class="status" style="margin-top:10px">Galben = ziua de azi · Bleu = calculat automat · Roșu = valoare invalidă</p>
      <div class="actions"><button class="ok" id="hl_close">Închide</button></div></div>`;
    $("settings").classList.remove("hidden"); $("hl_close").onclick = () => $("settings").classList.add("hidden");
  }
  function openAbout() {
    $("settings").innerHTML = `<div class="box"><h3>Despre</h3>
      <p style="font-weight:600">Registru Digital de Evidență a Activității Bibliotecii</p>
      <p class="status">Versiune web · multi-user (Supabase)</p>
      <p style="font-size:13px">Aplicație web pentru evidența activității bibliotecilor publice (12 părți ale registrului, export Word/PDF/Excel, backup, sincronizare în timp real).</p>
      <p class="status">Realizat de Victor Bărbuță · portare web</p>
      <div class="actions"><button class="ok" id="ab_close">Închide</button></div></div>`;
    $("settings").classList.remove("hidden"); $("ab_close").onclick = () => $("settings").classList.add("hidden");
  }

  // ---- Navigație + badges ---------------------------------------------------
  function badge(st) { return st === "ok" ? '<span class="b" style="color:#4ade80">✓</span>' : st === "warn" ? '<span class="b" style="color:#fbbf24">⚠</span>' : ""; }
  function renderNav() {
    $("nav").innerHTML =
      `<button class="nav" data-key="__home">🏠 Acasă</button>` +
      `<button class="nav" data-key="__final">📗 Registru final</button>` +
      `<div class="navsep"></div>` +
      PARTS.map((p) => `<button class="nav" data-key="${p.key}">${p.nr}. ${esc(p.title.split(" ").slice(0, 2).join(" "))}${badge(state.badges[p.key])}</button>`).join("") +
      `<div class="navsep"></div><button class="nav" data-key="__staff">👤 Personal</button>` +
      `<button class="nav" data-key="__import">⬆ Import / Migrare</button>`;
    $("nav").querySelectorAll("button.nav").forEach((b) => (b.onclick = () => selectPart(b.dataset.key)));
    markActive(state.part ? state.part.key : "__home");
  }
  function markActive(key) { document.querySelectorAll("#nav button.nav").forEach((b) => b.classList.toggle("active", b.dataset.key === key)); }

  function selectPart(key) {
    if (channel) { sb.removeChannel(channel); channel = null; }
    const aside = document.querySelector("aside"); if (aside) aside.classList.remove("open");
    undoStack.length = 0;
    if (key === "__home") { state.part = HOME; updateChrome(); renderHome(); return; }
    if (key === "__final") { state.part = FINAL; updateChrome(); renderFinal(); return; }
    if (key === "__staff") { state.part = STAFF; updateChrome(); renderStaff(); subscribe("personal"); return; }
    if (key === "__import") { state.part = IMPORT; updateChrome(); renderImport(); return; }
    state.part = PARTS.find((p) => p.key === key);
    if (!state.part.categorie) state.cat = "copii";
    updateChrome(); loadData(); subscribe(state.part.key);
  }

  function updateChrome() {
    const p = state.part, sp = special();
    markActive(p.key);
    $("hbadge").textContent = p === HOME ? "🏠" : p === FINAL ? "📗" : p === STAFF ? "👤" : p === IMPORT ? "⬆" : p.nr;
    $("title").textContent = p === HOME ? "Acasă" : p === FINAL ? "Registru final" : p === STAFF ? "Personal (responsabili)" : p === IMPORT ? "Import / Migrare date" : `Partea ${p.nr}. ${p.title}`;
    $("subtitle").textContent = isPart() ? (p.period === "luna" ? `Anul ${state.an}` : (p.period !== "crud" ? `${LUNI[state.luna - 1]} ${state.an}` : "")) : "";
    $("anWrap").style.display = (p === HOME || p === FINAL || (isPart() && p.period !== "crud")) ? "" : "none";
    buildToolbar();
    // taburi lună — doar la părțile zilnice/evenimente
    const showMonths = isPart() && (p.period === "zi" || p.period === "lista");
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
    if (p.period === "zi") { btns.push(["genDays", "🗓 Generează zilele", "ghost"], ["exclDays", "🚫 Zile libere", "ghost"], ["copyPrev", "⧉ Copiază luna trecută", "ghost"], ["addRow", "+ Zi", "ghost"]); }
    else if (p.period === "luna") { btns.push(["genDays", "🗓 Creează lunile", "ghost"]); }
    else if (p.period === "lista") { btns.push(["addRow", "+ Rând", "ghost"], ["dupRow", "⧉ Duplică rând", "ghost"], ["copyPrev", "⧉ Copiază luna trecută", "ghost"]); }
    else { btns.push(["addRow", "+ Rând", "ghost"]); }
    if (p.period === "zi" || p.period === "lista") btns.push(["autoFill", "🎲 Auto valori", "ghost"]);
    if (p.period !== "crud") btns.push(["ranges", "⚖ Range-uri", "ghost"]);
    if (p.cols.some((c) => c[2] === "text" || c[2] === "txt" || c[2] === "staff")) btns.push(["presets", "📝 Liste text", "ghost"]);
    btns.push(["sp", "", ""], ["exportXls", "⬇ Excel", "ghost"], ["exportPdf", "⬇ PDF", "ghost"], ["exportDoc", "⬇ Word", "ghost"], ["printBtn", "🖶 Printează", "ghost"]);
    tb.innerHTML = btns.map(([id, l, c]) => id === "sp" ? '<span style="flex:1"></span>' : `<button id="${id}" class="${c}">${l}</button>`).join("");
    const bind = (id, fn) => { const el = $(id); if (el) el.onclick = fn; };
    bind("genDays", autoGenerate); bind("exclDays", openExcluded); bind("copyPrev", copyLastMonth); bind("addRow", addRow); bind("ranges", openRanges); bind("presets", openPresetLists); bind("dupRow", duplicateRow); bind("autoFill", autoFillValues);
    bind("exportXls", exportCurrent);
    bind("exportPdf", () => window.RegistruExport.exportPDF(p, state.rows, exCtx()));
    bind("exportDoc", () => window.RegistruExport.exportWord(p, state.rows, exCtx()));
    bind("printBtn", printCurrent);
  }
  const exCtx = () => ({ an: state.an, luna: state.luna, cat: state.cat, cols: effCols(), orientation: state.settings.print_orientation || "landscape", toast });

  // ---- Încărcare + meta -----------------------------------------------------
  async function loadData(fromScaffold) {
    const p = state.part;
    setBusy(true);
    try {
      let q = sb.from(p.key).select("*");
      if (p.period === "luna") q = q.eq("an", state.an); // toate cele 12 luni
      else if (p.period !== "crud") q = q.eq("an", state.an).eq("luna", state.luna);
      if (p.categorie) q = q.eq("categorie_varsta", state.cat);
      q = p.period === "luna" ? q.order("luna", { ascending: true }) : (p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true }));
      const { data, error } = await q;
      if (error) { toast("Eroare: " + error.message); return; }
      state.rows = data || [];
      // Auto-schelet (ca în desktop): la deschiderea unei luni goale, creează
      // automat zilele lucrătoare (părți zilnice) sau rândul lunii (parte lunară).
      if (!fromScaffold && !state.rows.length && (p.period === "zi" || p.period === "luna")) {
        const scaffold = [];
        if (p.period === "luna") { for (let m = 1; m <= 12; m++) { const o = { an: state.an, luna: m }; if (p.categorie) o.categorie_varsta = state.cat; scaffold.push(o); } }
        else { const excl = await getExcluded(state.an), exSet = new Set(excl[state.luna] || []); weekdays(state.an, state.luna).filter((d) => !exSet.has(d)).forEach((d) => { const o = { an: state.an, luna: state.luna, [p.dateField]: d }; if (p.categorie) o.categorie_varsta = state.cat; scaffold.push(o); }); }
        if (scaffold.length) { const { error: e2 } = await sb.from(p.key).insert(scaffold); if (!e2) return loadData(true); }
      }
      await syncIn(p); await loadMeta(p);
      state.prior = null;
      if (p.cumulative) {
        let pq = sb.from(p.key).select("*").eq("an", state.an).lt("luna", state.luna);
        if (p.categorie) pq = pq.eq("categorie_varsta", state.cat);
        const { data: pd } = await pq; state.prior = computeAcc(effCols(), pd || []);
      }
      renderGrid();
      saveSession();
    } finally { setBusy(false); }
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
    if (t === "monthlabel") return `<input class="txt calc" type="text" readonly value="${esc(LUNI[(+v || 1) - 1] || "")}" ${attr}>`;
    if (t === "bool") return `<input type="checkbox" ${v ? "checked" : ""} ${attr}>`;
    if (t === "date") return `<input class="date" type="text" placeholder="ZZ.LL" value="${esc(v)}" ${attr}>`;
    if (t === "staff") return `<input class="txt" type="text" value="${esc(v)}" ${attr}>`;
    if (t === "txt") return `<input class="txt wide" type="text" value="${esc(v)}" ${attr}>`;
    return `<input class="txt" type="text" value="${esc(v)}" ${attr}>`;
  }
  // Popup listă presets: click stânga → listă (ca în desktop); scrii direct → filtrează
  let presetPop = null;
  function ensurePresetPop() { if (!presetPop) { presetPop = document.createElement("div"); presetPop.className = "presetpop"; presetPop.style.display = "none"; document.body.appendChild(presetPop); } return presetPop; }
  function openPresetPopup(inp) {
    const col = inp.dataset.col;
    let vals = state.presets[col] ? state.presets[col].slice() : [];
    if (inp.dataset.type === "staff") { const names = state.staff.filter((s) => s.activ).map((s) => s.nume_prenume); vals = [...new Set([...names, ...vals])].sort((a, b) => String(a).localeCompare(b)); }
    if (!vals.length) { closePresetPopup(); return; }
    const flt = String(inp.value || "").toLowerCase();
    const shown = vals.filter((v) => v.toLowerCase().includes(flt));
    const pop = ensurePresetPop();
    pop.innerHTML = shown.length ? shown.map((v) => `<div class="pp-item">${esc(v)}</div>`).join("") : `<div class="pp-empty">Nicio potrivire · scrieți direct</div>`;
    const r = inp.getBoundingClientRect();
    pop.style.left = r.left + "px"; pop.style.top = (r.bottom + 2) + "px"; pop.style.minWidth = r.width + "px"; pop.style.display = "block";
    pop.querySelectorAll(".pp-item").forEach((d) => (d.onmousedown = (ev) => { ev.preventDefault(); inp.value = d.textContent; inp.dispatchEvent(new Event("change", { bubbles: true })); closePresetPopup(); }));
  }
  function closePresetPopup() { if (presetPop) presetPop.style.display = "none"; }

  function renderGrid() {
    const p = state.part, cols = effCols(), tk = todayStr(), showToday = p.period === "zi" && tk.y === state.an && tk.m === state.luna;
    const body = state.rows.map((r) => {
      const isToday = showToday && r[p.dateField] === tk.d;
      const cls = isToday ? "today" : (rowHasContent(r) ? "" : "blank");
      const tds = cols.map((c) => `<td>${inputHtml(p, r, c)}</td>`).join("");
      return `<tr class="${cls}">${tds}<td><button class="del" data-id="${r.id}" title="Șterge">✕</button></td></tr>`;
    }).join("");
    const hintMsg = p.period === "zi" ? "Apăsați butonul Generează zilele." : "Apăsați butonul + Rând.";
    const empty = `<tr><td colspan="${cols.length + 1}" style="padding:16px;color:var(--muted)">Niciun rând. ${hintMsg}</td></tr>`;
    $("content").innerHTML =
      `<div id="scrollNav" style="display:none;gap:6px;margin-bottom:8px"><button class="ghost" id="scL">◀ Stânga</button><button class="ghost" id="scR">Dreapta ▶</button><button class="ghost" id="scE">La sfârșit ▶▶</button></div>` +
      `<div class="tablebox"><table><thead>${buildHead(cols)}</thead><tbody>${state.rows.length ? body : empty}</tbody><tfoot id="gridFoot"></tfoot></table></div>`;
    setTimeout(() => {
      const box = $("content").querySelector(".tablebox"), nav = $("scrollNav");
      if (box && nav && box.scrollWidth > box.clientWidth + 4) {
        nav.style.display = "flex"; const step = () => Math.max(220, box.clientWidth * 0.6);
        $("scL").onclick = () => box.scrollBy({ left: -step(), behavior: "smooth" });
        $("scR").onclick = () => box.scrollBy({ left: step(), behavior: "smooth" });
        $("scE").onclick = () => box.scrollTo({ left: box.scrollWidth, behavior: "smooth" });
      }
    }, 0);
    $("content").querySelectorAll("thead tr:last-child th[data-col]").forEach((th) => { th.style.cursor = "pointer"; th.ondblclick = () => renameCol(th.dataset.col, cols.find((c) => c[0] === th.dataset.col)); });
    $("content").querySelectorAll("tbody input").forEach((inp) => {
      inp.addEventListener("change", saveCell);
      const t = inp.dataset.type;
      if (t === "text" || t === "txt" || t === "staff") {
        inp.addEventListener("focus", () => openPresetPopup(inp));
        inp.addEventListener("input", () => { inp.classList.add("dirty"); openPresetPopup(inp); });
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); closePresetPopup(); moveDown(inp); } else if (e.key === "Escape") closePresetPopup(); });
        inp.addEventListener("blur", () => setTimeout(closePresetPopup, 160));
      } else if (inp.type !== "checkbox" && !inp.readOnly) {
        inp.addEventListener("input", () => inp.classList.add("dirty"));
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); moveDown(inp); } });
      }
    });
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteRow(+b.dataset.id)));
    state.rows.forEach((r) => applyRowValidation(r.id));
    renderFooter();
  }
  function moveDown(inp) {
    const col = inp.dataset.col, all = [...$("content").querySelectorAll(`tbody input[data-col="${col}"]`)];
    const i = all.indexOf(inp); if (i >= 0 && i < all.length - 1) all[i + 1].focus(); else inp.blur();
  }

  const computeAcc = (cols, rows) => window.RegistruLogic.sumCols(cols, rows);
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
    if (part.key === "evidenta_utilizatori" && ["elevi", "copii_pana_16", "prescolari"].indexOf(col) >= 0) {
      const r2 = window.RegistruLogic.copiiSplit(row.prescolari, row.elevi, row.copii_pana_16, col);
      ["prescolari", "elevi", "copii_pana_16"].forEach((k) => { if ((+row[k] || 0) !== r2[k]) { row[k] = r2[k]; affected.add(k); } });
    }
    if (part.split && col === part.split.total) { const t = +row[part.split.total] || 0; if (t > 0) { const g = window.RegistruLogic.genderSplit(t); row[part.split.f] = g.f; row[part.split.m] = g.m; affected.add(part.split.f); affected.add(part.split.m); } }
    const oldTotal = part.key === "documente_inregistrate" ? (+row.total_imprumuturi || 0) : null;
    cols.forEach(([k, l, t, o]) => { if (o && o.sum) { const s = o.sum.reduce((a, x) => a + (+row[x] || 0), 0); if ((+row[k] || 0) !== s) { row[k] = s; affected.add(k); } } });
    if (part.key === "documente_inregistrate" && affected.has("total_imprumuturi")) {
      // „Cărți" moștenește implicit totalul împrumuturilor cât timp e la valoarea implicită
      const nt = +row.total_imprumuturi || 0, cur = +row.carti || 0;
      if (cur === 0 || cur === oldTotal) { if (row.carti !== nt) { row.carti = nt; affected.add("carti"); } }
    }
    // Părțile III & VII — „Limba română" = „Cărți" − „Alte limbi" (calculat automat, read-only)
    if (part.key === "documente_inregistrate" || part.key === "documente_electronice") {
      const lr = window.RegistruLogic.docLangSplit(row.carti, row.alte_limbi).limba_romana;
      if ((+row.limba_romana || 0) !== lr) { row.limba_romana = lr; affected.add("limba_romana"); }
    }
    if (part.key === "documente_continut_czu") {
      // Totalul se preia din Partea III cât timp există date pentru zi (altfel rămâne cel editat manual)
      if (state.aux && state.aux.p3) { const p3 = state.aux.p3[row.data] || 0; if (p3 > 0 && (+row.total_imprumuturi || 0) !== p3) { row.total_imprumuturi = p3; affected.add("total_imprumuturi"); } }
      // „8 Limbi" (literatură) = Total − Σ(celelalte categorii CZU) — categoria-rest (calculat automat, read-only)
      const others = part.cols.filter((c) => c[0].indexOf("czu_") === 0 && c[0] !== "czu_8_limbi").map((c) => c[0]);
      const czu8 = window.RegistruLogic.czuRemainder(row.total_imprumuturi, others.map((k) => row[k]));
      if ((+row.czu_8_limbi || 0) !== czu8) { row.czu_8_limbi = czu8; affected.add("czu_8_limbi"); }
    }
    return affected;
  }
  // Constrângeri între câmpuri (evidențiere roșie, ca în desktop)
  function validateRow(part, row) {
    const bad = new Set();
    if (part.key === "evidenta_utilizatori" && (+row.copii_pana_16 || 0) > 0 && (+row.prescolari || 0) > (+row.copii_pana_16 || 0)) bad.add("prescolari");
    if (part.split) { const t = +row[part.split.total] || 0, m = +row[part.split.m] || 0, f = +row[part.split.f] || 0; if (m + f > t) { bad.add(part.split.m); bad.add(part.split.f); } }
    if (part.key === "documente_continut_czu") { const t = +row.total_imprumuturi || 0; if (t > 0) { const others = part.cols.filter((c) => c[0].indexOf("czu_") === 0 && c[0] !== "czu_8_limbi"); if (others.reduce((a, c) => a + (+row[c[0]] || 0), 0) > t) others.forEach((c) => bad.add(c[0])); } }
    if ((part.key === "documente_inregistrate" || part.key === "documente_electronice") && (+row.alte_limbi || 0) > (+row.carti || 0)) bad.add("alte_limbi");
    return bad;
  }
  function applyRowValidation(id) {
    const row = state.rows.find((r) => r.id === id); if (!row) return;
    const bad = validateRow(state.part, row);
    effCols().forEach(([k]) => { const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`); if (inp) inp.classList.toggle("badrel", bad.has(k)); });
  }

  function markOOR(inp) { const mx = inp.dataset.max; if (mx == null) return; const v = +inp.value || 0; inp.classList.toggle("oor", v > +mx || v < +(inp.dataset.min || 0)); }

  function setSaveState(s) {
    const el = $("saveState"); if (!el) return;
    const map = { saving: ["save-saving", "⏳ se salvează…"], ok: ["save-ok", "✔ salvat"], err: ["save-err", "⚠ eroare — reîncerc"], dirty: ["save-dirty", "• nesalvat"] };
    const [cls, txt] = map[s] || map.ok;
    el.className = "pill " + cls; el.textContent = txt;
  }
  // Salvare cu reîncercare la blip de rețea (last-write-wins; realtime menține
  // vizualizarea proaspătă). Fără blocare pe updated_at ca să nu apară „nu salvează".
  async function saveUpdate(table, payload, id) {
    for (let attempt = 0; ; attempt++) {
      const res = await sb.from(table).update(payload).eq("id", id).select().maybeSingle();
      if (!res.error) return res;
      if (attempt >= 2) return res;
      setSaveState("err");
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
    }
  }

  async function saveCell(e) {
    const el = e.target, id = +el.dataset.id, col = el.dataset.col, type = el.dataset.type;
    const row = state.rows.find((r) => r.id === id); if (!row) return;
    const oldVal = row[col];
    if (type === "int") row[col] = toInt(el.value);
    else if (type === "bool") row[col] = el.checked;
    else row[col] = el.value === "" ? (el.dataset.req ? "" : null) : el.value;
    const affected = deriveRow(state.part, row, col);
    if (state.settings.strict_validation === "1") {
      const rg = type === "int" ? colRange(state.part, col) : null;
      const oor = rg && ((+row[col] || 0) > rg.max || (+row[col] || 0) < rg.min);
      if (oor || validateRow(state.part, row).has(col)) {
        row[col] = oldVal; deriveRow(state.part, row, col);
        if (type === "bool") el.checked = !!oldVal; else el.value = oldVal == null ? "" : oldVal;
        toast(oor ? `Valoare în afara limitelor (${rg.min}–${rg.max})` : "Valoare respinsă (validare strictă)");
        markOOR(el); applyRowValidation(id); renderFooter(); return;
      }
    }
    const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
    setSaveState("saving");
    const res = await saveUpdate(state.part.key, payload, id);
    if (res.error) { setSaveState("err"); toast("Eroare salvare: " + res.error.message); return; }
    if (res.data) row.updated_at = res.data.updated_at;
    setSaveState("ok"); markDirty();
    if (oldVal !== row[col]) pushUndo({ kind: "cell", key: state.part.key, id, col, type, old: oldVal });
    // sincronizare inversă II → IX/XI
    const cdef = effCols().find((c) => c[0] === col);
    if (state.part.key === "evidenta_utilizatori_copii_adulti" && cdef && cdef[3] && cdef[3].rev) await reverseSync(col, row.data, +row[col] || 0);
    el.classList.remove("dirty"); markOOR(el);
    if ((type === "text" || type === "txt" || type === "staff") && row[col]) {
      const arr = state.presets[col] || (state.presets[col] = []);
      if (!arr.includes(row[col])) { arr.push(row[col]); const dl = $("pl_" + col); if (dl) dl.insertAdjacentHTML("beforeend", `<option value="${esc(row[col])}">`); sb.from("text_presets").upsert({ parte: state.part.pid, camp: col, valoare: row[col] }, { onConflict: "parte,camp,valoare", ignoreDuplicates: true }).then(() => {}, () => {}); }
    }
    affected.forEach((k) => { if (k === col) return; const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`); if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else inp.value = row[k] == null ? "" : row[k]; markOOR(inp); } });
    applyRowValidation(id);
    renderFooter();
  }

  // ---- Lipire din Excel (Ctrl+V) --------------------------------------------
  async function handlePaste(e) {
    const el = document.activeElement;
    if (!isPart() || !el || !el.matches || !el.matches("#content tbody input")) return;
    const text = (e.clipboardData || window.clipboardData).getData("text");
    if (!text) return;
    e.preventDefault();
    const cols = effCols();
    const startCol = cols.findIndex((c) => c[0] === el.dataset.col);
    const startIdx = state.rows.findIndex((r) => r.id === +el.dataset.id);
    if (startCol < 0 || startIdx < 0) return;
    const lines = text.replace(/\r\n?/g, "\n").replace(/\n$/, "").split("\n");
    let n = 0;
    for (let dr = 0; dr < lines.length; dr++) {
      const ri = startIdx + dr; if (ri >= state.rows.length) break;
      const row = state.rows[ri], cells = lines[dr].split("\t"), affected = new Set();
      for (let dc = 0; dc < cells.length; dc++) {
        const ci = startCol + dc; if (ci >= cols.length) break;
        const [k, l, t, o = {}] = cols[ci]; if (o.ro || t === "monthlabel") continue;
        const raw = cells[dc].trim();
        if (t === "int") row[k] = Math.max(0, parseInt(raw.replace(/[^\d-]/g, ""), 10) || 0);
        else if (t === "bool") row[k] = /^(1|true|da|x|✓|adevărat)$/i.test(raw);
        else row[k] = raw === "" ? (o.req ? "" : null) : raw;
        deriveRow(state.part, row, k).forEach((x) => affected.add(x)); affected.add(k);
      }
      if (affected.size) {
        const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
        await sb.from(state.part.key).update(payload).eq("id", row.id); n++;
      }
    }
    toast(`Lipit din Excel: ${n} rânduri`); await loadData();
  }

  async function addRow() {
    const p = state.part, base = {};
    if (p.period !== "crud") { base.an = state.an; base.luna = state.luna; }
    if (p.categorie) base.categorie_varsta = state.cat;
    if (p.period === "zi") { const d = prompt("Data (ZZ.LL):", ddmm(1, state.luna)); if (!d) return; base[p.dateField] = d; }
    else if (p.period === "lista" && p.dateField) base[p.dateField] = ddmm(1, state.luna);
    p.cols.forEach(([k, l, t, o]) => { if (o && o.req && (t === "text" || t === "txt") && base[k] === undefined) base[k] = ""; });
    const { data, error } = await sb.from(p.key).insert(base).select().maybeSingle(); if (error) { toast("Eroare: " + error.message); return; }
    if (data) pushUndo({ kind: "add", key: p.key, id: data.id });
    markDirty(); await loadData();
  }
  async function deleteRow(id) {
    if (!confirm("Ștergeți acest rând?")) return;
    const row = state.rows.find((r) => r.id === id);
    const { error } = await sb.from(state.part.key).delete().eq("id", id); if (error) { toast("Eroare: " + error.message); return; }
    if (row) pushUndo({ kind: "del", key: state.part.key, row: { ...row } });
    markDirty(); await loadData();
  }

  // ---- Generare automată zile lucrătoare + copiere lună ---------------------
  async function autoGenerate() {
    const p = state.part;
    if (p.period === "luna") {
      const have = new Set(state.rows.map((r) => r.luna)), toAdd = [];
      for (let m = 1; m <= 12; m++) if (!have.has(m)) { const o = { an: state.an, luna: m }; if (p.categorie) o.categorie_varsta = state.cat; toAdd.push(o); }
      if (!toAdd.length) { toast("Toate lunile există deja"); return; }
      const { error } = await sb.from(p.key).insert(toAdd); if (error) { toast("Eroare: " + error.message); return; }
      toast(`${toAdd.length} luni create`); await loadData(); return;
    }
    const have = new Set(state.rows.map((r) => r[p.dateField]));
    const excl = await getExcluded(state.an), exSet = new Set(excl[state.luna] || []);
    const toAdd = weekdays(state.an, state.luna).filter((d) => !have.has(d) && !exSet.has(d)).map((d) => {
      const o = { an: state.an, luna: state.luna, [p.dateField]: d }; if (p.categorie) o.categorie_varsta = state.cat; return o;
    });
    if (!toAdd.length) { toast("Zilele lucrătoare există deja"); return; }
    const { error } = await sb.from(p.key).insert(toAdd); if (error) { toast("Eroare: " + error.message); return; }
    toast(`${toAdd.length} zile adăugate`); await loadData();
  }
  async function autoFillValues() {
    const p = state.part;
    if (p.period !== "zi" && p.period !== "lista") { toast("Disponibil pe părți zilnice/evenimente"); return; }
    if (!state.rows.length) { toast("Generați întâi rândurile"); return; }
    if (!confirm("Completați rândurile cu valori aleatorii de test? Suprascrie valorile numerice existente.")) return;
    const cols = effCols().filter((c) => c[2] === "int" && !(c[3] && c[3].ro));
    const ups = state.rows.map((row) => {
      cols.forEach(([k]) => { const rg = colRange(p, k); row[k] = rg.min + Math.floor(Math.random() * (rg.max - rg.min + 1)); });
      cols.forEach(([k]) => deriveRow(p, row, k));
      const payload = {}; effCols().forEach(([k]) => (payload[k] = row[k]));
      return sb.from(p.key).update(payload).eq("id", row.id);
    });
    await Promise.all(ups);
    toast("Valori generate"); await loadData();
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
      const ups = [];
      for (const r of state.rows) {
        const src = map[p.period === "zi" ? String(r[p.dateField]).slice(0, 2) : "_"]; if (!src) continue;
        const upd = {}; valCols.forEach((k) => (upd[k] = src[k]));
        ups.push(sb.from(p.key).update(upd).eq("id", r.id));
      }
      await Promise.all(ups);
      toast(`${ups.length} rânduri actualizate din luna trecută`); await loadData();
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

  // ---- Liste text rapide (presets gestionate) -------------------------------
  function openPresetLists() {
    const p = state.part, cols = effCols().filter((c) => c[2] === "text" || c[2] === "txt" || c[2] === "staff");
    if (!cols.length) { toast("Nu există câmpuri text cu liste"); return; }
    const tabs = cols.map((c, i) => `<button class="ptab ${i === 0 ? "active" : ""}" data-i="${i}">${esc(label(c))}</button>`).join("");
    const areas = cols.map((c, i) => `<textarea class="parea" data-col="${c[0]}" rows="9" placeholder="O valoare pe rând..." style="${i === 0 ? "" : "display:none"}">${esc((state.presets[c[0]] || []).join("\n"))}</textarea>`).join("");
    $("settings").innerHTML = `<div class="box"><h3>📝 Liste text rapide — Partea ${p.nr}</h3>
      <p class="status">Introduceți valorile, câte una pe rând. Apoi le alegeți rapid în tabel (scrieți în celulă și apare lista).</p>
      <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">${tabs}</div>${areas}
      <div class="actions"><button class="ghost" id="pl_cancel">Renunță</button><button class="ok" id="pl_save">Salvează listele</button></div></div>`;
    $("settings").classList.remove("hidden");
    const areaEls = [...$("settings").querySelectorAll(".parea")];
    $("settings").querySelectorAll(".ptab").forEach((b) => (b.onclick = () => { $("settings").querySelectorAll(".ptab").forEach((x) => x.classList.remove("active")); b.classList.add("active"); areaEls.forEach((a, idx) => (a.style.display = idx === +b.dataset.i ? "" : "none")); }));
    $("pl_cancel").onclick = () => $("settings").classList.add("hidden");
    $("pl_save").onclick = async () => {
      for (const a of areaEls) {
        const col = a.dataset.col, vals = [...new Set(a.value.split("\n").map((s) => s.trim()).filter(Boolean))];
        await sb.from("text_presets").delete().eq("parte", p.pid).eq("camp", col);
        if (vals.length) await sb.from("text_presets").insert(vals.map((v) => ({ parte: p.pid, camp: col, valoare: v })));
        state.presets[col] = vals;
      }
      $("settings").classList.add("hidden"); toast("Liste salvate"); if (isPart()) renderGrid();
    };
  }

  // ---- Sincronizare între părți ---------------------------------------------
  async function syncIn(p) {
    state.aux = {};
    try {
      if (p.key === "documente_continut_czu") {
        const { data } = await sb.from("documente_inregistrate").select("*").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const map = {}; (data || []).forEach((r) => { const t = (+r.total_imprumuturi || 0) || P3_DIN.reduce((a, k) => a + (+r[k] || 0), 0); if (r.data) map[r.data] = t; });
        state.aux.p3 = map;
        const others = effCols().filter((c) => c[0].indexOf("czu_") === 0 && c[0] !== "czu_8_limbi").map((c) => c[0]);
        const ups = [];
        for (const r of state.rows) {
          const upd = {}, p3t = map[r.data] || 0;
          if (p3t > 0 && (+r.total_imprumuturi || 0) !== p3t) { r.total_imprumuturi = p3t; upd.total_imprumuturi = p3t; }
          const czu8 = window.RegistruLogic.czuRemainder(r.total_imprumuturi, others.map((k) => r[k]));
          if ((+r.czu_8_limbi || 0) !== czu8) { r.czu_8_limbi = czu8; upd.czu_8_limbi = czu8; }
          if (Object.keys(upd).length) ups.push(sb.from(p.key).update(upd).eq("id", r.id));
        }
        await Promise.all(ups);
      } else if (p.key === "evidenta_utilizatori_copii_adulti") {
        const q = (t) => sb.from(t).select("data,total_participanti").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const [ix, xi] = await Promise.all([q("instruiri"), q("activitati_culturale")]);
        const im = {}, xm = {}; (ix.data || []).forEach((r) => { if (r.data) im[r.data] = (im[r.data] || 0) + (+r.total_participanti || 0); }); (xi.data || []).forEach((r) => { if (r.data) xm[r.data] = (xm[r.data] || 0) + (+r.total_participanti || 0); });
        const ups = [];
        for (const r of state.rows) { const u = {}; const ins = im[r.data] || 0, act = xm[r.data] || 0;
          if ((+r.instruiri || 0) !== ins) { r.instruiri = ins; u.instruiri = ins; } if ((+r.activitati_culturale_stiintifice || 0) !== act) { r.activitati_culturale_stiintifice = act; u.activitati_culturale_stiintifice = act; }
          const it = P2_INTR.reduce((a, k) => a + (+r[k] || 0), 0); if ((+r.intrari_total_zi || 0) !== it) { r.intrari_total_zi = it; u.intrari_total_zi = it; }
          if (Object.keys(u).length) ups.push(sb.from(p.key).update(u).eq("id", r.id)); }
        await Promise.all(ups);
      }
    } catch (e) { /* nu bloca */ }
  }

  // Sincronizare inversă: editarea Părții II (instruiri/activități) → IX/XI.
  // Pune întreaga sumă pe primul rând al datei, restul = 0; dacă nu există, inserează.
  async function reverseSync(col, dateStr, value) {
    if (!dateStr) return;
    const table = col === "instruiri" ? "instruiri" : "activitati_culturale";
    const { data } = await sb.from(table).select("id").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat).eq("data", dateStr).order("id", { ascending: true });
    if (data && data.length) {
      await sb.from(table).update({ total_participanti: value }).eq("id", data[0].id);
      for (let i = 1; i < data.length; i++) await sb.from(table).update({ total_participanti: 0 }).eq("id", data[i].id);
    } else if (value > 0) {
      const ins = { an: state.an, luna: state.luna, categorie_varsta: state.cat, data: dateStr, total_participanti: value };
      if (table === "activitati_culturale") ins.total_activitati = 1;
      await sb.from(table).insert(ins);
    }
  }

  // ---- Excluse (zile libere / sărbători) ------------------------------------
  async function getExcluded(year) {
    const { data } = await sb.from("app_settings").select("valoare").eq("cheie", `excluded_days_${year}`).maybeSingle();
    let obj = {}; try { obj = JSON.parse((data && data.valoare) || "{}"); } catch (e) {}
    const res = {}; for (let m = 1; m <= 12; m++) res[m] = obj[String(m)] || obj[m] || [];
    return res;
  }
  async function saveExcluded(year, byMonth) {
    const payload = {}; for (let m = 1; m <= 12; m++) payload[String(m)] = byMonth[m] || [];
    await sb.from("app_settings").upsert({ cheie: `excluded_days_${year}`, valoare: JSON.stringify(payload) }, { onConflict: "cheie" });
  }
  async function openExcluded() {
    const excl = await getExcluded(state.an), cur = new Set(excl[state.luna] || []);
    const items = weekdays(state.an, state.luna).map((d) => `<label class="row" style="width:88px;display:inline-flex;margin:2px 0"><input type="checkbox" data-d="${d}" ${cur.has(d) ? "checked" : ""} style="width:auto;margin-right:6px">${d}</label>`).join("");
    $("settings").innerHTML = `<div class="box"><h3>🚫 Zile libere — ${LUNI[state.luna - 1]} ${state.an}</h3>
      <p class="status">Bifați zilele nelucrătoare (sărbători). Nu vor fi generate de „Generează zilele".</p>
      <div style="display:flex;flex-wrap:wrap;gap:4px">${items}</div>
      <div class="actions"><button class="ghost" id="ex_cancel">Renunță</button><button class="ok" id="ex_save">Salvează</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("ex_cancel").onclick = () => $("settings").classList.add("hidden");
    $("ex_save").onclick = async () => {
      const chosen = [...$("settings").querySelectorAll("input[data-d]:checked")].map((i) => i.dataset.d);
      excl[state.luna] = chosen; await saveExcluded(state.an, excl);
      // șterge rândurile deja generate care acum sunt excluse (partea curentă, luna curentă)
      const ex = new Set(chosen), toDel = state.rows.filter((r) => ex.has(r[state.part.dateField]));
      for (const r of toDel) await sb.from(state.part.key).delete().eq("id", r.id);
      $("settings").classList.add("hidden"); toast("Zile libere salvate"); if (isPart()) loadData();
    };
  }

  // ---- Sesiune (Continuă unde am rămas) -------------------------------------
  const IGNORE_CONTENT = new Set(["id", "an", "luna", "categorie_varsta", "is_auto_generated", "created_at", "updated_at", "data"]);
  function rowHasContent(r) {
    for (const k of Object.keys(r)) {
      if (IGNORE_CONTENT.has(k)) continue;
      const v = r[k];
      if (v === true) return true;
      if (typeof v === "number" && v !== 0) return true;
      if (typeof v === "string" && v.trim() !== "") return true;
    }
    return false;
  }
  async function loadSession() {
    const { data } = await sb.from("app_settings").select("valoare").eq("cheie", "session_state").maybeSingle();
    try { return JSON.parse((data && data.valoare) || "{}"); } catch (e) { return {}; }
  }
  async function saveSession() {
    if (!isPart()) return;
    const s = { part: state.part.key, year: state.an, month: state.luna, cat: state.cat };
    sb.from("app_settings").upsert({ cheie: "session_state", valoare: JSON.stringify(s) }, { onConflict: "cheie" }).then(() => {}, () => {});
  }
  function navigateTo(partKey, year, month, cat) {
    if (year) { state.an = year; $("an").value = String(year); }
    if (month) state.luna = month;
    if (cat) state.cat = cat;
    selectPart(partKey);
  }
  async function continueLastSession() {
    const s = await loadSession();
    const key = PARTS.some((p) => p.key === s.part) ? s.part : PARTS[0].key;
    navigateTo(key, s.year || state.an, s.month || state.luna, s.cat || "copii");
  }

  // ---- Pagina de titlu (copertă) --------------------------------------------
  const COVER_DEF = { institutie_1: "Ministerul Culturii al Republicii Moldova", institutie_2: "Consiliul Biblioteconomic Național", titlu: "Registru de evidență a activității", biblioteca: "", localitate: "", an: "" };
  async function getCover() {
    const { data } = await sb.from("app_settings").select("cheie,valoare").like("cheie", "cover_%");
    const s = {}; (data || []).forEach((r) => (s[r.cheie.slice(6)] = r.valoare));
    const nm = state.settings.library_name || "", loc = state.settings.library_loc || "", out = {};
    Object.keys(COVER_DEF).forEach((k) => { out[k] = (s[k] != null && s[k] !== "") ? s[k] : (k === "biblioteca" && nm ? nm : k === "localitate" && loc ? loc : COVER_DEF[k]); });
    return out;
  }
  async function openCover() {
    const c = await getCover(), f = (k, l) => `<label>${l}</label><input id="cov_${k}" value="${esc(c[k])}">`;
    $("settings").innerHTML = `<div class="box"><h3>📄 Pagina de titlu (copertă)</h3>
      ${f("institutie_1", "Instituția (rând 1)")}${f("institutie_2", "Instituția (rând 2)")}${f("titlu", "Titlu")}${f("biblioteca", "Biblioteca")}${f("localitate", "Localitate")}${f("an", "An (gol = anul selectat)")}
      <div class="actions"><button class="ghost" id="cov_cancel">Renunță</button><button class="ok" id="cov_save">Salvează</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("cov_cancel").onclick = () => $("settings").classList.add("hidden");
    $("cov_save").onclick = async () => {
      const up = Object.keys(COVER_DEF).map((k) => ({ cheie: "cover_" + k, valoare: $("cov_" + k).value.trim() }));
      await sb.from("app_settings").upsert(up, { onConflict: "cheie" });
      $("settings").classList.add("hidden"); toast("Copertă salvată");
    };
  }

  // ---- Dashboard ------------------------------------------------------------
  async function computeBadges() {
    state.incomplete = [];
    const results = await Promise.all(PARTS.map(async (p) => {
      let q = sb.from(p.key).select("*"); if (p.period !== "crud") q = q.eq("an", state.an);
      const { data } = await q; return { p, rows: data || [] };
    }));
    for (const { p, rows } of results) {
      if (p.period === "crud") { state.badges[p.key] = rows.length ? "ok" : "empty"; continue; }
      const cats = p.categorie ? ["adulti", "copii"] : [null];
      let inc = 0, total = 0;
      for (const cat of cats) for (let m = 1; m <= 12; m++) {
        total++;
        const sr = rows.filter((r) => r.luna === m && (!p.categorie || r.categorie_varsta === cat));
        let reason = null;
        if (!sr.length) reason = "fără rânduri";
        else if (!sr.some(rowHasContent)) reason = "toate valorile 0";
        if (reason) { inc++; state.incomplete.push({ key: p.key, nr: p.nr, title: p.title, month: m, cat, reason }); }
      }
      state.badges[p.key] = inc === 0 ? "ok" : inc >= total ? "empty" : "warn";
    }
  }
  function openIncompleteReport() {
    const items = state.incomplete.map((s, i) => `<div data-i="${i}" style="cursor:pointer">Partea ${s.nr}. ${esc(s.title)} — ${LUNI[s.month - 1]} ${state.an}${s.cat ? " (" + s.cat + ")" : ""} <span style="color:var(--muted)">(${s.reason})</span></div>`).join("") || "<div>Toate perioadele au date 🎉</div>";
    $("settings").innerHTML = `<div class="box"><h3>Luni fără date — ${state.an}</h3><p class="status">${state.incomplete.length} perioade. Click pe o linie pentru a merge acolo.</p><div class="todo">${items}</div><div class="actions"><button class="ghost" id="ir_close">Închide</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("ir_close").onclick = () => $("settings").classList.add("hidden");
    $("settings").querySelectorAll(".todo div[data-i]").forEach((d) => (d.onclick = () => { const s = state.incomplete[+d.dataset.i]; $("settings").classList.add("hidden"); navigateTo(s.key, state.an, s.month, s.cat || "copii"); }));
  }
  function openYearEnd() {
    $("settings").innerHTML = `<div class="box"><h3>📅 Asistent închidere an — ${state.an}</h3>
      <p class="status">${state.incomplete.length} perioade de verificat.</p>
      <label class="row" style="margin:6px 0"><input type="checkbox" style="width:auto;margin-right:8px">Am verificat lunile fără date / cu zerouri</label>
      <label class="row" style="margin:6px 0"><input type="checkbox" style="width:auto;margin-right:8px">Pagina de titlu (copertă) este completă</label>
      <label class="row" style="margin:6px 0"><input type="checkbox" style="width:auto;margin-right:8px">Am creat o copie de rezervă (backup)</label>
      <label class="row" style="margin:6px 0"><input type="checkbox" style="width:auto;margin-right:8px">Am exportat registrul pentru arhivă</label>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">
        <button class="ghost" id="ye_report">Raport luni…</button><button class="ghost" id="ye_cover">Copertă…</button>
        <button class="ghost" id="ye_backup">Backup acum</button><button class="ok" id="ye_final">Registru final…</button></div>
      <div class="actions"><button class="ghost" id="ye_close">Închide</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("ye_close").onclick = () => $("settings").classList.add("hidden");
    $("ye_report").onclick = openIncompleteReport;
    $("ye_cover").onclick = openCover;
    $("ye_backup").onclick = doBackup;
    $("ye_final").onclick = () => { $("settings").classList.add("hidden"); selectPart("__final"); };
  }
  async function renderHome() {
    updateChrome();
    $("content").innerHTML = `<div class="status">Se încarcă…</div>`;
    setBusy(true); await computeBadges(); setBusy(false); renderNav();
    const done = PARTS.filter((p) => state.badges[p.key] === "ok").length;
    const warn = PARTS.filter((p) => state.badges[p.key] === "warn").length;
    const empty = PARTS.filter((p) => state.badges[p.key] === "empty").length;
    const pct = Math.round((done / PARTS.length) * 100);
    const nm = state.settings.library_name || "Biblioteca dvs.", loc = state.settings.library_loc || "";
    const sess = await loadSession();
    const sp = PARTS.find((p) => p.key === sess.part);
    const sessHint = sp ? `Ultima sesiune: Partea ${sp.nr}${sess.month ? ", " + LUNI[sess.month - 1] : ""}${sess.year ? " " + sess.year : ""}` : "Nicio sesiune anterioară";
    const todo = state.incomplete.slice(0, 10).map((s, i) => `<div data-i="${i}" style="cursor:pointer">Partea ${s.nr}. ${esc(s.title)} — ${LUNI[s.month - 1]} ${state.an}${s.cat ? " (" + s.cat + ")" : ""} <span style="color:var(--muted)">(${s.reason})</span></div>`).join("") + (state.incomplete.length > 10 ? `<div style="color:var(--muted)">… și încă ${state.incomplete.length - 10} perioade</div>` : "") || `<div>Toate părțile sunt complete 🎉</div>`;
    $("content").innerHTML = `
      <div class="card" style="margin-bottom:16px"><h2 style="margin:0 0 2px">Bun venit</h2>
        <div style="font-size:17px;color:var(--accent);font-weight:600">${esc(nm)}</div>
        <div class="status">${esc(loc)}${loc ? " · " : ""}anul ${state.an}</div></div>
      <div class="cards">
        <div class="card"><h3>Progres registru ${state.an}</h3>
          <div class="progress"><div style="width:${pct}%"></div><span>${pct}% părți complete</span></div>
          <div class="kpis"><div><b style="color:var(--ok)">${done}</b>complete</div><div><b style="color:var(--warn)">${warn}</b>cu atenție</div><div><b>${empty}</b>neîncepute</div></div>
          <p class="status" id="sessHint" style="margin:12px 0 6px">${esc(sessHint)}</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap"><button id="homeContinue">Continuă unde am rămas</button><button class="ghost" id="homeYearEnd">Asistent închidere an…</button></div>
          <h3 style="margin-top:16px">De completat (prioritar)</h3>
          <p class="status">${state.incomplete.length} perioade fără date complete în ${state.an}.</p>
          <div class="todo">${todo}</div>
          <div style="margin-top:8px"><button class="ghost" id="homeReport">Raport complet luni fără date…</button></div>
        </div>
        <div class="card"><h3>Backup</h3>
          <p class="status" id="homeBk">—</p>
          <p class="status" id="homeCloudBk">—</p>
          <p class="status" id="homeFolderBk">—</p>
          <button id="homeBackup" style="width:100%;margin-bottom:8px">⬇ Salvează copie (descărcare + cloud + folder)</button>
          <button class="ghost" id="homeFolder" style="width:100%;margin-bottom:8px">📁 Salvează în folderul „registru mother"</button>
          <button class="ghost" id="homeFolderRestore" style="width:100%;margin-bottom:8px">📂 Restaurează din folderul local</button>
          <button class="ghost" id="homeCloudRestore" style="width:100%;margin-bottom:8px">☁ Restaurează din cloud…</button>
          <p class="status">Folder local = copie pe acest PC. Cloud = copie off-device. Descărcare = Excel/SQLite.</p>
          <h3 style="margin-top:16px">Document</h3>
          <button class="ghost" id="homeCover" style="width:100%;margin-bottom:8px">📄 Pagina de titlu (copertă)…</button>
          <button class="ghost" id="homeSettings" style="width:100%">⚙ Setări (nume, temă, backup automat)…</button>
        </div>
      </div>`;
    const h = window.RegistruBackup.hoursSinceBackup();
    $("homeBk").textContent = h === null ? "Local: nicio copie încă." : h > 24 ? `Local: acum ${Math.floor(h / 24)} zi(le).` : "Local: recent ✔";
    const hc = window.RegistruBackup.hoursSinceCloudBackup();
    $("homeCloudBk").textContent = hc === null ? "Cloud: nicio copie încă." : hc > 24 ? `Cloud: acum ${Math.floor(hc / 24)} zi(le).` : "Cloud: recent ✔";
    const F = window.RegistruLocalFolder;
    let lf = null; try { lf = localStorage.getItem("lastLocalFolder"); } catch (e) {}
    $("homeFolderBk").textContent = !F || !F.supported ? "Folder local: necesită Chrome/Edge." : (!(await F.hasFolder()) ? "Folder local: neconfigurat (apăsați butonul)." : (lf ? "Folder local: registru mother ✔" : "Folder local: configurat."));
    $("homeBackup").onclick = doBackup; $("homeSettings").onclick = openSettings;
    $("homeCloudRestore").onclick = openCloudRestore;
    $("homeFolder").onclick = async () => { const F2 = window.RegistruLocalFolder; if (!F2 || !F2.supported) { toast("Necesită Chrome/Edge"); return; } if (!(await F2.hasFolder())) return openFolderSetup(); const ok = await saveLocalFolder((m) => toast(m), true); if (ok) renderHome(); };
    $("homeFolderRestore").onclick = async () => { if (!confirm("Restaurați datele din folderul local registru mother? (se actualizează/adaugă)")) return; await restoreFromFolder(false, (m) => toast(m)); };
    $("homeContinue").onclick = continueLastSession; $("homeYearEnd").onclick = openYearEnd;
    $("homeReport").onclick = openIncompleteReport; $("homeCover").onclick = openCover;
    $("content").querySelectorAll(".todo div[data-i]").forEach((d) => (d.onclick = () => { const s = state.incomplete[+d.dataset.i]; navigateTo(s.key, state.an, s.month, s.cat || "copii"); }));
  }

  // ---- Registru final (document compilat pe an) -----------------------------
  function buildFinalPageList() {
    const pages = [];
    const add = (p, cat) => { if (p.period === "zi" || p.period === "lista") { for (let m = 1; m <= 12; m++) pages.push({ key: p.key, nr: p.nr, title: p.title, cat, month: m }); } else pages.push({ key: p.key, nr: p.nr, title: p.title, cat, month: null }); };
    for (const p of PARTS) add(p, p.categorie ? "adulti" : null);
    for (const p of PARTS) if (p.categorie) add(p, "copii");
    return pages;
  }
  function renderFinal() {
    const pages = buildFinalPageList();
    if (!state.finalChecked) state.finalChecked = {};
    const list = pages.map((pg, i) => {
      const checked = state.finalChecked[i] !== false;
      const lbl = `Partea ${pg.nr}. ${esc(pg.title)}${pg.cat ? " — " + (pg.cat === "adulti" ? "Adulți" : "Copii") : ""}${pg.month ? " — " + LUNI[pg.month - 1] : " — anul"} ${state.an}`;
      return `<div style="padding:2px 0"><label style="display:flex;gap:8px;align-items:center;font-size:13px"><input type="checkbox" data-i="${i}" ${checked ? "checked" : ""} style="width:auto">${lbl}</label></div>`;
    }).join("");
    $("content").innerHTML = `<div class="card" style="max-width:840px"><h3>📗 Registru final — anul ${state.an}</h3>
      <p class="status">Bifați paginile de inclus. Ordine: copertă, apoi toate părțile (Adulți), apoi toate părțile (Copii).</p>
      <label style="display:flex;gap:8px;align-items:center;margin:6px 0"><input type="checkbox" id="fin_cover" checked style="width:auto">Include pagina de titlu (copertă)</label>
      <div style="display:flex;gap:8px;margin:8px 0;flex-wrap:wrap"><button class="ghost" id="fin_all">Bifează tot</button><button class="ghost" id="fin_none">Debifează tot</button><button class="ghost" id="fin_coveredit">📄 Editează coperta</button></div>
      <div style="max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:10px">${list}</div>
      <div style="display:flex;gap:8px;margin-top:12px"><button class="ok" id="fin_word">⬇ Export Word (.doc)</button><button class="ghost" id="fin_pdf">⬇ Export PDF</button></div>
      <p class="status" id="fin_status" style="margin-top:10px"></p></div>`;
    $("content").querySelectorAll("input[data-i]").forEach((cb) => (cb.onchange = () => (state.finalChecked[+cb.dataset.i] = cb.checked)));
    const setAll = (v) => { pages.forEach((pg, i) => { state.finalChecked[i] = v; }); renderFinal(); };
    $("fin_all").onclick = () => setAll(true); $("fin_none").onclick = () => setAll(false);
    $("fin_coveredit").onclick = openCover;
    $("fin_word").onclick = () => exportFinal("word"); $("fin_pdf").onclick = () => exportFinal("pdf");
  }
  function finalSections(dataByPart) {
    const pages = buildFinalPageList().filter((pg, i) => state.finalChecked[i] !== false);
    return pages.map((pg) => {
      const p = PARTS.find((x) => x.key === pg.key), cols = partCols(p, pg.cat || "copii");
      let rows = dataByPart[p.key] || [];
      if (p.period !== "crud") rows = rows.filter((r) => (pg.month ? r.luna === pg.month : true) && (!p.categorie || r.categorie_varsta === pg.cat));
      const title = `Partea ${pg.nr}. ${p.title}${pg.cat ? " (" + pg.cat + ")" : ""}${pg.month ? " — " + LUNI[pg.month - 1] + " " + state.an : " — anul " + state.an}`;
      return { title, cols, rows };
    });
  }
  function finalHeadWord(cols) {
    const hasSG = cols.some((c) => c[3] && c[3].sg), hasG = cols.some((c) => c[3] && c[3].g), rows = [];
    if (hasSG) rows.push(spanRow(cols, (c) => (c[3] && c[3].sg) || null));
    if (hasG || hasSG) rows.push(spanRow(cols, (c) => (c[3] && c[3].g) || null));
    rows.push(cols.map((c) => `<th>${esc(c[1])}</th>`).join(""));
    return rows.map((r) => `<tr>${r}</tr>`).join("");
  }
  function finalHeadPDF(cols) {
    const build = (fn) => { const r = []; let i = 0; while (i < cols.length) { const k = fn(cols[i]); if (k == null) { r.push({ text: "", fillColor: "#eef2f7" }); i++; continue; } let j = i + 1; while (j < cols.length && fn(cols[j]) === k) j++; r.push({ text: k, colSpan: j - i, bold: true, fontSize: 6, fillColor: "#eef2f7" }); for (let x = 1; x < j - i; x++) r.push({}); i = j; } return r; };
    const rows = [], hasSG = cols.some((c) => c[3] && c[3].sg), hasG = cols.some((c) => c[3] && c[3].g);
    if (hasSG) rows.push(build((c) => (c[3] && c[3].sg) || null));
    if (hasG || hasSG) rows.push(build((c) => (c[3] && c[3].g) || null));
    rows.push(cols.map((c) => ({ text: c[1], bold: true, fontSize: 6, fillColor: "#eef2f7" })));
    return rows;
  }
  async function exportFinal(format) {
    const cover = $("fin_cover").checked, c = await getCover();
    c.an = c.an || String(state.an);
    $("fin_status").textContent = "Se generează…"; setBusy(true);
    const dataByPart = {};
    (await Promise.all(PARTS.map(async (p) => {
      let q = sb.from(p.key).select("*"); if (p.period !== "crud") q = q.eq("an", state.an);
      q = p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true });
      const { data } = await q; return [p.key, data || []];
    }))).forEach(([k, v]) => (dataByPart[k] = v));
    setBusy(false);
    const secs = finalSections(dataByPart);
    if (!secs.length && !cover) { $("fin_status").textContent = "Nu ați selectat nicio pagină."; return; }
    if (format === "word") {
      const coverHtml = cover ? `<div style="text-align:center;page-break-after:always"><p>${esc(c.institutie_1)}<br>${esc(c.institutie_2)}</p><h1>${esc(c.titlu)}</h1><h2>${esc(c.biblioteca)}</h2><p>${esc(c.localitate)}</p><p style="margin-top:60px;font-size:20px">${esc(c.an)}</p></div>` : "";
      const body = secs.map((s, i) => {
        const trs = s.rows.map((r) => `<tr>${s.cols.map(([k, l, t]) => `<td>${esc(cellText(r, k, t))}</td>`).join("")}</tr>`).join("");
        return `<div style="${i > 0 || cover ? "page-break-before:always" : ""}"><h3>${esc(s.title)}</h3><table>${finalHeadWord(s.cols)}${trs}</table></div>`;
      }).join("");
      const html = `<html><head><meta charset="utf-8"><style>@page{size:A4 landscape}body{font:10px Segoe UI,sans-serif}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:2px;text-align:center}th{background:#eef2f7}h1,h2,h3{text-align:center}</style></head><body>${coverHtml}${body}</body></html>`;
      download(new Blob(["﻿", html], { type: "application/msword" }), `registru_final_${state.an}.doc`);
    } else {
      const content = [];
      if (cover) content.push({ text: c.institutie_1 + "\n" + c.institutie_2, alignment: "center", margin: [0, 60, 0, 24] }, { text: c.titlu, fontSize: 18, bold: true, alignment: "center" }, { text: c.biblioteca, fontSize: 14, alignment: "center", margin: [0, 6, 0, 6] }, { text: c.localitate, alignment: "center" }, { text: c.an, fontSize: 20, alignment: "center", margin: [0, 60, 0, 0], pageBreak: "after" });
      secs.forEach((s, i) => {
        const head = finalHeadPDF(s.cols), tbl = head.slice();
        s.rows.forEach((r) => tbl.push(s.cols.map(([k, l, t]) => ({ text: cellText(r, k, t), fontSize: 6 }))));
        content.push({ text: s.title, bold: true, fontSize: 10, margin: [0, 8, 0, 4], pageBreak: i > 0 ? "before" : undefined });
        content.push({ table: { headerRows: head.length, body: tbl }, layout: "lightHorizontalLines" });
      });
      window.pdfMake.createPdf({ pageOrientation: state.settings.print_orientation || "landscape", pageSize: "A4", pageMargins: [16, 24, 16, 28], content, defaultStyle: { fontSize: 6 }, footer: (cur, tot) => ({ text: `Pagina ${cur} din ${tot}`, alignment: "right", fontSize: 8, color: "#555", margin: [0, 6, 16, 0] }) }).download(`registru_final_${state.an}.pdf`);
    }
    $("fin_status").textContent = `Gata: ${secs.length} secțiuni compilate.`;
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
      <label class="row" style="margin:10px 0"><input type="checkbox" id="impReplace" style="width:auto;margin-right:8px"><b>Înlocuiește</b> datele existente (restaurare curată — șterge înainte de import)</label>
      <pre id="importLog" style="margin-top:8px;background:#0f172a;color:#cbd5e1;padding:12px;border-radius:8px;max-height:320px;overflow:auto;font-size:12px;white-space:pre-wrap"></pre>
      <p class="status">Fără „Înlocuiește": importul e sigur (nu dublează datele zilnice — actualizează pe cheie). Cu „Înlocuiește": șterge tot și pune datele din fișier.</p></div>`;
    const logEl = $("importLog"), log = (m) => { logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; };
    const run = async (btnId, fileId, fn) => { const f = $(fileId).files[0]; if (!f) { toast("Alegeți un fișier"); return; } const replace = $("impReplace").checked; if (replace && !confirm("Mod înlocuire: datele curente vor fi ȘTERSE și înlocuite cu cele din fișier. Continuați?")) return; logEl.textContent = ""; $(btnId).disabled = true; try { await fn(sb, f, log, { replace }); await loadStaff(); } catch (e) { log("✗ " + e.message); } finally { $(btnId).disabled = false; } };
    $("doSqlite").onclick = () => run("doSqlite", "sqliteFile", window.RegistruImport.migrateSqlite);
    $("doXlsx").onclick = () => run("doXlsx", "xlsxFile", window.RegistruImport.importExcel);
  }

  // ---- Export / print / backup ----------------------------------------------
  function exportCurrent() { const p = state.part; if (!isPart() || !state.rows.length) { toast("Nimic de exportat"); return; } const ws = XLSX.utils.json_to_sheet(state.rows); const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, `Partea ${p.nr}`.slice(0, 31)); XLSX.writeFile(wb, `partea_${p.nr}_${state.an}_${pad2(state.luna)}.xlsx`); }
  function printCurrent() {
    const p = state.part, cols = effCols(), ori = state.settings.print_orientation || "landscape";
    const head = `<tr>${cols.map((c) => `<th>${esc(label(c))}</th>`).join("")}</tr>`;
    const body = state.rows.map((r) => `<tr>${cols.map(([k, l, t]) => `<td>${esc(cellText(r, k, t))}</td>`).join("")}</tr>`).join("");
    const per = p.period === "luna" ? `Anul ${state.an}` : (p.period !== "crud" ? `${LUNI[state.luna - 1]} ${state.an}` : "");
    const w = window.open("", "_blank");
    w.document.write(`<html><head><meta charset="utf-8"><title>Partea ${p.nr}</title><style>@page{size:A4 ${ori}}body{font:11px Segoe UI,sans-serif}h3{margin:0 0 8px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:3px;text-align:center}th{background:#eef2f7}</style></head><body><h3>Partea ${p.nr}. ${esc(p.title)} — ${per}${p.categorie ? " (" + state.cat + ")" : ""}</h3><table>${head}${body}</table><script>window.onload=function(){window.print()}<\/script></body></html>`);
    w.document.close();
  }
  function refreshBackupInfo() { const h = window.RegistruBackup.hoursSinceBackup(), info = $("backupInfo"); info.textContent = h === null ? "fără backup" : h > 24 ? `backup acum ${Math.floor(h / 24)}z` : "backup recent ✔"; }
  // ---- Folder local de siguranță „registru mother" --------------------------
  let localDirty = false;
  function markDirty() { localDirty = true; }
  async function saveLocalFolder(note, request) {
    try {
      const F = window.RegistruLocalFolder; if (!F || !F.supported) return false;
      const h = await F.getFolder(request); if (!h) return false;
      const obj = await window.RegistruBackup.snapshot(sb);
      await F.saveSnapshot(h, obj, window.RegistruBackup.stamp());
      localDirty = false; try { localStorage.setItem("lastLocalFolder", new Date().toISOString()); } catch (e) {}
      if (note) note("Copie salvată în folderul local ✔");
      return true;
    } catch (e) { if (note) note("Folder local: " + e.message); return false; }
  }
  async function restoreFromFolder(replace, put) {
    const F = window.RegistruLocalFolder; if (!F || !F.supported) { toast("Necesită Chrome/Edge"); return; }
    const h = await F.getFolder(true); if (!h) { toast("Folderul local nu e configurat"); return; }
    const obj = await F.readSnapshot(h);
    await window.RegistruImport.restoreJson(sb, obj, put || toast, { replace });
  }
  function openFolderSetup() {
    const F = window.RegistruLocalFolder;
    if (!F || !F.supported) { toast("Salvarea în folder local necesită Chrome sau Edge"); return; }
    $("settings").innerHTML = `<div class="box"><h3>📁 Copie de siguranță pe acest calculator</h3>
      <p style="font-size:13px">Alegeți un loc (recomandat: <b>Desktop</b>). Aplicația creează automat folderul <b>„registru mother"</b> și salvează acolo o copie completă a datelor — ca să nu se piardă nimic, chiar dacă nu merge internetul sau backup-ul cloud.</p>
      <p class="status">Pe alt calculator, alegeți din nou o dată — folderul se creează dacă lipsește.</p>
      <div class="actions"><button class="ghost" id="fs_later">Mai târziu</button><button class="ok" id="fs_pick">Alege locul și creează folderul</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("fs_later").onclick = () => $("settings").classList.add("hidden");
    $("fs_pick").onclick = async () => {
      try { await F.pickFolder(); await saveLocalFolder((m) => toast(m), true); $("settings").classList.add("hidden"); if (state.part === HOME) renderHome(); }
      catch (e) { toast(e.message); }
    };
  }
  async function doBackup() {
    await window.RegistruBackup.runBackup(sb, { note: (m) => ($("backupInfo").textContent = m) });
    await window.RegistruBackup.cloudBackup(sb, (m) => ($("backupInfo").textContent = m));
    await saveLocalFolder((m) => ($("backupInfo").textContent = m), true);
    refreshBackupInfo(); if (state.part === HOME) renderHome();
  }
  async function maybeAutoBackup() {
    await saveLocalFolder(null, false); // copie în folderul local (dacă permisiunea e deja acordată)
    const days = toInt(state.settings.backup_days || "0"); if (!days) return;
    const h = window.RegistruBackup.hoursSinceCloudBackup(); if (h !== null && h < days * 24) return;
    await window.RegistruBackup.cloudBackup(sb, (m) => ($("backupInfo").textContent = m)); // off-device, silent
    refreshBackupInfo();
  }
  async function openCloudRestore() {
    $("settings").innerHTML = `<div class="box"><h3>☁ Backup cloud</h3><p class="status">Se încarcă lista…</p></div>`;
    $("settings").classList.remove("hidden");
    const list = await window.RegistruBackup.listCloudBackups(sb);
    const rows = list.map((f) => `<div style="display:flex;gap:8px;align-items:center;padding:5px 4px;border-bottom:1px solid var(--line)"><span style="flex:1;font-size:13px">${esc(f.name)}</span><button class="ghost cr-dl" data-n="${esc(f.name)}" title="Descarcă pe PC">⬇</button><button class="ghost cr-rs" data-n="${esc(f.name)}">Restaurează</button></div>`).join("") || "<div class='pp-empty'>Nicio copie în cloud.</div>";
    $("settings").innerHTML = `<div class="box"><h3>☁ Backup cloud</h3>
      <label class="row" style="margin:6px 0"><input type="checkbox" id="cr_replace" style="width:auto;margin-right:8px"><b>Înlocuiește</b> datele la restaurare (curat)</label>
      <div style="max-height:260px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 8px">${rows}</div>
      <pre id="restLog" style="margin-top:10px;background:#0f172a;color:#cbd5e1;padding:10px;border-radius:8px;max-height:160px;overflow:auto;font-size:12px;white-space:pre-wrap;display:none"></pre>
      <div class="actions"><button class="ghost" id="cr_close">Închide</button></div></div>`;
    $("cr_close").onclick = () => $("settings").classList.add("hidden");
    $("settings").querySelectorAll(".cr-dl").forEach((b) => (b.onclick = async () => { try { const obj = await window.RegistruBackup.downloadCloud(sb, b.dataset.n); download(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }), b.dataset.n); } catch (e) { toast("Eroare: " + e.message); } }));
    $("settings").querySelectorAll(".cr-rs").forEach((b) => (b.onclick = async () => {
      const replace = $("cr_replace").checked;
      if (!confirm((replace ? "ÎNLOCUIEȘTE toate datele cu " : "Adaugă/actualizează din ") + "„" + b.dataset.n + "”?")) return;
      const log = $("restLog"); log.style.display = "block"; log.textContent = "";
      const put = (m) => { log.textContent += m + "\n"; log.scrollTop = log.scrollHeight; };
      try { const obj = await window.RegistruBackup.downloadCloud(sb, b.dataset.n); await window.RegistruImport.restoreJson(sb, obj, put, { replace }); await loadSettings(); await loadStaff(); } catch (e) { put("✗ " + e.message); }
    }));
  }

  // ---- Etichete + realtime --------------------------------------------------
  async function renameCol(camp, col) {
    const nv = prompt("Etichetă coloană:", state.labels[camp] || col[1]); if (nv == null) return;
    const { error } = await sb.from("etichete_custom").upsert({ parte: state.part.pid, camp, eticheta_default: col[1], eticheta_custom: nv }, { onConflict: "parte,camp" });
    if (error) { toast("Eroare: " + error.message); return; } state.labels[camp] = nv; renderGrid();
  }
  function editingRowId() { const a = document.activeElement; return (a && a.matches && a.matches("#content tbody input")) ? +a.dataset.id : null; }
  let rtReloadTimer = null;
  function rtReload() { clearTimeout(rtReloadTimer); rtReloadTimer = setTimeout(() => { if (isPart() && editingRowId() === null) loadData(); }, 300); }
  function patchRowInputs(row) {
    effCols().forEach(([k]) => { const inp = $("content").querySelector(`tbody input[data-id="${row.id}"][data-col="${k}"]`); if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else if (document.activeElement !== inp) inp.value = row[k] == null ? "" : row[k]; markOOR(inp); } });
    applyRowValidation(row.id);
  }
  function subscribe(table) {
    if (channel) sb.removeChannel(channel);
    channel = sb.channel("rt-" + table).on("postgres_changes", { event: "*", schema: "public", table }, (payload) => {
      if (state.part === STAFF) { loadStaff().then(renderStaff); return; }
      if (!isPart() || state.part.key !== table) return;
      const editId = editingRowId();
      if (payload.eventType === "UPDATE" && payload.new) {
        const nw = payload.new;
        const inScope = (state.part.period === "crud" || (nw.an === state.an && nw.luna === state.luna)) && (!state.part.categorie || nw.categorie_varsta === state.cat);
        if (inScope) {
          const idx = state.rows.findIndex((r) => r.id === nw.id);
          if (idx >= 0) { if (nw.id === editId) return; state.rows[idx] = nw; patchRowInputs(nw); renderFooter(); return; }
        }
      }
      if (editId === null) rtReload(); // INSERT/DELETE sau în afara vizualizării → reîncarcă (debounced) dacă nu se editează
    }).subscribe((st) => { const ok = st === "SUBSCRIBED"; $("live").textContent = ok ? "live" : "offline"; $("live").classList.toggle("live", ok); });
  }

  // ---- Undo (Ctrl+Z) --------------------------------------------------------
  const undoStack = [];
  function pushUndo(e) { undoStack.push(e); if (undoStack.length > 25) undoStack.shift(); }
  async function undo() {
    const e = undoStack.pop(); if (!e) { toast("Nimic de anulat"); return; }
    if (e.key && isPart() && e.key !== state.part.key) { toast("Anulare disponibilă pe partea unde s-a modificat"); undoStack.push(e); return; }
    if (e.kind === "add") { await sb.from(e.key).delete().eq("id", e.id); await loadData(); toast("Anulat: adăugare"); return; }
    if (e.kind === "del") { const o = {}; Object.keys(e.row).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = e.row[k]; }); await sb.from(e.key).insert(o); await loadData(); toast("Anulat: ștergere"); return; }
    const row = state.rows.find((r) => r.id === e.id); if (!row) { toast("Rândul nu mai există"); return; }
    row[e.col] = e.old;
    const affected = deriveRow(state.part, row, e.col);
    const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
    const { error } = await sb.from(state.part.key).update(payload).eq("id", e.id);
    if (error) { toast("Eroare: " + error.message); return; }
    affected.forEach((k) => { const inp = $("content").querySelector(`tbody input[data-id="${e.id}"][data-col="${k}"]`); if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else inp.value = row[k] == null ? "" : row[k]; markOOR(inp); } });
    applyRowValidation(e.id); renderFooter(); toast("Anulat (Ctrl+Z)");
  }

  // ---- Duplică rând (events / Ctrl+D) ---------------------------------------
  async function duplicateRow() {
    if (state.part.period !== "lista") { toast("Duplicarea e disponibilă pe părțile cu evenimente"); return; }
    const el = document.activeElement; let src;
    if (el && el.matches && el.matches("#content tbody input")) src = state.rows.find((r) => r.id === +el.dataset.id);
    if (!src) src = state.rows[state.rows.length - 1];
    if (!src) { toast("Niciun rând de duplicat"); return; }
    const o = {}; Object.keys(src).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = src[k]; });
    const { error } = await sb.from(state.part.key).insert(o); if (error) { toast("Eroare: " + error.message); return; }
    toast("Rând duplicat"); await loadData();
  }

  // ---- Găsește în tabel (Ctrl+F) --------------------------------------------
  let findMatches = [], findIdx = -1;
  function openFind() {
    if (!isPart()) return;
    let bar = $("findBar");
    if (!bar) {
      bar = document.createElement("div"); bar.id = "findBar"; bar.className = "findbar";
      bar.innerHTML = `<input id="findInp" placeholder="Găsește în tabel…"><button id="findPrev" class="ghost">◀</button><button id="findNext" class="ghost">▶</button><span id="findCount" class="status"></span><button id="findClose" class="ghost">✕</button>`;
      document.body.appendChild(bar);
      $("findInp").addEventListener("input", () => runFind($("findInp").value));
      $("findInp").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); findStep(e.shiftKey ? -1 : 1); } else if (e.key === "Escape") closeFind(); });
      $("findNext").onclick = () => findStep(1); $("findPrev").onclick = () => findStep(-1); $("findClose").onclick = closeFind;
    }
    bar.style.display = "flex"; $("findInp").focus(); $("findInp").select();
  }
  function runFind(q) {
    findMatches = []; findIdx = -1;
    if (q) { const ql = q.toLowerCase(); $("content").querySelectorAll("tbody input").forEach((inp) => { if (inp.type !== "checkbox" && String(inp.value || "").toLowerCase().includes(ql)) findMatches.push(inp); }); }
    $("findCount").textContent = findMatches.length ? `${findMatches.length} rezultate` : "0";
    if (findMatches.length) findStep(1);
  }
  function findStep(d) {
    if (!findMatches.length) return;
    findIdx = (findIdx + d + findMatches.length) % findMatches.length;
    const inp = findMatches[findIdx]; inp.scrollIntoView({ block: "center", inline: "center" }); inp.focus(); if (inp.select) inp.select();
    $("findCount").textContent = `${findIdx + 1}/${findMatches.length}`;
  }
  function closeFind() { const b = $("findBar"); if (b) b.style.display = "none"; }

  // ---- Legături -------------------------------------------------------------
  document.addEventListener("keydown", (e) => {
    if ($("app").classList.contains("hidden")) return;
    if (e.key === "F1") { e.preventDefault(); openHelp(); return; }
    if (!(e.ctrlKey || e.metaKey)) return;
    const k = e.key.toLowerCase();
    if (k === "f") { e.preventDefault(); openFind(); }
    else if (k === "z") { e.preventDefault(); undo(); }
    else if (k === "s") { e.preventDefault(); toast("Salvat automat ✔"); }
    else if (k === "e") { if (isPart()) { e.preventDefault(); exportCurrent(); } }
    else if (k === "c") { const el = document.activeElement; if (el && el.matches && el.matches("#content tbody input") && el.type !== "checkbox" && el.selectionStart === el.selectionEnd && navigator.clipboard) navigator.clipboard.writeText(el.value || "").catch(() => {}); }
    else if (k === "d") { if (isPart() && state.part.period === "lista") { e.preventDefault(); duplicateRow(); } }
    else if (e.shiftKey && k === "m") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista")) { e.preventDefault(); copyLastMonth(); } }
    else if (e.key === "ArrowLeft") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista") && state.luna > 1) { e.preventDefault(); state.luna--; loadData(); updateChrome(); } }
    else if (e.key === "ArrowRight") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista") && state.luna < 12) { e.preventDefault(); state.luna++; loadData(); updateChrome(); } }
  });
  $("loginBtn").onclick = login;
  $("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
  $("settingsBtn").onclick = openSettings;
  $("menuBtn").onclick = () => { const a = document.querySelector("aside"); if (a) a.classList.toggle("open"); };
  document.addEventListener("paste", handlePaste);
  setInterval(() => { if (localDirty) saveLocalFolder(null, false); }, 5 * 60 * 1000);
  document.addEventListener("visibilitychange", () => { if (document.hidden && localDirty) saveLocalFolder(null, false); });
  $("logout").onclick = async () => { await sb.auth.signOut(); location.reload(); };
  sb.auth.getSession().then(({ data }) => { if (data.session) onLoggedIn(); });
})();
