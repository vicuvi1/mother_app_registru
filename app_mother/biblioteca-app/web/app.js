// ============================================================================
// Motorul aplicației web — construiește toate părțile din REGISTRU_PARTS.
// Autentificare Supabase + tabele editabile + salvare live + realtime +
// export Excel + backup local + gestiune personal (responsabili).
// ============================================================================
(function () {
  const $ = (id) => document.getElementById(id);
  const PARTS = window.REGISTRU_PARTS;
  const STAFF = { key: "__staff" }; // pseudo-parte pentru gestiunea personalului
  const LUNI = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Noi","Dec"];

  if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) {
    $("authErr").textContent = "Lipsește config.js (URL + cheie Supabase).";
  }
  const sb = window.supabase.createClient(window.SUPABASE_URL || "", window.SUPABASE_ANON_KEY || "");

  const state = { part: null, an: 2026, luna: 7, cat: "copii", rows: [], staff: [] };
  let channel = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function toast(msg) {
    const t = $("toast"); t.textContent = msg; t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 1400);
  }
  const pad2 = (n) => String(n).padStart(2, "0");

  // ---- Autentificare --------------------------------------------------------
  async function login() {
    $("authErr").textContent = "";
    const { error } = await sb.auth.signInWithPassword({
      email: $("email").value.trim(), password: $("password").value,
    });
    if (error) { $("authErr").textContent = error.message; return; }
    onLoggedIn();
  }

  async function onLoggedIn() {
    const { data } = await sb.auth.getUser();
    if (!data.user) return;
    $("auth").classList.add("hidden");
    $("app").classList.remove("hidden");
    $("who").textContent = data.user.email;
    initSelectors();
    renderNav();
    await loadStaff();
    selectPart(PARTS[0].key);
    refreshBackupInfo();
  }

  // ---- Selectoare an / lună -------------------------------------------------
  function initSelectors() {
    if ($("an").options.length) return;
    for (let y = 2023; y <= 2027; y++) $("an").add(new Option(y, y, false, y === state.an));
    LUNI.forEach((m, i) => $("luna").add(new Option(m, i + 1, false, i + 1 === state.luna)));
    $("an").onchange = () => { state.an = +$("an").value; if (state.part !== STAFF) loadData(); };
    $("luna").onchange = () => { state.luna = +$("luna").value; if (state.part !== STAFF) loadData(); };
    $("cat").onchange = () => { state.cat = $("cat").value; if (state.part !== STAFF) loadData(); };
  }

  // ---- Navigație ------------------------------------------------------------
  function renderNav() {
    const nav = $("nav");
    nav.innerHTML =
      PARTS.map((p) => `<button class="nav" data-key="${p.key}">${p.nr}. ${esc(p.title)}</button>`).join("") +
      `<div class="navsep"></div>` +
      `<button class="nav" data-key="__staff">👤 Personal</button>`;
    nav.querySelectorAll("button.nav").forEach((b) =>
      (b.onclick = () => selectPart(b.dataset.key)));
  }
  function markActive(key) {
    document.querySelectorAll("#nav button.nav").forEach((b) =>
      b.classList.toggle("active", b.dataset.key === key));
  }

  function selectPart(key) {
    if (key === "__staff") {
      state.part = STAFF; updateHeader(); markActive(key);
      renderStaff(); subscribe("personal"); return;
    }
    state.part = PARTS.find((p) => p.key === key);
    updateHeader(); markActive(key); loadData(); subscribe(state.part.key);
  }

  function updateHeader() {
    const p = state.part;
    const isStaff = p === STAFF;
    $("title").textContent = isStaff ? "Personal (responsabili)" : `Partea ${p.nr} — ${p.title}`;
    const showPeriod = !isStaff && p.period !== "crud";
    $("anWrap").style.display = showPeriod ? "" : "none";
    $("lunaWrap").style.display = showPeriod ? "" : "none";
    $("catWrap").style.display = !isStaff && p.categorie ? "" : "none";
    $("addRow").style.display = isStaff ? "none" : "";
    $("exportBtn").style.display = isStaff ? "none" : "";
  }

  // ---- Încărcare + randare tabel -------------------------------------------
  async function loadData() {
    const p = state.part;
    let q = sb.from(p.key).select("*");
    if (p.period !== "crud") q = q.eq("an", state.an).eq("luna", state.luna);
    if (p.categorie) q = q.eq("categorie_varsta", state.cat);
    q = p.dateField ? q.order(p.dateField, { ascending: true }) : q.order("id", { ascending: true });
    const { data, error } = await q;
    if (error) { toast("Eroare: " + error.message); return; }
    state.rows = data || [];
    renderGrid();
  }

  function inputHtml(r, k, t, o) {
    const req = o && o.req ? 'data-req="1"' : "";
    const base = `data-id="${r.id}" data-col="${k}" data-type="${t}" ${req}`;
    const v = r[k];
    if (t === "int") return `<input class="num" type="number" min="0" value="${esc(v == null ? 0 : v)}" ${base}>`;
    if (t === "bool") return `<input type="checkbox" ${v ? "checked" : ""} ${base}>`;
    if (t === "date") return `<input class="date" type="date" value="${esc(v)}" ${base}>`;
    if (t === "staff") return `<input class="txt" type="text" list="staffList" value="${esc(v)}" ${base}>`;
    if (t === "txt") return `<input class="txt wide" type="text" value="${esc(v)}" ${base}>`;
    return `<input class="txt" type="text" value="${esc(v)}" ${base}>`;
  }

  function renderGrid() {
    const p = state.part;
    const head = "<tr>" + p.cols.map((c) => `<th title="${c[0]}">${esc(c[1])}</th>`).join("") + "<th></th></tr>";
    let body = state.rows.map((r) => {
      const tds = p.cols.map(([k, l, t, o]) => `<td>${inputHtml(r, k, t, o)}</td>`).join("");
      return `<tr>${tds}<td><button class="del" data-id="${r.id}" title="Șterge rândul">✕</button></td></tr>`;
    }).join("");
    if (!state.rows.length)
      body = `<tr><td colspan="${p.cols.length + 1}" style="padding:16px;color:var(--muted)">Niciun rând. Apăsați „+ Rând".</td></tr>`;
    $("content").innerHTML = `<div class="tablebox"><table>${head}${body}</table></div>`;

    $("content").querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", saveCell);
      if (inp.type !== "checkbox") {
        inp.addEventListener("input", () => inp.classList.add("dirty"));
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
      }
    });
    $("content").querySelectorAll(".del").forEach((b) =>
      (b.onclick = () => deleteRow(+b.dataset.id)));
  }

  // ---- Salvare / adăugare / ștergere ---------------------------------------
  async function saveCell(e) {
    const el = e.target;
    const id = +el.dataset.id, col = el.dataset.col, type = el.dataset.type;
    let val;
    if (type === "int") val = Math.max(0, parseInt(el.value || "0", 10) || 0);
    else if (type === "bool") val = el.checked;
    else val = el.value === "" ? (el.dataset.req ? "" : null) : el.value;
    const { error } = await sb.from(state.part.key).update({ [col]: val }).eq("id", id);
    if (error) { toast("Eroare salvare: " + error.message); return; }
    const r = state.rows.find((x) => x.id === id); if (r) r[col] = val;
    el.classList.remove("dirty");
    toast("Salvat");
  }

  async function addRow() {
    const p = state.part, base = {};
    if (p.period !== "crud") { base.an = state.an; base.luna = state.luna; }
    if (p.categorie) base.categorie_varsta = state.cat;
    const firstDay = `${state.an}-${pad2(state.luna)}-01`;
    if (p.period === "zi") {
      const d = prompt("Data (AAAA-LL-ZZ):", firstDay);
      if (!d) return;
      base[p.dateField] = d;
    } else if (p.period === "lista" && p.dateField) {
      base[p.dateField] = firstDay;
    }
    // valori implicite pentru coloanele text obligatorii (NOT NULL)
    p.cols.forEach(([k, l, t, o]) => {
      if (o && o.req && (t === "text" || t === "txt") && base[k] === undefined) base[k] = "";
    });
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
    if (p === STAFF || !state.rows.length) { toast("Nimic de exportat"); return; }
    const ws = XLSX.utils.json_to_sheet(state.rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, `Partea ${p.nr}`.slice(0, 31));
    XLSX.writeFile(wb, `partea_${p.nr}_${state.an}_${pad2(state.luna)}.xlsx`);
  }

  // ---- Personal (responsabili) ---------------------------------------------
  async function loadStaff() {
    const { data } = await sb.from("personal").select("*").order("nume_prenume");
    state.staff = data || [];
    $("staffList").innerHTML = state.staff.filter((s) => s.activ)
      .map((s) => `<option value="${esc(s.nume_prenume)}">`).join("");
  }
  function renderStaff() {
    const rows = state.staff.map((s) =>
      `<tr><td class="txtcell" style="text-align:left">${esc(s.nume_prenume)}</td>
       <td><input type="checkbox" ${s.activ ? "checked" : ""} class="sa" data-sid="${s.id}"></td>
       <td><button class="del" data-sid="${s.id}">✕</button></td></tr>`).join("");
    $("content").innerHTML =
      `<div class="tablebox" style="max-width:520px"><table>
        <tr><th style="text-align:left">Nume și prenume</th><th>Activ</th><th></th></tr>
        ${rows || `<tr><td colspan="3" style="padding:16px;color:var(--muted)">Nicio persoană încă.</td></tr>`}
       </table></div>
       <div style="margin-top:12px;display:flex;gap:8px;max-width:520px">
         <input id="newStaff" placeholder="Nume și prenume nou" style="flex:1">
         <button id="addStaff">+ Adaugă</button></div>`;
    $("addStaff").onclick = addStaff;
    $("content").querySelectorAll(".sa").forEach((c) =>
      (c.onchange = () => toggleStaff(+c.dataset.sid, c.checked)));
    $("content").querySelectorAll(".del").forEach((b) =>
      (b.onclick = () => deleteStaff(+b.dataset.sid)));
  }
  async function addStaff() {
    const n = $("newStaff").value.trim(); if (!n) return;
    const { error } = await sb.from("personal").insert({ nume_prenume: n, activ: true });
    if (error) { toast("Eroare: " + error.message); return; }
    await loadStaff(); renderStaff();
  }
  async function toggleStaff(id, activ) {
    await sb.from("personal").update({ activ }).eq("id", id); await loadStaff();
  }
  async function deleteStaff(id) {
    if (!confirm("Ștergeți această persoană?")) return;
    await sb.from("personal").delete().eq("id", id); await loadStaff(); renderStaff();
  }

  // ---- Realtime (multi-user) ------------------------------------------------
  function subscribe(table) {
    if (channel) sb.removeChannel(channel);
    channel = sb.channel("rt-" + table)
      .on("postgres_changes", { event: "*", schema: "public", table }, () => {
        if (state.part === STAFF) loadStaff().then(renderStaff);
        else loadData();
      })
      .subscribe((st) => {
        const live = $("live"), ok = st === "SUBSCRIBED";
        live.textContent = ok ? "live" : "offline"; live.classList.toggle("live", ok);
      });
  }

  // ---- Backup local ---------------------------------------------------------
  function refreshBackupInfo() {
    const h = window.RegistruBackup.hoursSinceBackup();
    const info = $("backupInfo"), btn = $("backup");
    if (h === null) { info.textContent = "fără backup local încă"; btn.style.background = "var(--accent)"; btn.style.color = "#fff"; }
    else if (h > 24) { info.textContent = `ultimul backup acum ${Math.floor(h / 24)} zi(le)`; btn.style.background = "var(--accent)"; btn.style.color = "#fff"; }
    else { info.textContent = "backup local recent ✔"; btn.style.background = ""; btn.style.color = ""; }
  }
  async function doBackup() {
    await window.RegistruBackup.runBackup(sb, { note: (m) => ($("backupInfo").textContent = m) });
    refreshBackupInfo();
  }

  // ---- Legături globale -----------------------------------------------------
  $("loginBtn").onclick = login;
  $("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
  $("addRow").onclick = addRow;
  $("exportBtn").onclick = exportCurrent;
  $("backup").onclick = doBackup;
  $("logout").onclick = async () => { await sb.auth.signOut(); location.reload(); };

  sb.auth.getSession().then(({ data }) => { if (data.session) onLoggedIn(); });
})();
