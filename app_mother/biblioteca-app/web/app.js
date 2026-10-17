// ============================================================================
// Motorul aplicației web — dashboard, taburi lună/categorie, generare automată
// zile lucrătoare, copiere lună, totaluri, sincronizare, validări (range_config),
// etichete custom, presets, export, backup automat, setări.
// ============================================================================
(function () {
  const $ = (id) => document.getElementById(id);
  const PARTS = window.REGISTRU_PARTS, MAX5 = window.REGISTRU_MAX5, partCols = window.partCols;
  const HOME = { key: "__home" }, STAFF = { key: "__staff" }, IMPORT = { key: "__import" }, FINAL = { key: "__final" }, HISTORY = { key: "__history" };
  function download(blob, name) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); }
  const LUNI = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"];

  if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) $("authErr").textContent = "Lipsește config.js.";
  const sb = window.supabase.createClient(window.SUPABASE_URL || "", window.SUPABASE_ANON_KEY || "");

  const NOW = new Date();
  const state = { part: null, an: NOW.getFullYear(), luna: NOW.getMonth() + 1, cat: "copii", rows: [], staff: [], prior: null,
    aux: {}, presets: {}, labels: {}, ranges: {}, settings: {}, badges: {} };
  let channel = null;

  // Coada de salvare: orice modificare e întâi păstrată pe calculator (localStorage),
  // apoi trimisă; iese din coadă doar după confirmarea serverului. Vezi outbox.js.
  const LS = (() => { try { localStorage.setItem("__t", "1"); localStorage.removeItem("__t"); return localStorage; } catch (e) { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } }; } })();
  const OB = window.RegistruOutbox.create(LS, "registruOutbox_v1");

  const P3_DIN = ["consultare_pe_loc", "imprumut_pe_loc", "imprumut_la_domiciliu", "imprumut_inter_bibliotecar"];
  const P2_INTR = ["imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii"];

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cellText = (r, k, t) => t === "bool" ? (r[k] ? "✓" : "") : t === "monthlabel" ? (LUNI[(+r[k] || 1) - 1] || "") : (r[k] == null ? "" : String(r[k]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const toInt = (v) => Math.max(0, parseInt(v, 10) || 0);
  const ddmm = (d, m) => `${pad2(d)}.${pad2(m)}`;
  let toastTimer = null;
  function toast(m, ms) { const t = $("toast"); t.textContent = m; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), ms || 1500); }
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
    // Doar conturile aprobate (tabelul utilizatori_permisi). Înainte de migrarea 001 funcția
    // nu există → eroare → nu blocăm pe nimeni.
    const acc = await sb.rpc("is_allowed");
    if (!acc.error && acc.data === false) {
      loggingOut = true; await sb.auth.signOut(); loggingOut = false;
      $("authErr").textContent = "Acest cont nu are acces la registru. Cereți administratorului să vă adauge.";
      return;
    }
    $("auth").classList.add("hidden"); $("app").classList.remove("hidden");
    $("who").textContent = data.user.email; $("who2").textContent = data.user.email;
    lastEmail = data.user.email; needLogin = false;
    // Modificări rămase netrimise de data trecută (filă închisă, fără internet…) → le trimitem acum.
    const left = OB.size();
    if (left) { await flushNow(); if (!OB.size()) toast(`✔ ${left} modificări rămase din sesiunea trecută au fost salvate`, 6000); }
    updateSaveState();
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
  const special = () => state.part === STAFF || state.part === IMPORT || state.part === HOME || state.part === FINAL || state.part === HISTORY;

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
      <label>Backup automat — la câte zile (0 = dezactivat)</label><input id="st_bk" type="number" min="0" value="${esc(s.backup_days || "7")}">
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
    const rows = [["Ctrl+F", "Găsește în tabel"], ["Ctrl+Z", "Anulează ultima editare"], ["Ctrl+C / Ctrl+V", "Copiază / lipește (din Excel)"], ["Ctrl+D", "Duplică rândul (părți evenimente)"], ["Ctrl+Shift+M", "Copiază luna trecută"], ["Ctrl+← / Ctrl+→", "Luna anterioară / următoare"], ["↑ / ↓", "Rândul de sus / de jos (și alegere din listă)"], ["Ctrl+S", "Trimite acum modificările"], ["Ctrl+E", "Export Excel"], ["Enter", "Celula de mai jos"], ["Tab", "Celula următoare"], ["F1", "Acest ajutor"]];
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
      `<button class="nav" data-key="__history">🕘 Istoric modificări</button>` +
      `<button class="nav" data-key="__import">⬆ Import / Migrare</button>`;
    $("nav").querySelectorAll("button.nav").forEach((b) => (b.onclick = () => selectPart(b.dataset.key)));
    markActive(state.part ? state.part.key : "__home");
  }
  function markActive(key) { document.querySelectorAll("#nav button.nav").forEach((b) => b.classList.toggle("active", b.dataset.key === key)); }

  function selectPart(key) {
    commitActive();
    if (channel) { sb.removeChannel(channel); channel = null; }
    const aside = document.querySelector("aside"); if (aside) aside.classList.remove("open");
    undoStack.length = 0;
    if (key === "__home") { state.part = HOME; updateChrome(); renderHome(); return; }
    if (key === "__final") { state.part = FINAL; updateChrome(); renderFinal(); return; }
    if (key === "__staff") { state.part = STAFF; updateChrome(); renderStaff(); subscribe("personal"); return; }
    if (key === "__import") { state.part = IMPORT; updateChrome(); renderImport(); return; }
    if (key === "__history") { state.part = HISTORY; state.hist = null; updateChrome(); renderHistory(false); return; }
    state.part = PARTS.find((p) => p.key === key);
    if (!state.part.categorie) state.cat = "copii";
    updateChrome(); loadData(); subscribe(state.part.key);
  }

  function updateChrome() {
    const p = state.part, sp = special();
    markActive(p.key);
    $("hbadge").textContent = p === HOME ? "🏠" : p === FINAL ? "📗" : p === STAFF ? "👤" : p === IMPORT ? "⬆" : p === HISTORY ? "🕘" : p.nr;
    $("title").textContent = p === HOME ? "Acasă" : p === FINAL ? "Registru final" : p === STAFF ? "Personal (responsabili)" : p === IMPORT ? "Import / Migrare date" : p === HISTORY ? "Istoric modificări" : `Partea ${p.nr}. ${p.title}`;
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
  const exCtx = () => ({ an: state.an, luna: state.luna, cat: state.cat, cols: effCols(), label, totals: totalsRows(), orientation: state.settings.print_orientation || "landscape", toast });

  // ---- Încărcare + meta -----------------------------------------------------
  // Fiecare încărcare primește un număr; un răspuns întârziat al unei încărcări
  // mai vechi (ex. clic rapid Ianuarie → Februarie) e ignorat, ca să nu apară
  // rândurile altei luni sub tab-ul curent.
  let loadSeq = 0;
  async function loadData(fromScaffold) {
    commitActive();
    const p = state.part, seq = ++loadSeq;
    const stale = () => seq !== loadSeq || state.part !== p;
    setBusy(true);
    try {
      let q = sb.from(p.key).select("*");
      if (p.period === "luna") q = q.eq("an", state.an); // toate cele 12 luni
      else if (p.period !== "crud") q = q.eq("an", state.an).eq("luna", state.luna);
      if (p.categorie) q = q.eq("categorie_varsta", state.cat);
      q = p.orderById ? q.order("id", { ascending: true }) : (p.period === "luna" ? q.order("luna", { ascending: true }) : (p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true })));
      const { data, error } = await q;
      if (stale()) return;
      if (error) {
        state.rows = [];
        $("content").innerHTML = `<div class="card" style="max-width:560px"><h3>⚠ Datele nu s-au putut încărca</h3><p class="status">${esc(error.message)}</p><p style="font-size:13px">Verificați internetul. Modificările dvs. nesalvate rămân păstrate pe calculator.</p><button id="retryLoad">↻ Încearcă din nou</button></div>`;
        $("retryLoad").onclick = () => loadData(); return;
      }
      // Peste datele serverului se pun modificările încă netrimise (ca să le vedeți, chiar și offline).
      state.rows = (data || []).map((r) => Object.assign(r, OB.pending(p.key, r.id) || {}));
      // Auto-schelet (ca în desktop): la deschiderea unei luni goale, creează
      // automat zilele lucrătoare (părți zilnice) sau rândul lunii (parte lunară).
      if (!fromScaffold && !state.rows.length && (p.period === "zi" || p.period === "luna")) {
        const scaffold = [];
        if (p.period === "luna") { for (let m = 1; m <= 12; m++) { const o = { an: state.an, luna: m }; if (p.categorie) o.categorie_varsta = state.cat; scaffold.push(o); } }
        else { const excl = await getExcluded(state.an), exSet = new Set(excl[state.luna] || []); weekdays(state.an, state.luna).filter((d) => !exSet.has(d)).forEach((d) => { const o = { an: state.an, luna: state.luna, [p.dateField]: d }; if (p.categorie) o.categorie_varsta = state.cat; scaffold.push(o); }); }
        // (dacă alt calculator a creat zilele în același timp, inserarea dă eroare — reîncărcăm oricum)
        if (scaffold.length) { await sb.from(p.key).insert(scaffold); if (stale()) return; return loadData(true); }
      }
      await syncIn(p); await loadMeta(p);
      if (stale()) return;
      let prior = null;
      if (p.cumulative) {
        let pq = sb.from(p.key).select("*").eq("an", state.an).lt("luna", state.luna);
        if (p.categorie) pq = pq.eq("categorie_varsta", state.cat);
        const { data: pd } = await pq; prior = computeAcc(effCols(), pd || []);
        if (stale()) return;
      }
      state.prior = prior;
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
      // type="text" (nu "number"): la „number" săgețile ↑/↓ și rotița mouse-ului modifică valoarea pe ascuns
      return `<input class="num${o.ro ? " calc" : ""}${oor ? " oor" : ""}" type="text" inputmode="numeric" autocomplete="off" ${o.ro ? "readonly" : `data-min="${rg.min}" data-max="${rg.max}"`} value="${esc(v == null ? 0 : v)}" ${attr}>`;
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
  // ↑/↓ aleg din listă, Enter pune valoarea aleasă. Întoarce true dacă tasta a fost folosită.
  function presetKey(inp, e) {
    if (!presetPop || presetPop.style.display === "none") return false;
    const items = [...presetPop.querySelectorAll(".pp-item")]; if (!items.length) return false;
    let i = items.findIndex((x) => x.classList.contains("sel"));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (i < 0 && e.key === "ArrowUp") { closePresetPopup(); return false; }
      i = Math.max(0, Math.min(items.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)));
      items.forEach((x, j) => x.classList.toggle("sel", j === i)); items[i].scrollIntoView({ block: "nearest" });
      return true;
    }
    if (e.key === "Enter" && i >= 0) {
      e.preventDefault(); inp.value = items[i].textContent; inp.dispatchEvent(new Event("change", { bubbles: true })); closePresetPopup(); moveDown(inp);
      return true;
    }
    return false;
  }

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
      inp.addEventListener("change", () => commitCell(inp, true));
      inp.addEventListener("focus", () => { const r = state.rows.find((x) => x.id === +inp.dataset.id); if (r) focusOld.set(inp, r[inp.dataset.col]); });
      const t = inp.dataset.type, live = LIVE_TYPES.has(t) && !inp.readOnly;
      if (t === "text" || t === "txt" || t === "staff") {
        inp.addEventListener("focus", () => openPresetPopup(inp));
        inp.addEventListener("input", () => { inp.classList.add("dirty"); if (live) commitCell(inp, false); openPresetPopup(inp); });
        inp.addEventListener("keydown", (e) => {
          if (presetKey(inp, e)) return; // ↑/↓/Enter în lista deschisă
          if (e.key === "Enter" || e.key === "ArrowDown") { e.preventDefault(); closePresetPopup(); moveDown(inp); }
          else if (e.key === "ArrowUp") { e.preventDefault(); closePresetPopup(); moveUp(inp); }
          else if (e.key === "Escape") closePresetPopup();
        });
        inp.addEventListener("blur", () => setTimeout(closePresetPopup, 160));
      } else if (inp.type !== "checkbox" && !inp.readOnly) {
        inp.addEventListener("input", () => { inp.classList.add("dirty"); if (live) commitCell(inp, false); });
        inp.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === "ArrowDown") { e.preventDefault(); moveDown(inp); }
          else if (e.key === "ArrowUp") { e.preventDefault(); moveUp(inp); }
        });
      }
    });
    $("content").querySelectorAll(".del").forEach((b) => (b.onclick = () => deleteRow(+b.dataset.id)));
    state.rows.forEach((r) => applyRowValidation(r.id));
    renderFooter();
  }
  function moveDown(inp) { moveRow(inp, 1); }
  function moveUp(inp) { moveRow(inp, -1); }
  function moveRow(inp, d) {
    const col = inp.dataset.col, all = [...$("content").querySelectorAll(`tbody input[data-col="${col}"]`)];
    const i = all.indexOf(inp), next = all[i + d];
    if (next) { next.focus(); if (next.select && next.type !== "checkbox") next.select(); }
    else if (d > 0) inp.blur();
  }
  // Pune cursorul pe prima celulă editabilă a unui rând (după + Rând / Duplică).
  function focusRow(id) {
    const inp = [...$("content").querySelectorAll(`tbody input[data-id="${id}"]`)].find((x) => !x.readOnly && x.type !== "checkbox");
    if (inp) { inp.scrollIntoView({ block: "center" }); inp.focus(); if (inp.select) inp.select(); }
  }

  const computeAcc = (cols, rows) => window.RegistruLogic.sumCols(cols, rows);
  function footerRow(label2, acc, cols, cls) {
    return "<tr>" + cols.map((c, i) => i === 0 ? `<td class="totlbl">${esc(label2)}</td>` : `<td class="${cls}">${acc[c[0]] == null ? "" : acc[c[0]]}</td>`).join("") + `<td class="${cls}"></td></tr>`;
  }
  // Rândurile de total ale tabelului curent: [[eticheta, {coloană: valoare}], …] — pe ecran și în exporturi.
  function totalsRows() {
    const cols = effCols(), acc = computeAcc(cols, state.rows), out = [["Total", acc]];
    if (state.part.cumulative && state.prior) {
      const cum = {}; cols.forEach(([k, l, t, o]) => { if (t === "int" || (t === "bool" && o && o.ct)) cum[k] = (state.prior[k] || 0) + (acc[k] || 0); });
      out.push(["Total de la început", cum]);
    }
    return out;
  }
  function renderFooter() {
    const cols = effCols(), html = totalsRows().map(([l, acc], i) => footerRow(l, acc, cols, i ? "cumrow" : "totalrow")).join("");
    const f = $("gridFoot"); if (f) f.innerHTML = html;
  }

  // ---- Reguli intra-rând ----------------------------------------------------
  // prev = valoarea câmpului înainte de modificare (doar la editarea unei celule).
  function deriveRow(part, row, col, prev) {
    const cols = effCols(), affected = new Set([col]);
    if (part.key === "evidenta_utilizatori" && ["elevi", "copii_pana_16", "prescolari"].indexOf(col) >= 0) {
      const r2 = window.RegistruLogic.copiiSplit(row.prescolari, row.elevi, row.copii_pana_16, col);
      ["prescolari", "elevi", "copii_pana_16"].forEach((k) => { if ((+row[k] || 0) !== r2[k]) { row[k] = r2[k]; affected.add(k); } });
    }
    if (part.split) {
      const sk = part.split, t = +row[sk.total] || 0;
      if (sk.bidir) {
        // Editezi un sex → celălalt = Total − acela (doar la editarea Fete/Băieți, nu a Totalului)
        if (col === sk.f || col === sk.m) {
          const r = window.RegistruLogic.pairSplit(t, +row[sk.f] || 0, +row[sk.m] || 0, col === sk.m ? "m" : "f");
          if ((+row[sk.f] || 0) !== r.f) { row[sk.f] = r.f; affected.add(sk.f); }
          if ((+row[sk.m] || 0) !== r.m) { row[sk.m] = r.m; affected.add(sk.m); }
        }
      } else if (col === sk.total && t > 0) {
        // Împărțirea automată (jumătate-jumătate) doar dacă Masculin/Feminin n-au fost scrise de mână:
        // sunt goale sau sunt exact împărțirea automată a totalului de dinainte.
        const f0 = +row[sk.f] || 0, m0 = +row[sk.m] || 0, g0 = window.RegistruLogic.genderSplit(+prev || 0);
        if (prev === undefined || (f0 === 0 && m0 === 0) || (f0 === g0.f && m0 === g0.m)) {
          const g = window.RegistruLogic.genderSplit(t); row[sk.f] = g.f; row[sk.m] = g.m; affected.add(sk.f); affected.add(sk.m);
        }
      }
    }
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
    // Partea IX, tab Copii — „Elevi" = Total − Preșcolari (restul copiilor; calculat automat, read-only)
    if (part.key === "instruiri" && row.categorie_varsta === "copii") {
      const elevi = window.RegistruLogic.pairSplit(row.total_participanti, row.prescolari, row.elevi, "f").m;
      if ((+row.elevi || 0) !== elevi) { row.elevi = elevi; affected.add("elevi"); }
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
    if (part.key === "instruiri" && row.categorie_varsta === "copii" && (+row.prescolari || 0) > (+row.total_participanti || 0)) bad.add("prescolari");
    return bad;
  }
  function applyRowValidation(id) {
    const row = state.rows.find((r) => r.id === id); if (!row) return;
    const bad = validateRow(state.part, row);
    effCols().forEach(([k]) => { const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`); if (inp) inp.classList.toggle("badrel", bad.has(k)); });
  }

  function markOOR(inp) { const mx = inp.dataset.max; if (mx == null) return; const v = +inp.value || 0; inp.classList.toggle("oor", v > +mx || v < +(inp.dataset.min || 0)); }

  // ---- Salvare sigură -------------------------------------------------------
  // Fluxul unei modificări: celulă → rândul din memorie → coada OB (localStorage,
  // sincron) → trimitere la Supabase → confirmare (≥1 rând modificat) → scoasă
  // din coadă. Nimic nu se pierde dacă fila se închide, internetul cade sau
  // sesiunea expiră: coada se retrimite automat (și la următoarea pornire).
  let lastEmail = "", needLogin = false, loggingOut = false, flushTimer = null, retryDelay = 0, authSession = null;

  function updateSaveState(mode) {
    const el = $("saveState"); if (!el) return;
    const n = OB.size();
    let cls, txt;
    if (!n) { cls = "save-ok"; txt = "✔ Toate salvate"; }
    else if (needLogin) { cls = "save-err"; txt = `🔒 ${n} nesalvate — reconectați-vă`; }
    else if (mode === "saving") { cls = "save-saving"; txt = `⏳ Se salvează… (${n})`; }
    else if (!navigator.onLine || retryDelay) { cls = "save-err"; txt = `⚠ ${n} în așteptare — păstrate pe calculator`; }
    else { cls = "save-dirty"; txt = `• ${n} de salvat`; }
    el.className = "pill " + cls; el.textContent = txt;
    el.title = n ? "Modificările sunt păstrate pe acest calculator până ajung în registru. Click = încearcă acum." : "Toate modificările sunt în registru.";
  }
  function queueSave(table, id, fields) {
    if (!OB.put(table, id, fields)) toast("⚠ Browserul nu permite salvarea locală — nu închideți fila până apare „Toate salvate”", 6000);
    markDirty(); updateSaveState(); scheduleFlush(500);
  }
  function scheduleFlush(ms) { clearTimeout(flushTimer); flushTimer = setTimeout(flushNow, ms); }

  // Trimite un rând; răspunsul spune cozii ce să facă (vezi RegistruOutbox.classify).
  async function sendRow(table, id, fields) {
    let res;
    try { res = await sb.from(table).update(fields).eq("id", id).select("id"); } catch (e) { return "retry"; }
    const c = window.RegistruOutbox.classify(res.error, res.status, (res.data || []).length);
    if (c !== "none") return c;
    // 0 rânduri modificate, fără eroare: fie sesiunea s-a pierdut (fără login baza
    // nu arată nimic), fie rândul a fost șters între timp de altcineva.
    const { data } = await sb.auth.getSession();
    if (!data || !data.session) return "auth";
    const chk = await sb.from(table).select("id").eq("id", id);
    if (chk.error) return "retry";
    return chk.data && chk.data.length ? "retry" : { drop: "rândul a fost șters între timp" };
  }
  async function flushNow(refreshed) {
    clearTimeout(flushTimer);
    if (!OB.size() || needLogin) { updateSaveState(); return; }
    updateSaveState("saving");
    const r = await OB.flush(sendRow);
    const why = (m) => /duplicate key|unique/i.test(m) ? "există deja un rând cu aceeași dată" : /invalid input|out of range/i.test(m) ? "valoare nevalidă" : m;
    r.dropped.forEach((d) => toast(`⚠ O modificare nu a putut fi salvată: ${why(d.reason)}. S-a revenit la valoarea din registru.`, 8000));
    if (r.dropped.length && isPart() && editingRowId() === null) loadData();
    if (r.stopped === "auth") {
      const { data, error } = await sb.auth.refreshSession().catch((e) => ({ error: e }));
      if (!refreshed && !error && data && data.session) return flushNow(true);
      retryDelay = 0; showRelogin(); return;
    }
    if (r.stopped === "retry") { retryDelay = Math.min(30000, (retryDelay || 1000) * 2); scheduleFlush(retryDelay); }
    else retryDelay = 0;
    updateSaveState();
    if (OB.size() && !r.stopped) scheduleFlush(300); // s-a mai editat în timpul trimiterii
  }

  // Sesiune pierdută → fereastră de reconectare peste aplicație; modificările rămân în coadă.
  function showRelogin() {
    needLogin = true; updateSaveState();
    let m = $("relogin");
    if (!m) {
      m = document.createElement("div"); m.id = "relogin"; m.className = "modal"; m.style.zIndex = "60";
      m.innerHTML = `<div class="box" style="max-width:420px"><h3>🔒 Reconectare necesară</h3>
        <p style="font-size:13px">Sesiunea a expirat. Modificările dvs. <b>nu s-au pierdut</b> — <span id="rl_n"></span> sunt păstrate pe acest calculator și se trimit imediat după reconectare.</p>
        <label>Email</label><input id="rl_email" type="email" autocomplete="username">
        <label>Parolă</label><input id="rl_pass" type="password" autocomplete="current-password">
        <div class="err" id="rl_err"></div>
        <div class="actions"><button class="ok" id="rl_go">Reconectare</button></div></div>`;
      document.body.appendChild(m);
      const go = async () => {
        $("rl_err").textContent = ""; $("rl_go").disabled = true;
        const { error } = await sb.auth.signInWithPassword({ email: $("rl_email").value.trim(), password: $("rl_pass").value });
        $("rl_go").disabled = false;
        if (error) { $("rl_err").textContent = error.message; return; }
        hideRelogin(); await flushNow(); if (isPart() && editingRowId() === null) loadData();
      };
      $("rl_go").onclick = go;
      $("rl_pass").addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    }
    $("rl_n").textContent = `${OB.size()} modificări`;
    if (!$("rl_email").value) $("rl_email").value = lastEmail;
    $("rl_pass").value = ""; m.classList.remove("hidden");
    setTimeout(() => $(lastEmail ? "rl_pass" : "rl_email").focus(), 50);
  }
  function hideRelogin() { needLogin = false; const m = $("relogin"); if (m) m.classList.add("hidden"); updateSaveState(); }

  // Trimitere „de ultimă clipă" la închiderea filei (fetch keepalive). Nu scoate
  // nimic din coadă — confirmarea vine abia la următoarea pornire (retrimitere sigură).
  function sendBeacons() {
    const token = authSession && authSession.access_token; if (!token || !window.fetch) return;
    for (const it of OB.list().slice(0, 40)) {
      try {
        fetch(`${window.SUPABASE_URL}/rest/v1/${it.table}?id=eq.${encodeURIComponent(it.id)}`, {
          method: "PATCH", keepalive: true, body: JSON.stringify(it.fields),
          headers: { apikey: window.SUPABASE_ANON_KEY, Authorization: "Bearer " + token, "Content-Type": "application/json", Prefer: "return=minimal" },
        }).catch(() => {});
      } catch (e) { /* best effort */ }
    }
  }

  // ---- Editarea celulelor ---------------------------------------------------
  const focusOld = new WeakMap(); // valoarea celulei la intrarea în ea (pt. Ctrl+Z și validare strictă)
  const LIVE_TYPES = new Set(["int", "text", "txt", "staff"]); // se salvează în timp ce scrieți (data: la ieșire)
  function readInput(el, type) {
    if (type === "int") return toInt(el.value);
    if (type === "bool") return el.checked;
    return el.value === "" ? (el.dataset.req ? "" : null) : el.value;
  }
  function refreshRowUI(id, keys, skipCol) {
    const row = state.rows.find((r) => r.id === id); if (!row) return;
    keys.forEach((k) => { if (k === skipCol) return; const inp = $("content").querySelector(`tbody input[data-id="${id}"][data-col="${k}"]`); if (inp) { if (inp.type === "checkbox") inp.checked = !!row[k]; else inp.value = row[k] == null ? "" : row[k]; markOOR(inp); } });
    applyRowValidation(id); renderFooter();
  }
  // Verifică o dată scrisă într-o celulă: format ZZ.LL, zi existentă și — pentru data rândului
  // pe părțile zilnice / cu evenimente — luna afișată. Întoarce { value } sau { error: mesaj }.
  function checkDate(part, col, text, required) {
    const r = window.RegistruLogic.normDate(text, state.an, state.luna);
    if (r.error) return { error: `Data „${text}" nu e validă — scrieți ziua și luna, ex. ${ddmm(5, state.luna)}` };
    if (!r.value) return required ? { error: "Data este obligatorie" } : r;
    if (col === part.dateField && (part.period === "zi" || part.period === "lista") && r.month !== state.luna)
      return { error: `Data trebuie să fie în luna afișată (${LUNI[state.luna - 1]}). Pentru altă lună, alegeți tab-ul lunii.` };
    return r;
  }
  // final=false: la fiecare tastă (salvare din mers); final=true: la ieșirea din celulă.
  function commitCell(el, final) {
    if (!el.isConnected && !final) return;
    const id = +el.dataset.id, col = el.dataset.col, type = el.dataset.type, part = state.part;
    const row = state.rows.find((r) => r.id === id); if (!row || !isPart()) return;
    if (!focusOld.has(el)) focusOld.set(el, row[col]); // fără eveniment focus (ex. fereastră inactivă)
    const before = focusOld.get(el);
    if (type === "date") { // datele se potrivesc între părți după textul exact „ZZ.LL"
      const chk = checkDate(part, col, el.value, !!el.dataset.req);
      if (chk.error) {
        el.value = before == null ? "" : before; el.classList.remove("dirty");
        toast(chk.error, 6000); return;
      }
      el.value = chk.value;
    }
    const prev = row[col], nv = readInput(el, type);
    if (nv !== prev) {
      row[col] = nv;
      const affected = deriveRow(part, row, col, prev);
      if (state.settings.strict_validation === "1") {
        const rg = type === "int" ? colRange(part, col) : null;
        const oor = rg && (nv > rg.max || nv < rg.min);
        if (oor || validateRow(part, row).has(col)) {
          if (!final) { row[col] = prev; deriveRow(part, row, col); markOOR(el); return; } // în timp ce scrieți: nu salvăm valoarea invalidă
          row[col] = before; const back = deriveRow(part, row, col); back.add(col);
          if (type === "bool") el.checked = !!before; else el.value = before == null ? "" : before;
          const payload = {}; back.forEach((k) => (payload[k] = row[k])); queueSave(part.key, id, payload);
          toast(oor ? `Valoare în afara limitelor (${rg.min}–${rg.max})` : "Valoare respinsă (validare strictă)");
          el.classList.remove("dirty"); markOOR(el); refreshRowUI(id, back, col); return;
        }
      }
      const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
      queueSave(part.key, id, payload);
      markOOR(el); refreshRowUI(id, affected, col);
    }
    if (!final) return;
    el.classList.remove("dirty");
    if (type === "int") el.value = row[col] == null ? 0 : row[col];
    if (before === row[col]) return;
    focusOld.set(el, row[col]);
    pushUndo({ kind: "cell", key: part.key, id, col, type, old: before });
    // sincronizare inversă II → IX/XI
    const cdef = effCols().find((c) => c[0] === col);
    if (part.key === "evidenta_utilizatori_copii_adulti" && cdef && cdef[3] && cdef[3].rev) reverseSync(col, row.data, +row[col] || 0);
    if ((type === "text" || type === "txt" || type === "staff") && row[col]) {
      const arr = state.presets[col] || (state.presets[col] = []);
      if (!arr.includes(row[col])) { arr.push(row[col]); sb.from("text_presets").upsert({ parte: part.pid, camp: col, valoare: row[col] }, { onConflict: "parte,camp,valoare", ignoreDuplicates: true }).then(() => {}, () => {}); }
    }
  }
  // Salvează celula în care se află cursorul (înainte de schimbarea lunii/părții, închiderea filei…).
  function commitActive() {
    const a = document.activeElement;
    if (a && a.matches && a.matches("#content tbody input") && !a.readOnly) commitCell(a, true);
  }

  // Modificări în masă (lipire, auto valori, copiere lună) → prin coadă + un singur pas de Ctrl+Z.
  function batchUpdate(label, changes) { // changes: [{ row, fields }]
    const key = state.part.key, undoRows = [];
    for (const { row, fields } of changes) {
      const old = {}; Object.keys(fields).forEach((k) => (old[k] = row[k]));
      Object.assign(row, fields); undoRows.push({ id: row.id, old });
      queueSave(key, row.id, fields);
    }
    if (undoRows.length) pushUndo({ kind: "batch", key, rows: undoRows, label });
    renderGrid();
  }

  // ---- Lipire din Excel (Ctrl+V) --------------------------------------------
  function handlePaste(e) {
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
    const changes = []; let badDates = 0;
    for (let dr = 0; dr < lines.length; dr++) {
      const ri = startIdx + dr; if (ri >= state.rows.length) break;
      const row = state.rows[ri], work = Object.assign({}, row), cells = lines[dr].split("\t"), affected = new Set();
      for (let dc = 0; dc < cells.length; dc++) {
        const ci = startCol + dc; if (ci >= cols.length) break;
        const [k, l, t, o = {}] = cols[ci]; if (o.ro || t === "monthlabel") continue;
        const raw = cells[dc].trim();
        if (t === "date") { const chk = checkDate(state.part, k, raw, !!o.req); if (chk.error) { badDates++; continue; } work[k] = chk.value; }
        else if (t === "int") work[k] = Math.max(0, parseInt(raw.replace(/[^\d-]/g, ""), 10) || 0);
        else if (t === "bool") work[k] = /^(1|true|da|x|✓|adevărat)$/i.test(raw);
        else work[k] = raw === "" ? (o.req ? "" : null) : raw;
        deriveRow(state.part, work, k).forEach((x) => affected.add(x)); affected.add(k);
      }
      if (affected.size) { const fields = {}; affected.forEach((k) => (fields[k] = work[k])); changes.push({ row, fields }); }
    }
    batchUpdate("lipire din Excel", changes);
    toast(`Lipit din Excel: ${changes.length} rânduri (Ctrl+Z anulează)` + (badDates ? ` · ${badDates} date nevalide sărite` : ""), badDates ? 6000 : 3000);
  }

  async function addRow() {
    const p = state.part, base = {};
    if (p.period !== "crud") { base.an = state.an; base.luna = state.luna; }
    if (p.categorie) base.categorie_varsta = state.cat;
    if (p.period === "zi") {
      let d = ddmm(1, state.luna);
      for (;;) {
        d = prompt("Data zilei (ZZ.LL):", d); if (d == null) return;
        const chk = checkDate(p, p.dateField, d, true);
        if (!chk.error) { base[p.dateField] = chk.value; break; }
        alert(chk.error);
      }
      if (state.rows.some((r) => r[p.dateField] === base[p.dateField])) { toast(`Ziua ${base[p.dateField]} există deja în tabel`, 5000); return; }
    }
    else if (p.period === "lista" && p.dateField) { const t = todayStr(); base[p.dateField] = t.y === state.an && t.m === state.luna ? t.d : ddmm(1, state.luna); }
    p.cols.forEach(([k, l, t, o]) => { if (o && o.req && (t === "text" || t === "txt") && base[k] === undefined) base[k] = ""; });
    const { data, error } = await sb.from(p.key).insert(base).select().maybeSingle(); if (error) { toast("Eroare: " + error.message); return; }
    if (data) pushUndo({ kind: "add", key: p.key, id: data.id });
    markDirty(); await loadData(); if (data) focusRow(data.id);
  }
  async function deleteRow(id) {
    if (!confirm("Ștergeți acest rând?")) return;
    const row = state.rows.find((r) => r.id === id);
    const { error } = await sb.from(state.part.key).delete().eq("id", id); if (error) { toast("Eroare: " + error.message, 6000); return; }
    OB.remove(state.part.key, id); updateSaveState();
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
    const changes = state.rows.map((row) => {
      const work = Object.assign({}, row);
      cols.forEach(([k]) => { const rg = colRange(p, k); work[k] = rg.min + Math.floor(Math.random() * (rg.max - rg.min + 1)); });
      cols.forEach(([k]) => deriveRow(p, work, k));
      const fields = {}; effCols().forEach(([k]) => { if (work[k] !== row[k]) fields[k] = work[k]; });
      return { row, fields };
    });
    batchUpdate("auto valori", changes);
    toast("Valori generate (Ctrl+Z anulează)", 3000);
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
      if (!confirm("Copiați valorile din luna trecută peste rândurile acestei luni? (Ctrl+Z anulează)")) return;
      const changes = [];
      for (const r of state.rows) {
        const src = map[p.period === "zi" ? String(r[p.dateField]).slice(0, 2) : "_"]; if (!src) continue;
        const upd = {}; valCols.forEach((k) => { if (src[k] !== r[k]) upd[k] = src[k]; });
        if (Object.keys(upd).length) changes.push({ row: r, fields: upd });
      }
      batchUpdate("copiere luna trecută", changes);
      toast(`${changes.length} rânduri actualizate din luna trecută (Ctrl+Z anulează)`, 3000);
    } else {
      if (!confirm(`Adăugați în această lună cele ${data.length} rânduri din luna trecută? (Ctrl+Z anulează)`)) return;
      const rows = data.map((r) => { const o = {}; Object.keys(r).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = r[k]; }); o.an = state.an; o.luna = state.luna; if (p.dateField && /^\d{2}\.\d{2}$/.test(o[p.dateField] || "")) o[p.dateField] = o[p.dateField].slice(0, 3) + pad2(state.luna); return o; });
      const { data: ins, error } = await sb.from(p.key).insert(rows).select("id"); if (error) { toast("Eroare: " + error.message, 6000); return; }
      pushUndo({ kind: "addMany", key: p.key, ids: (ins || []).map((r) => r.id) });
      toast(`${rows.length} rânduri copiate (Ctrl+Z anulează)`, 3000); await loadData();
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
    const rows = state.rows, stale = () => state.rows !== rows; // o încărcare mai nouă a înlocuit rândurile
    try {
      if (p.key === "documente_continut_czu") {
        const { data } = await sb.from("documente_inregistrate").select("*").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const map = {}; (data || []).forEach((r) => { const t = (+r.total_imprumuturi || 0) || P3_DIN.reduce((a, k) => a + (+r[k] || 0), 0); if (r.data) map[r.data] = t; });
        if (stale()) return;
        state.aux.p3 = map;
        const others = effCols().filter((c) => c[0].indexOf("czu_") === 0 && c[0] !== "czu_8_limbi").map((c) => c[0]);
        for (const r of rows) {
          const upd = {}, p3t = map[r.data] || 0;
          if (p3t > 0 && (+r.total_imprumuturi || 0) !== p3t) { r.total_imprumuturi = p3t; upd.total_imprumuturi = p3t; }
          const czu8 = window.RegistruLogic.czuRemainder(r.total_imprumuturi, others.map((k) => r[k]));
          if ((+r.czu_8_limbi || 0) !== czu8) { r.czu_8_limbi = czu8; upd.czu_8_limbi = czu8; }
          if (Object.keys(upd).length) queueSave(p.key, r.id, upd);
        }
      } else if (p.key === "evidenta_utilizatori_copii_adulti") {
        const q = (t) => sb.from(t).select("data,total_participanti").eq("an", state.an).eq("luna", state.luna).eq("categorie_varsta", state.cat);
        const [ix, xi] = await Promise.all([q("instruiri"), q("activitati_culturale")]);
        if (stale()) return;
        const im = {}, xm = {}; (ix.data || []).forEach((r) => { if (r.data) im[r.data] = (im[r.data] || 0) + (+r.total_participanti || 0); }); (xi.data || []).forEach((r) => { if (r.data) xm[r.data] = (xm[r.data] || 0) + (+r.total_participanti || 0); });
        for (const r of rows) { const u = {}; const ins = im[r.data] || 0, act = xm[r.data] || 0;
          if ((+r.instruiri || 0) !== ins) { r.instruiri = ins; u.instruiri = ins; } if ((+r.activitati_culturale_stiintifice || 0) !== act) { r.activitati_culturale_stiintifice = act; u.activitati_culturale_stiintifice = act; }
          const it = P2_INTR.reduce((a, k) => a + (+r[k] || 0), 0); if ((+r.intrari_total_zi || 0) !== it) { r.intrari_total_zi = it; u.intrari_total_zi = it; }
          if (Object.keys(u).length) queueSave(p.key, r.id, u); }
      }
    } catch (e) { /* nu bloca */ }
  }

  // Sincronizare inversă: editarea Părții II (instruiri/activități) → IX/XI.
  // Diferența față de suma din IX/XI se pune pe primul rând al zilei (o scădere se ia pe rând,
  // de la primul); celelalte instruiri/activități ale zilei rămân neatinse. Fără rânduri → se adaugă unul.
  async function reverseSync(col, dateStr, value) {
    if (!dateStr) return;
    const table = col === "instruiri" ? "instruiri" : "activitati_culturale";
    const an = state.an, luna = state.luna, cat = state.cat, nr = table === "instruiri" ? "IX" : "XI";
    const { data, error } = await sb.from(table).select("id,total_participanti,prescolari,categorie_varsta").eq("an", an).eq("luna", luna).eq("categorie_varsta", cat).eq("data", dateStr).order("id", { ascending: true });
    if (error) { toast(`Sincronizarea cu Partea ${nr} a eșuat: ${error.message}`, 6000); return; }
    if (data && data.length) {
      const rows = data.map((r) => Object.assign({}, r, OB.pending(table, r.id) || {}));
      let delta = value - rows.reduce((a, r) => a + (+r.total_participanti || 0), 0);
      if (!delta) return;
      const set = (r, t) => { const u = { total_participanti: t }; if (table === "instruiri" && r.categorie_varsta === "copii") u.elevi = Math.max(0, t - (+r.prescolari || 0)); queueSave(table, r.id, u); };
      if (delta > 0) set(rows[0], (+rows[0].total_participanti || 0) + delta);
      else for (const r of rows) { if (!delta) break; const cur = +r.total_participanti || 0, take = Math.min(cur, -delta); if (take) { set(r, cur - take); delta += take; } }
      if (rows.length > 1) toast(`Partea ${nr}: ${dateStr} are ${rows.length} rânduri — diferența a fost pusă pe primul. Verificați acolo dacă e corect.`, 6000);
    } else if (value > 0) {
      const ins = { an, luna, categorie_varsta: cat, data: dateStr, total_participanti: value };
      if (table === "activitati_culturale") ins.total_activitati = 1;
      const { error: e2 } = await sb.from(table).insert(ins);
      if (e2) toast(`Sincronizarea cu Partea ${nr} a eșuat: ${e2.message}`, 6000);
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
      const ex = new Set(chosen), df = state.part.dateField, toDel = state.rows.filter((r) => ex.has(r[df]));
      const filled = toDel.filter(rowHasContent);
      const keepFilled = filled.length > 0 && !confirm(`Atenție: ${filled.length} zi(le) bifate au deja date completate (${filled.map((r) => r[df]).join(", ")}).\n\nOK = ștergeți și aceste rânduri · Anulare = păstrați-le`);
      for (const r of toDel) {
        if (keepFilled && rowHasContent(r)) continue;
        const { error } = await sb.from(state.part.key).delete().eq("id", r.id);
        if (error) { toast("Eroare la ștergere: " + error.message, 6000); break; }
        OB.remove(state.part.key, r.id);
        if (rowHasContent(r)) pushUndo({ kind: "del", key: state.part.key, row: { ...r } });
      }
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

  // Supabase întoarce cel mult 1000 de rânduri pe cerere → citim pe pagini. `build` = funcție
  // care construiește interogarea (cu ordine stabilă), apelată pentru fiecare pagină.
  async function fetchRows(build) {
    let all = [];
    for (let from = 0; ; from += 1000) {
      const { data, error } = await build().range(from, from + 999);
      if (error) throw new Error(error.message);
      all = all.concat(data || []);
      if (!data || data.length < 1000) return all;
    }
  }

  // ---- Dashboard ------------------------------------------------------------
  async function computeBadges() {
    state.incomplete = [];
    const results = await Promise.all(PARTS.map(async (p) => {
      const build = () => { let q = sb.from(p.key).select("*"); if (p.period !== "crud") q = q.eq("an", state.an); return q.order("id", { ascending: true }); };
      try { return { p, rows: await fetchRows(build) }; } catch (e) { return { p, rows: [] }; }
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
    $("homeFolderRestore").onclick = restoreFromFolder;
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
    const dataByPart = {}, failed = [];
    (await Promise.all(PARTS.map(async (p) => {
      const build = () => {
        let q = sb.from(p.key).select("*"); if (p.period !== "crud") q = q.eq("an", state.an);
        q = (p.orderById || !p.dateField) ? q.order("id", { ascending: true }) : q.order(p.dateField, { ascending: true });
        return q.order("id", { ascending: true });
      };
      try { return [p.key, await fetchRows(build)]; } catch (e) { failed.push(`Partea ${p.nr}`); return [p.key, []]; }
    }))).forEach(([k, v]) => (dataByPart[k] = v));
    setBusy(false);
    if (failed.length) { $("fin_status").textContent = "Nu am putut citi: " + failed.join(", ") + ". Verificați conexiunea și încercați din nou."; return; }
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
  async function toggleStaff(id, activ) { const { error } = await sb.from("personal").update({ activ }).eq("id", id); if (error) toast("Eroare: " + error.message, 6000); await loadStaff(); }
  async function deleteStaff(id) { if (!confirm("Ștergeți persoana?")) return; const { error } = await sb.from("personal").delete().eq("id", id); if (error) toast("Eroare: " + error.message, 6000); await loadStaff(); renderStaff(); }

  function renderImport() {
    $("content").innerHTML = `<div style="max-width:720px"><h3 style="margin-top:0">Migrare din aplicația desktop (SQLite)</h3>
      <p class="status">Alegeți fișierul <b>biblioteca.db</b> din aplicația desktop (folderul <code>app\\data</code>).</p>
      <input type="file" id="sqliteFile" accept=".db,.sqlite,.sqlite3"><button id="doSqlite">Importă din SQLite</button>
      <hr style="margin:20px 0;border:0;border-top:1px solid var(--line)"><h3>Import din Excel (backup)</h3>
      <input type="file" id="xlsxFile" accept=".xlsx"><button id="doXlsx">Importă din Excel</button>
      <label class="row" style="margin:10px 0"><input type="checkbox" id="impReplace" style="width:auto;margin-right:8px"><b>Înlocuiește</b> datele existente (restaurare curată — șterge înainte de import)</label>
      <pre id="importLog" style="margin-top:8px;background:#0f172a;color:#cbd5e1;padding:12px;border-radius:8px;max-height:320px;overflow:auto;font-size:12px;white-space:pre-wrap"></pre>
      <p class="status">Fără „Înlocuiește": importul e sigur și se poate repeta — zilele/lunile se actualizează, iar la celelalte părți se adaugă doar rândurile care lipsesc (nimic nu se dublează). Cu „Înlocuiește": părțile din fișier sunt înlocuite deodată (totul sau nimic). Înainte de orice import se face automat o copie a datelor de acum.</p></div>`;
    const logEl = $("importLog"), log = (m) => { logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; };
    const run = async (btnId, fileId, fn) => {
      const f = $(fileId).files[0]; if (!f) { toast("Alegeți un fișier"); return; }
      const replace = $("impReplace").checked;
      if (replace && !confirm("Mod înlocuire: părțile din fișier vor ÎNLOCUI datele de acum (se face întâi o copie de siguranță). Continuați?")) return;
      logEl.textContent = ""; $(btnId).disabled = true;
      try {
        commitActive(); await flushNow();
        log("Copie de siguranță a datelor de acum…");
        const pre = await takeSnapshot(true);
        if (pre.skip) { log("✗ Reconectați-vă întâi."); return; }
        const name = `registru_inainte-de-import_${window.RegistruBackup.stamp()}.json`;
        const up = await window.RegistruBackup.cloudBackup(sb, () => {}, { snapshot: pre.obj, name });
        if (up.error) { download(new Blob([JSON.stringify(pre.obj)], { type: "application/json" }), name); log("  ✔ descărcată pe calculator: " + name); }
        else log("  ✔ în cloud: " + name + " (se poate restaura din Acasă → Restaurează din cloud)");
        await fn(sb, f, log, { replace });
        window.RegistruBackup.markSnapshot(null);
        await loadSettings(); await loadStaff();
      } catch (e) { log("✗ " + e.message); } finally { $(btnId).disabled = false; }
    };
    $("doSqlite").onclick = () => run("doSqlite", "sqliteFile", window.RegistruImport.migrateSqlite);
    $("doXlsx").onclick = () => run("doXlsx", "xlsxFile", window.RegistruImport.importExcel);
  }

  // ---- Export / print / backup ----------------------------------------------
  // Excel-ul tabelului de pe ecran: aceleași coloane și denumiri ca în aplicație + rândul Total.
  // (Pentru backup complet / reimport există „Salvează copie"; foaia nu se numește exact
  // „Partea N", ca importul să n-o confunde cu o foaie de backup.)
  function exportCurrent() {
    const p = state.part; if (!isPart() || !state.rows.length) { toast("Nimic de exportat"); return; }
    const cols = effCols(), heads = cols.map(label);
    const val = (r, [k, l, t]) => t === "int" ? (+r[k] || 0) : cellText(r, k, t);
    const aoa = [heads].concat(state.rows.map((r) => cols.map((c) => val(r, c))));
    const acc = computeAcc(cols, state.rows);
    aoa.push(cols.map(([k], i) => (i === 0 ? "Total" : acc[k] == null ? "" : acc[k])));
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    ws["!cols"] = heads.map((h) => ({ wch: Math.max(8, Math.min(30, String(h).length + 2)) }));
    const per = p.period === "luna" ? String(state.an) : p.period === "crud" ? "" : `${LUNI[state.luna - 1].slice(0, 3)} ${state.an}`;
    const sheet = `Partea ${p.nr}${per ? " - " + per : ""}${p.categorie ? " " + (state.cat === "adulti" ? "Adulți" : "Copii") : ""}`.slice(0, 31);
    const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, sheet);
    XLSX.writeFile(wb, `partea_${p.nr}_${state.an}_${pad2(state.luna)}${p.categorie ? "_" + state.cat : ""}.xlsx`);
  }
  function printCurrent() {
    const p = state.part, cols = effCols(), ori = state.settings.print_orientation || "landscape";
    const head = `<tr>${cols.map((c) => `<th>${esc(label(c))}</th>`).join("")}</tr>`;
    const body = state.rows.map((r) => `<tr>${cols.map(([k, l, t]) => `<td>${esc(cellText(r, k, t))}</td>`).join("")}</tr>`).join("") +
      totalsRows().map(([l2, acc]) => `<tr>${cols.map(([k], i) => `<td style="font-weight:700;background:#eef2f7">${i === 0 ? esc(l2) : acc[k] == null ? "" : acc[k]}</td>`).join("")}</tr>`).join("");
    const per = p.period === "luna" ? `Anul ${state.an}` : (p.period !== "crud" ? `${LUNI[state.luna - 1]} ${state.an}` : "");
    const w = window.open("", "_blank");
    w.document.write(`<html><head><meta charset="utf-8"><title>Partea ${p.nr}</title><style>@page{size:A4 ${ori}}body{font:11px Segoe UI,sans-serif}h3{margin:0 0 8px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:3px;text-align:center}th{background:#eef2f7}</style></head><body><h3>Partea ${p.nr}. ${esc(p.title)} — ${per}${p.categorie ? " (" + state.cat + ")" : ""}</h3><table>${head}${body}</table><script>window.onload=function(){window.print()}<\/script></body></html>`);
    w.document.close();
  }
  function refreshBackupInfo() { const h = window.RegistruBackup.hoursSinceBackup(), info = $("backupInfo"); info.textContent = h === null ? "fără backup" : h > 24 ? `backup acum ${Math.floor(h / 24)}z` : "backup recent ✔"; }
  // ---- Copii de siguranță ---------------------------------------------------
  let localDirty = false;
  function markDirty() { localDirty = true; }
  // Copie completă, verificată: fără login sau cu mult mai puține rânduri decât data
  // trecută (ex. tabele citite goale) NU o salvăm peste copiile bune.
  async function takeSnapshot(force) {
    const { data } = await sb.auth.getSession(); if (!data || !data.session) return { skip: true };
    const obj = await window.RegistruBackup.snapshot(sb);
    const chk = window.RegistruBackup.checkSnapshot(obj);
    if (!chk.ok && !force) return { suspect: chk };
    return { obj, total: chk.total };
  }
  let suspectWarned = false;
  function warnSuspect(c) {
    if (suspectWarned) return; suspectWarned = true;
    toast(`⚠ Copia de acum are doar ${c.total} rânduri (data trecută: ${c.prev}). Nu am suprascris copiile bune. Dacă ați șters date intenționat, apăsați „Salvează copie”.`, 10000);
  }
  async function saveLocalFolder(note, request, snap) {
    try {
      const F = window.RegistruLocalFolder; if (!F || !F.supported) return false;
      const h = await F.getFolder(request); if (!h) return false;
      const s = snap || await takeSnapshot(false);
      if (s.skip) return false;
      if (s.suspect) { warnSuspect(s.suspect); return false; }
      await F.saveSnapshot(h, s.obj, window.RegistruBackup.stamp());
      window.RegistruBackup.markSnapshot(s.total);
      localDirty = false; try { localStorage.setItem("lastLocalFolder", new Date().toISOString()); } catch (e) {}
      if (note) note("Copie salvată în folderul local ✔");
      return true;
    } catch (e) { if (note) note("Folder local: " + e.message); return false; }
  }
  async function restoreFromFolder() {
    const F = window.RegistruLocalFolder; if (!F || !F.supported) { toast("Necesită Chrome/Edge"); return; }
    const h = await F.getFolder(true); if (!h) { toast("Folderul local nu e configurat"); return; }
    const names = (await F.listNames(h)).filter((n) => n !== "registru_backup.json");
    const rows = [`<div style="display:flex;gap:8px;align-items:center;padding:5px 4px;border-bottom:1px solid var(--line)"><span style="flex:1;font-size:13px"><b>Cea mai recentă copie</b></span><button class="ghost lf-rs" data-n="registru_backup.json">Alege…</button></div>`]
      .concat(names.map((n) => `<div style="display:flex;gap:8px;align-items:center;padding:5px 4px;border-bottom:1px solid var(--line)"><span style="flex:1;font-size:13px">${esc(window.RegistruBackup.describe(n))}</span><button class="ghost lf-rs" data-n="${esc(n)}">Alege…</button></div>`)).join("");
    $("settings").innerHTML = `<div class="box"><h3>📂 Copii din folderul local</h3>
      <p class="status">Alegeți copia; în pasul următor alegeți ce părți se restaurează.</p>
      <div style="max-height:320px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 8px">${rows}</div>
      <div class="actions"><button class="ghost" id="lf_close">Închide</button></div></div>`;
    $("settings").classList.remove("hidden");
    $("lf_close").onclick = () => $("settings").classList.add("hidden");
    $("settings").querySelectorAll(".lf-rs").forEach((b) => (b.onclick = async () => {
      try { openRestoreDialog(await F.readSnapshot(h, b.dataset.n), "folderul local (" + (b.dataset.n === "registru_backup.json" ? "cea mai recentă" : window.RegistruBackup.describe(b.dataset.n)) + ")"); }
      catch (e) { toast("Nu pot citi copia: " + e.message, 6000); }
    }));
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
    const note = (m) => ($("backupInfo").textContent = m);
    note("Se pregătește copia…");
    let s = await takeSnapshot(false);
    if (s.skip) { toast("Reconectați-vă întâi", 4000); return; }
    if (s.suspect) {
      if (!confirm(`Copia de acum are ${s.suspect.total} rânduri, față de ${s.suspect.prev} data trecută.\n\nAți șters intenționat date? OK = salvează totuși · Anulare = nu salva`)) { note("Copie anulată"); return; }
      s = await takeSnapshot(true);
    }
    await window.RegistruBackup.runBackup(sb, { note }, s.obj.tables);
    await window.RegistruBackup.cloudBackup(sb, note, { snapshot: s.obj });
    await saveLocalFolder(note, true, s);
    window.RegistruBackup.markSnapshot(s.total);
    refreshBackupInfo(); if (state.part === HOME) renderHome();
  }
  // La pornire și apoi la fiecare oră: copie în folderul local (dacă s-a modificat ceva)
  // și în cloud (dacă a trecut intervalul din Setări). Ora ultimei copii cloud se citește
  // din lista de copii, nu din acest browser — corect și pe alt calculator.
  let autoBusy = false, autoFirst = true;
  async function maybeAutoBackup() {
    if (autoBusy || needLogin || $("app").classList.contains("hidden")) return;
    autoBusy = true;
    try {
      const days = toInt(state.settings.backup_days || "0");
      let needCloud = false;
      if (days) { const t = await window.RegistruBackup.lastCloudBackupTime(sb); needCloud = !t || Date.now() - t > days * 864e5; }
      const F = window.RegistruLocalFolder;
      const canLocal = (autoFirst || localDirty) && F && F.supported && !!(await F.getFolder(false));
      autoFirst = false;
      if (!needCloud && !canLocal) return;
      const s = await takeSnapshot(false);
      if (s.skip) return;
      if (s.suspect) { warnSuspect(s.suspect); return; }
      if (canLocal) await saveLocalFolder(null, false, s);
      if (needCloud) await window.RegistruBackup.cloudBackup(sb, (m) => ($("backupInfo").textContent = m), { snapshot: s.obj });
      window.RegistruBackup.markSnapshot(s.total);
      refreshBackupInfo();
    } catch (e) { /* încercăm din nou peste o oră */ } finally { autoBusy = false; }
  }
  async function openCloudRestore() {
    $("settings").innerHTML = `<div class="box"><h3>☁ Copii în cloud</h3><p class="status">Se încarcă lista…</p></div>`;
    $("settings").classList.remove("hidden");
    const list = await window.RegistruBackup.listCloudBackups(sb);
    const rows = list.map((f) => `<div style="display:flex;gap:8px;align-items:center;padding:5px 4px;border-bottom:1px solid var(--line)"><span style="flex:1;font-size:13px">${esc(window.RegistruBackup.describe(f.name))}</span><button class="ghost cr-dl" data-n="${esc(f.name)}" title="Descarcă pe PC">⬇</button><button class="ghost cr-rs" data-n="${esc(f.name)}">Alege…</button></div>`).join("") || "<div class='pp-empty'>Nicio copie în cloud.</div>";
    $("settings").innerHTML = `<div class="box"><h3>☁ Copii în cloud</h3>
      <p class="status">Alegeți copia; în pasul următor alegeți ce părți se restaurează.</p>
      <div style="max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 8px">${rows}</div>
      <div style="margin-top:10px"><label class="status" style="display:inline">Sau dintr-un fișier .json de pe calculator: </label><input type="file" id="cr_file" accept=".json,application/json" style="width:auto"></div>
      <div class="actions"><button class="ghost" id="cr_close">Închide</button></div></div>`;
    $("cr_close").onclick = () => $("settings").classList.add("hidden");
    $("cr_file").onchange = async () => { const f = $("cr_file").files[0]; if (!f) return; try { openRestoreDialog(JSON.parse(await f.text()), "fișierul " + f.name); } catch (e) { toast("Fișier invalid: " + e.message, 6000); } };
    $("settings").querySelectorAll(".cr-dl").forEach((b) => (b.onclick = async () => { try { const obj = await window.RegistruBackup.downloadCloud(sb, b.dataset.n); download(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }), b.dataset.n); } catch (e) { toast("Eroare: " + e.message); } }));
    $("settings").querySelectorAll(".cr-rs").forEach((b) => (b.onclick = async () => {
      try { openRestoreDialog(await window.RegistruBackup.downloadCloud(sb, b.dataset.n), "cloud (" + window.RegistruBackup.describe(b.dataset.n) + ")"); } catch (e) { toast("Eroare: " + e.message, 6000); }
    }));
  }

  // ---- Restaurare sigură ----------------------------------------------------
  // Părțile bifate sunt ÎNLOCUITE exact cu cele din copie, totul-sau-nimic (funcția
  // restore_tables din baza de date). Înainte se face automat o copie a datelor de acum.
  function restoreGroups() {
    return PARTS.map((p) => ({ label: `Partea ${p.nr}. ${p.title}`, tables: [p.key], on: true })).concat([
      { label: "Personal (responsabili)", tables: ["personal"], on: true },
      { label: "Liste text, etichete coloane, range-uri", tables: ["text_presets", "etichete_custom", "range_config"], on: true },
      { label: "Setări (nume bibliotecă, zile libere, copertă…)", tables: ["app_settings"], on: false },
    ]);
  }
  function openRestoreDialog(obj, source) {
    const T = (obj && obj.tables) || {};
    if (!Object.keys(T).length) { toast("Copia nu conține date", 5000); return; }
    const groups = restoreGroups(), cnt = (ts) => ts.reduce((a, t) => a + ((T[t] || []).length), 0);
    const when = obj.created ? new Date(obj.created).toLocaleString("ro-RO") : "dată necunoscută";
    const items = groups.map((g, i) => `<label class="row" style="margin:3px 0;font-size:13px"><input type="checkbox" data-g="${i}" ${g.on && cnt(g.tables) > 0 ? "checked" : ""} ${T[g.tables[0]] ? "" : "disabled"} style="width:auto;margin-right:8px">${esc(g.label)} <span class="status" style="margin-left:6px">(${T[g.tables[0]] ? cnt(g.tables) + " rânduri" : "lipsește din copie"})</span></label>`).join("");
    $("settings").innerHTML = `<div class="box"><h3>↺ Restaurare din copie</h3>
      <p style="font-size:13px">Copia din <b>${esc(when)}</b> · sursa: ${esc(source)}.</p>
      <p class="status">Părțile bifate vor fi <b>înlocuite exact</b> cu cele din copie (totul sau nimic — dacă ceva nu merge, nu se schimbă nimic). Înainte, aplicația face automat o copie a datelor de acum.</p>
      <div style="display:flex;gap:6px;margin:6px 0"><button class="ghost" id="rs_all">Bifează tot</button><button class="ghost" id="rs_none">Debifează tot</button></div>
      <div style="max-height:280px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:6px 10px">${items}</div>
      <pre id="rs_log" style="margin-top:10px;background:#0f172a;color:#cbd5e1;padding:10px;border-radius:8px;max-height:180px;overflow:auto;font-size:12px;white-space:pre-wrap;display:none"></pre>
      <div class="actions"><button class="ghost" id="rs_cancel">Închide</button><button class="ok" id="rs_go">Restaurează părțile bifate</button></div></div>`;
    $("settings").classList.remove("hidden");
    const boxes = () => [...$("settings").querySelectorAll("input[data-g]")];
    $("rs_all").onclick = () => boxes().forEach((b) => { if (!b.disabled) b.checked = true; });
    $("rs_none").onclick = () => boxes().forEach((b) => (b.checked = false));
    $("rs_cancel").onclick = () => $("settings").classList.add("hidden");
    $("rs_go").onclick = async () => {
      const chosen = boxes().filter((b) => b.checked).map((b) => groups[+b.dataset.g]);
      if (!chosen.length) { toast("Bifați cel puțin o parte"); return; }
      const emptied = chosen.filter((g) => !cnt(g.tables)).map((g) => g.label);
      if (!confirm(`Înlocuiți ${chosen.length} părți cu datele din copia de ${when}?\n\nDatele de acum ale acestor părți vor fi înlocuite (se face întâi o copie de siguranță).` +
        (emptied.length ? `\n\n⚠ Aceste părți sunt GOALE în copie și vor fi golite:\n• ${emptied.join("\n• ")}` : ""))) return;
      $("rs_go").disabled = true;
      try { await runRestore(obj, chosen.flatMap((g) => g.tables)); } finally { const b = $("rs_go"); if (b) b.disabled = false; }
    };
  }
  async function runRestore(obj, tabele) {
    const log = $("rs_log"); log.style.display = "block"; log.textContent = "";
    const put = (m) => { log.textContent += m + "\n"; log.scrollTop = log.scrollHeight; };
    commitActive(); await flushNow();
    // 1. Copie de siguranță a datelor de ACUM (ca restaurarea să poată fi anulată)
    put("1/3 Copie de siguranță a datelor de acum…");
    const pre = await takeSnapshot(true);
    if (pre.skip) { put("✗ Reconectați-vă întâi."); return; }
    const preName = `registru_inainte-de-restaurare_${window.RegistruBackup.stamp()}.json`;
    let saved = false;
    const up = await window.RegistruBackup.cloudBackup(sb, () => {}, { snapshot: pre.obj, name: preName });
    if (!up.error) { saved = true; put("   ✔ în cloud: " + preName); }
    const F = window.RegistruLocalFolder;
    try { const h = F && F.supported && (await F.getFolder(true)); if (h) { await F.saveNamed(h, preName, pre.obj); saved = true; put("   ✔ în folderul local"); } } catch (e) { /* încercăm descărcarea */ }
    if (!saved) { download(new Blob([JSON.stringify(pre.obj)], { type: "application/json" }), preName); put("   ✔ descărcată pe calculator: " + preName); }
    // 2. Restaurarea propriu-zisă
    put("2/3 Restaurare…");
    const payload = { created: obj.created || null, tables: {} };
    tabele.forEach((t) => (payload.tables[t] = (obj.tables && obj.tables[t]) || []));
    const { data, error } = await sb.rpc("restore_tables", { payload, tabele });
    if (error && (error.code === "PGRST202" || /could not find the function/i.test(error.message || ""))) {
      put("   (baza de date nu are încă migrarea 001 — folosesc metoda veche, tabel cu tabel)");
      await window.RegistruImport.restoreJson(sb, payload, put, { replace: true });
    } else if (error) {
      put("✗ Restaurarea a eșuat: " + error.message + "\n   Nimic nu s-a schimbat în registru."); return;
    } else {
      Object.keys(data || {}).forEach((t) => put(`   ⟳ ${t}: ${data[t]} rânduri`));
    }
    // 3. Modificările netrimise ale acestor părți ar suprascrie datele restaurate → renunțăm la ele
    OB.list().forEach((it) => { if (tabele.includes(it.table)) OB.remove(it.table, it.id); });
    updateSaveState();
    put("3/3 Gata ✔  (Dacă v-ați răzgândit: restaurați copia „înainte de restaurare”.)");
    window.RegistruBackup.markSnapshot(null);
    await loadSettings(); await loadStaff();
    if (isPart()) loadData(); else if (state.part === HOME) renderHome();
  }

  // ---- Istoric modificări (tabelul „istoric", scris de baza de date) -------
  // Fiecare adăugare / modificare / ștergere, cu cine și când; „↶ Revino" readuce valorile.
  const HIST_PAGE = 100;
  const SUPPORT_NAMES = { personal: "Personal", app_settings: "Setări", text_presets: "Liste text", etichete_custom: "Etichete coloane", range_config: "Range-uri", "*": "Tot registrul" };
  function histTableName(t) { const p = PARTS.find((x) => x.key === t); return p ? `Partea ${p.nr}` : (SUPPORT_NAMES[t] || t); }
  function histColLabel(t, k) {
    const p = PARTS.find((x) => x.key === t); if (!p) return k;
    const c = [...p.cols, ...((p.extra && p.extra.adulti) || []), ...((p.extra && p.extra.copii) || [])].find((x) => x[0] === k);
    return c ? c[1] : k;
  }
  function histRowLabel(e) {
    const i = e.ident || {}, bits = [];
    if (i.data) bits.push(i.data); else if (i.luna) bits.push(LUNI[(+i.luna || 1) - 1]);
    if (i.an && !i.data) bits.push(i.an);
    if (i.categorie_varsta) bits.push(i.categorie_varsta === "adulti" ? "Adulți" : "Copii");
    ["nume_prenume", "partener", "cheie"].forEach((k) => { if (i[k]) bits.push(i[k]); });
    return bits.join(" · ");
  }
  const histVal = (v) => v === true ? "✓" : v === false ? "—" : v == null || v === "" ? "∅" : String(v);
  function histWhat(e) {
    if (e.operatie === "INSERT") return "rând adăugat";
    if (e.operatie === "DELETE") return "rând șters";
    if (e.operatie === "RESTORE") { const n = e.nou || {}; return `restaurare din copia ${n.copia_din ? new Date(n.copia_din).toLocaleString("ro-RO") : ""} (${(n.tabele || []).map(histTableName).join(", ")})`; }
    const v = e.vechi || {}, n = e.nou || {};
    return Object.keys(n).map((k) => `${esc(histColLabel(e.tabel, k))}: ${esc(histVal(v[k]))} → <b>${esc(histVal(n[k]))}</b>`).join("<br>");
  }
  async function renderHistory(more) {
    if (!more || !state.hist) state.hist = { rows: [], filter: (state.hist && state.hist.filter) || "", done: false };
    const h = state.hist;
    if (!more) $("content").innerHTML = `<div class="status">Se încarcă…</div>`;
    let q = sb.from("istoric").select("*").order("id", { ascending: false }).limit(HIST_PAGE);
    if (h.rows.length) q = q.lt("id", h.rows[h.rows.length - 1].id);
    if (h.filter) q = q.eq("tabel", h.filter);
    const { data, error } = await q;
    if (state.part !== HISTORY) return;
    if (error) {
      const missing = /istoric|PGRST205|42P01|does not exist|schema cache/i.test((error.code || "") + " " + error.message);
      $("content").innerHTML = `<div class="card" style="max-width:640px"><h3>🕘 Istoric modificări</h3><p>${missing ? "Istoricul va fi disponibil după actualizarea bazei de date (migrarea <b>001</b> — vezi instrucțiunile)." : "Eroare: " + esc(error.message)}</p></div>`;
      return;
    }
    h.rows = h.rows.concat(data || []); h.done = (data || []).length < HIST_PAGE;
    const opts = [`<option value="">Toate părțile</option>`].concat(PARTS.map((p) => `<option value="${p.key}" ${h.filter === p.key ? "selected" : ""}>Partea ${p.nr}. ${esc(p.title)}</option>`),
      Object.keys(SUPPORT_NAMES).filter((k) => k !== "*").map((k) => `<option value="${k}" ${h.filter === k ? "selected" : ""}>${esc(SUPPORT_NAMES[k])}</option>`)).join("");
    // Rândurile create deodată (zilele unei luni noi, copierea lunii) → o singură linie.
    const groupKey = (e) => e.operatie === "INSERT" ? [e.tabel, e.utilizator, (e.ident || {}).luna, (e.ident || {}).categorie_varsta].join("|") : null;
    const lines = [];
    h.rows.forEach((e, i) => {
      const last = lines[lines.length - 1], gk = groupKey(e);
      if (gk && last && last.gk === gk && Math.abs(Date.parse(last.e.la) - Date.parse(e.la)) < 60000) { last.n++; last.first = e; return; }
      lines.push({ e, i, gk, n: 1, first: e });
    });
    const body = lines.map(({ e, i, n, first }) => {
      if (n > 1) {
        const d1 = (first.ident || {}).data, d2 = (e.ident || {}).data;
        return `<tr><td style="padding:6px 8px;white-space:nowrap">${esc(new Date(e.la).toLocaleString("ro-RO"))}</td><td style="padding:6px 8px">${esc(e.utilizator || "")}</td><td style="padding:6px 8px;white-space:nowrap">${esc(histTableName(e.tabel))}</td><td style="padding:6px 8px">${esc(d1 && d2 ? d1 + " … " + d2 : histRowLabel(e))}</td><td style="padding:6px 8px;text-align:left">${n} rânduri adăugate deodată</td><td></td></tr>`;
      }
      const can = (e.operatie === "UPDATE" && e.vechi) || (e.operatie === "DELETE" && e.vechi) || (e.operatie === "INSERT" && e.rand_id != null);
      const btn = can ? `<button class="ghost hs-undo" data-i="${i}" title="${e.operatie === "INSERT" ? "Șterge rândul adăugat" : e.operatie === "DELETE" ? "Readu rândul șters" : "Readu valorile de dinainte"}">↶ Revino</button>` : "";
      return `<tr><td style="padding:6px 8px;white-space:nowrap">${esc(new Date(e.la).toLocaleString("ro-RO"))}</td><td style="padding:6px 8px">${esc(e.utilizator || "")}</td><td style="padding:6px 8px;white-space:nowrap">${esc(histTableName(e.tabel))}</td><td style="padding:6px 8px">${esc(histRowLabel(e))}</td><td style="padding:6px 8px;text-align:left;white-space:normal">${histWhat(e)}</td><td style="padding:4px">${btn}</td></tr>`;
    }).join("") || `<tr><td colspan="6" style="padding:16px;color:var(--muted)">Nicio modificare înregistrată încă.</td></tr>`;
    $("content").innerHTML = `<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap"><select id="hs_filter">${opts}</select><button class="ghost" id="hs_refresh">↻ Reîmprospătează</button><span class="status">Modificările făcute „din mers" (în ~2 minute) pe același rând apar într-o singură linie.</span></div>
      <div class="tablebox"><table><thead><tr><th>Când</th><th>Cine</th><th>Partea</th><th>Rândul</th><th>Ce s-a schimbat</th><th></th></tr></thead><tbody>${body}</tbody></table></div>
      ${h.done ? "" : `<div style="margin-top:10px"><button class="ghost" id="hs_more">Mai multe…</button></div>`}`;
    $("hs_filter").onchange = () => { h.filter = $("hs_filter").value; renderHistory(false); };
    $("hs_refresh").onclick = () => renderHistory(false);
    if ($("hs_more")) $("hs_more").onclick = () => renderHistory(true);
    $("content").querySelectorAll(".hs-undo").forEach((b) => (b.onclick = () => revertHistory(h.rows[+b.dataset.i])));
  }
  async function revertHistory(e) {
    const where = `${histTableName(e.tabel)}${histRowLabel(e) ? " — " + histRowLabel(e) : ""}`;
    if (e.operatie === "UPDATE") {
      const what = Object.keys(e.vechi).map((k) => `${histColLabel(e.tabel, k)}: ${histVal((e.nou || {})[k])} → ${histVal(e.vechi[k])}`).join("\n");
      if (!confirm(`Readuceți valorile de dinainte?\n${where}\n\n${what}`)) return;
      if (e.rand_id != null) queueSave(e.tabel, e.rand_id, e.vechi);
      else if (e.tabel === "app_settings" && e.ident && e.ident.cheie) { const { error } = await sb.from("app_settings").upsert(Object.assign({ cheie: e.ident.cheie }, e.vechi), { onConflict: "cheie" }); if (error) { toast("Eroare: " + error.message, 6000); return; } }
      toast("Valorile de dinainte au fost readuse ✔", 3000);
    } else if (e.operatie === "DELETE") {
      if (!confirm(`Readuceți rândul șters?\n${where}`)) return;
      const row = Object.assign({}, e.vechi); delete row.created_at; delete row.updated_at;
      const { error } = e.tabel === "app_settings" ? await sb.from("app_settings").upsert(row, { onConflict: "cheie" }) : await sb.from(e.tabel).insert(row);
      if (error) { toast(/duplicate|unique/i.test(error.message) ? "Există deja un rând pentru aceeași dată — nu l-am readus." : "Eroare: " + error.message, 7000); return; }
      toast("Rândul a fost readus ✔", 3000);
    } else if (e.operatie === "INSERT") {
      if (!confirm(`Ștergeți rândul adăugat atunci?\n${where}\n\n(Dacă între timp a fost completat, se pierd și acele valori — dar rămân în istoric.)`)) return;
      const { error } = await sb.from(e.tabel).delete().eq("id", e.rand_id);
      if (error) { toast("Eroare: " + error.message, 6000); return; }
      OB.remove(e.tabel, e.rand_id); toast("Rândul a fost șters ✔", 3000);
    }
    setTimeout(() => { if (state.part === HISTORY) renderHistory(false); }, 1200);
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
        const nw = Object.assign({}, payload.new, OB.pending(table, payload.new.id) || {});
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
    commitActive(); // celula în care tocmai scrieți devine primul pas de anulat
    const e = undoStack.pop(); if (!e) { toast("Nimic de anulat"); return; }
    if (e.key && isPart() && e.key !== state.part.key) { toast("Anulare disponibilă pe partea unde s-a modificat"); undoStack.push(e); return; }
    if (e.kind === "add") { const { error } = await sb.from(e.key).delete().eq("id", e.id); if (error) { toast("Eroare: " + error.message, 6000); undoStack.push(e); return; } await loadData(); toast("Anulat: adăugare"); return; }
    if (e.kind === "addMany") { const { error } = await sb.from(e.key).delete().in("id", e.ids); if (error) { toast("Eroare: " + error.message, 6000); undoStack.push(e); return; } await loadData(); toast(`Anulat: ${e.ids.length} rânduri adăugate`); return; }
    if (e.kind === "del") { const o = {}; Object.keys(e.row).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = e.row[k]; }); const { error } = await sb.from(e.key).insert(o); if (error) { toast("Eroare: " + error.message, 6000); undoStack.push(e); return; } await loadData(); toast("Anulat: ștergere"); return; }
    if (e.kind === "batch") {
      for (const u of e.rows) { const row = state.rows.find((r) => r.id === u.id); if (row) Object.assign(row, u.old); queueSave(e.key, u.id, u.old); }
      renderGrid(); toast("Anulat: " + e.label); return;
    }
    const row = state.rows.find((r) => r.id === e.id); if (!row) { toast("Rândul nu mai există"); return; }
    row[e.col] = e.old;
    const affected = deriveRow(state.part, row, e.col); affected.add(e.col);
    const payload = {}; affected.forEach((k) => (payload[k] = row[k]));
    queueSave(e.key, e.id, payload);
    const cdef = effCols().find((c) => c[0] === e.col);
    if (e.key === "evidenta_utilizatori_copii_adulti" && cdef && cdef[3] && cdef[3].rev) reverseSync(e.col, row.data, +row[e.col] || 0);
    const inp = $("content").querySelector(`tbody input[data-id="${e.id}"][data-col="${e.col}"]`); if (inp) focusOld.set(inp, row[e.col]);
    refreshRowUI(e.id, affected, null); toast("Anulat (Ctrl+Z)");
  }

  // ---- Duplică rând (events / Ctrl+D) ---------------------------------------
  async function duplicateRow() {
    if (state.part.period !== "lista") { toast("Duplicarea e disponibilă pe părțile cu evenimente"); return; }
    const el = document.activeElement; let src;
    if (el && el.matches && el.matches("#content tbody input")) src = state.rows.find((r) => r.id === +el.dataset.id);
    if (!src) src = state.rows[state.rows.length - 1];
    if (!src) { toast("Niciun rând de duplicat"); return; }
    const o = {}; Object.keys(src).forEach((k) => { if (!["id", "created_at", "updated_at"].includes(k)) o[k] = src[k]; });
    const { data: made, error } = await sb.from(state.part.key).insert(o).select("id").maybeSingle(); if (error) { toast("Eroare: " + error.message, 6000); return; }
    if (made) pushUndo({ kind: "add", key: state.part.key, id: made.id });
    toast("Rând duplicat (Ctrl+Z anulează)", 3000); await loadData(); if (made) focusRow(made.id);
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
    else if (k === "s") { e.preventDefault(); commitActive(); flushNow().then(() => toast(OB.size() ? `⚠ ${OB.size()} modificări încă în așteptare (păstrate pe calculator)` : "✔ Toate modificările sunt salvate", 3000)); }
    else if (k === "e") { if (isPart()) { e.preventDefault(); exportCurrent(); } }
    else if (k === "c") { const el = document.activeElement; if (el && el.matches && el.matches("#content tbody input") && el.type !== "checkbox" && el.selectionStart === el.selectionEnd && navigator.clipboard) navigator.clipboard.writeText(el.value || "").catch(() => {}); }
    else if (k === "d") { if (isPart() && state.part.period === "lista") { e.preventDefault(); duplicateRow(); } }
    else if (e.shiftKey && k === "m") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista")) { e.preventDefault(); copyLastMonth(); } }
    else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && document.activeElement && document.activeElement.matches && document.activeElement.matches("input[type=text], input[type=email], textarea") && !["int", "date"].includes(document.activeElement.dataset.type)) { /* mutare pe cuvinte în text */ }
    else if (e.key === "ArrowLeft") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista") && state.luna > 1) { e.preventDefault(); state.luna--; loadData(); updateChrome(); } }
    else if (e.key === "ArrowRight") { if (isPart() && (state.part.period === "zi" || state.part.period === "lista") && state.luna < 12) { e.preventDefault(); state.luna++; loadData(); updateChrome(); } }
  });
  $("loginBtn").onclick = login;
  $("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
  $("email").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); if ($("password").value) login(); else $("password").focus(); } });
  $("settingsBtn").onclick = openSettings;
  $("menuBtn").onclick = () => { const a = document.querySelector("aside"); if (a) a.classList.toggle("open"); };
  document.addEventListener("paste", handlePaste);
  setInterval(() => { if (localDirty) saveLocalFolder(null, false); }, 5 * 60 * 1000);
  setInterval(() => { if (OB.size() && !needLogin) flushNow(); }, 15000);
  setInterval(maybeAutoBackup, 60 * 60 * 1000);
  $("saveState").style.cursor = "pointer";
  $("saveState").onclick = () => { retryDelay = 0; commitActive(); flushNow(); };
  // Închiderea filei: celula curentă intră în coadă (sincron); dacă mai e ceva netrimis,
  // browserul întreabă „Părăsiți pagina?" și încercăm o trimitere de ultimă clipă.
  window.addEventListener("beforeunload", (e) => {
    if ($("app").classList.contains("hidden")) return;
    commitActive();
    if (OB.size()) { sendBeacons(); e.preventDefault(); e.returnValue = ""; return ""; }
  });
  window.addEventListener("pagehide", () => { commitActive(); if (OB.size()) sendBeacons(); });
  window.addEventListener("online", () => { retryDelay = 0; flushNow(); });
  window.addEventListener("offline", () => updateSaveState());
  // Revenire după somn / altă filă: trimite ce a rămas și reîmprospătează datele (pot fi învechite).
  let hiddenAt = 0;
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { hiddenAt = Date.now(); commitActive(); flushNow(); if (localDirty) saveLocalFolder(null, false); return; }
    if ($("app").classList.contains("hidden")) return;
    flushNow();
    if (hiddenAt && Date.now() - hiddenAt > 60000 && isPart() && editingRowId() === null) { subscribe(state.part.key); loadData(); }
  });
  sb.auth.onAuthStateChange((event, s) => {
    authSession = s;
    // (fără apeluri Supabase direct în callback — recomandarea supabase-js)
    if (event === "SIGNED_OUT" && !loggingOut && !$("app").classList.contains("hidden")) setTimeout(showRelogin, 0);
    if (s && needLogin && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) setTimeout(() => { hideRelogin(); flushNow(); }, 0);
  });
  $("logout").onclick = async () => {
    commitActive(); await flushNow();
    if (OB.size() && !confirm(`${OB.size()} modificări nu au ajuns încă în registru. Rămân păstrate pe acest calculator și se trimit la următoarea autentificare.\n\nIeșiți totuși?`)) return;
    loggingOut = true; await sb.auth.signOut(); location.reload();
  };
  sb.auth.getSession().then(({ data }) => { if (data.session) onLoggedIn(); });
})();
