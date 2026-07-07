// ============================================================================
// Backup local — descarcă TOATE datele din Supabase pe PC (Excel + SQLite).
// „Local + cloud": Supabase e copia vie/partajată, iar acesta e copia locală.
// Fără build step — folosește SheetJS (xlsx) și sql.js (SQLite WASM) din CDN.
// ============================================================================
(function () {
  // Toate tabelele registrului (identice cu schema.sql / modelele SQLAlchemy).
  const ALL_TABLES = [
    "personal", "range_config", "etichete_custom", "app_settings", "text_presets",
    "evidenta_utilizatori", "evidenta_utilizatori_copii_adulti", "documente_inregistrate",
    "documente_continut_czu", "cercetari_bibliografice", "activitati_informare",
    "documente_electronice", "instruiri", "activitati_culturale", "activitati_online",
    "parteneri", "voluntariat",
  ];

  // Nume scurte (max 31 caractere) pentru foile Excel.
  const SHEET = {
    evidenta_utilizatori: "Partea I",
    evidenta_utilizatori_copii_adulti: "Partea II",
    documente_inregistrate: "Partea III",
    documente_continut_czu: "Partea IV",
    cercetari_bibliografice: "Partea V",
    activitati_informare: "Partea VI",
    documente_electronice: "Partea VII",
    instruiri: "Partea IX",
    activitati_culturale: "Partea XI",
    activitati_online: "Partea XII",
    parteneri: "Partea XIII",
    voluntariat: "Partea XIV",
  };

  const SQLJS_CDN = "https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/";

  function stamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  }

  function downloadBytes(bytes, filename, mime) {
    const blob = new Blob([bytes], { type: mime || "application/octet-stream" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  // Descarcă un tabel complet, paginat (PostgREST limitează implicit la 1000 rânduri).
  async function fetchTable(sb, t) {
    const page = 1000;
    let from = 0, all = [];
    for (;;) {
      const { data, error } = await sb.from(t).select("*").range(from, from + page - 1);
      if (error) throw new Error(`${t}: ${error.message}`);
      all = all.concat(data || []);
      if (!data || data.length < page) break;
      from += page;
    }
    return all;
  }

  async function fetchAll(sb, onProgress) {
    const out = {};
    for (let i = 0; i < ALL_TABLES.length; i++) {
      const t = ALL_TABLES[i];
      if (onProgress) onProgress(i + 1, ALL_TABLES.length, t);
      out[t] = await fetchTable(sb, t);
    }
    return out;
  }

  // ---- Excel (.xlsx) — o foaie per tabel ------------------------------------
  function buildExcel(dataByTable) {
    const wb = XLSX.utils.book_new();
    for (const t of ALL_TABLES) {
      const rows = dataByTable[t];
      if (!rows || !rows.length) continue;
      const ws = XLSX.utils.json_to_sheet(rows);
      let name = SHEET[t] || t;
      if (name.length > 31) name = name.slice(0, 31);
      XLSX.utils.book_append_sheet(wb, ws, name);
    }
    const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
    return new Uint8Array(out);
  }

  // ---- SQLite (.sqlite) — deschizibil de aplicația desktop ------------------
  async function buildSqlite(dataByTable) {
    const SQL = await initSqlJs({ locateFile: (f) => SQLJS_CDN + f });
    const db = new SQL.Database();
    try {
      for (const t of ALL_TABLES) {
        const rows = dataByTable[t];
        if (!rows || !rows.length) continue;
        const cols = Object.keys(rows[0]);
        const quoted = cols.map((c) => `"${c}"`).join(", ");
        db.run(`CREATE TABLE "${t}" (${quoted});`);
        const placeholders = cols.map(() => "?").join(", ");
        const stmt = db.prepare(`INSERT INTO "${t}" (${quoted}) VALUES (${placeholders});`);
        try {
          for (const r of rows) {
            stmt.run(cols.map((c) => {
              const v = r[c];
              if (v === null || v === undefined) return null;
              if (typeof v === "boolean") return v ? 1 : 0;
              return v;
            }));
          }
        } finally {
          stmt.free();
        }
      }
      return db.export(); // Uint8Array
    } finally {
      db.close();
    }
  }

  // ---- Backup complet (ambele formate) --------------------------------------
  async function runBackup(sb, ui) {
    ui = ui || {};
    const note = ui.note || (() => {});
    try {
      note("Se descarcă datele din Supabase…");
      const data = await fetchAll(sb, (i, n, t) => note(`Descărcare ${i}/${n}: ${t}`));

      note("Se generează Excel…");
      downloadBytes(buildExcel(data), `registru_backup_${stamp()}.xlsx`,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

      note("Se generează SQLite…");
      const sqlite = await buildSqlite(data);
      downloadBytes(sqlite, `registru_backup_${stamp()}.sqlite`, "application/x-sqlite3");

      try { localStorage.setItem("lastBackup", new Date().toISOString()); } catch (e) {}
      note("Backup local salvat ✔");
      return true;
    } catch (err) {
      note("Eroare backup: " + err.message);
      return false;
    }
  }

  // Câte ore de la ultimul backup (null dacă niciodată).
  function hoursSinceBackup() {
    try {
      const last = localStorage.getItem("lastBackup");
      if (!last) return null;
      return (Date.now() - new Date(last).getTime()) / 3.6e6;
    } catch (e) { return null; }
  }

  // ---- Backup în cloud (Supabase Storage, off-device) -----------------------
  async function cloudBackup(sb, note) {
    note = note || (() => {});
    try {
      note("Backup cloud: se colectează datele…");
      const data = await fetchAll(sb);
      const json = JSON.stringify({ created: new Date().toISOString(), tables: data });
      const name = `registru_${stamp()}.json`;
      const { error } = await sb.storage.from("backups").upload(name, new Blob([json], { type: "application/json" }), { upsert: false });
      if (error) { note("Backup cloud eșuat: " + error.message); return { error }; }
      try { localStorage.setItem("lastCloudBackup", new Date().toISOString()); } catch (e) {}
      note("Backup cloud salvat ✔ (" + name + ")");
      return { name };
    } catch (e) { note("Backup cloud eșuat: " + e.message); return { error: e }; }
  }
  function hoursSinceCloudBackup() {
    try { const last = localStorage.getItem("lastCloudBackup"); if (!last) return null; return (Date.now() - new Date(last).getTime()) / 3.6e6; } catch (e) { return null; }
  }
  async function listCloudBackups(sb) {
    const { data } = await sb.storage.from("backups").list("", { limit: 100, sortBy: { column: "name", order: "desc" } });
    return (data || []).filter((f) => f.name.endsWith(".json"));
  }
  async function downloadCloud(sb, name) {
    const { data, error } = await sb.storage.from("backups").download(name);
    if (error) throw new Error(error.message);
    return JSON.parse(await data.text());
  }

  window.RegistruBackup = { runBackup, hoursSinceBackup, cloudBackup, hoursSinceCloudBackup, listCloudBackups, downloadCloud, ALL_TABLES };
})();
