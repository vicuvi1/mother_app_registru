// ============================================================================
// Import / Migrare date — încarcă în Supabase datele existente, în browser.
//   • din baza SQLite a aplicației desktop (biblioteca.db) — recomandat
//   • dintr-un fișier Excel exportat de această aplicație (backup)
// Fără backend: SQLite prin sql.js, Excel prin SheetJS.
// ============================================================================
(function () {
  const SQLJS_CDN = "https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/";
  const SKIP = new Set(["id", "created_at", "updated_at"]); // lăsăm Postgres să le genereze

  // Coloane boolean (SQLite le ține ca 0/1; Postgres cere true/false)
  const BOOL = new Set(["is_auto_generated", "activ"]);
  (window.REGISTRU_PARTS || []).forEach((p) =>
    p.cols.forEach(([k, l, t]) => { if (t === "bool") BOOL.add(k); }));

  const ALL_TABLES = (window.RegistruBackup && window.RegistruBackup.ALL_TABLES) || [];

  // Chei unice → import idempotent (upsert). Tabelele fără cheie (evenimente,
  // crud) rămân additive. Astfel, re-importul NU dublează datele importante.
  const CONFLICT = {
    personal: "nume_prenume", range_config: "parte,coloana", etichete_custom: "parte,camp",
    text_presets: "parte,camp,valoare", app_settings: "cheie",
    evidenta_utilizatori: "an,luna,data",
    evidenta_utilizatori_copii_adulti: "an,luna,data,categorie_varsta",
    documente_inregistrate: "an,luna,data,categorie_varsta",
    documente_continut_czu: "an,luna,data,categorie_varsta",
    documente_electronice: "an,luna,categorie_varsta",
  };

  function cleanRow(obj) {
    const out = {};
    for (const k of Object.keys(obj)) {
      if (SKIP.has(k)) continue;
      let v = obj[k];
      if (v === undefined) continue;
      if (BOOL.has(k) && (v === 0 || v === 1 || v === "0" || v === "1")) v = !!Number(v);
      out[k] = v;
    }
    return out;
  }

  async function insertRows(sb, table, rows, log, replace) {
    if (!rows.length) return { table, inserted: 0 };
    if (replace && table !== "app_settings") { await sb.from(table).delete().gte("id", 0); }
    const clean = rows.map(cleanRow);
    const target = CONFLICT[table];
    let inserted = 0;
    for (let i = 0; i < clean.length; i += 200) {
      const batch = clean.slice(i, i + 200);
      const { error } = target ? await sb.from(table).upsert(batch, { onConflict: target }) : await sb.from(table).insert(batch);
      if (error) { log(`  ✗ ${table}: ${error.message}`); return { table, inserted, error: error.message }; }
      inserted += batch.length;
    }
    log(`  ${replace ? "⟳" : "✓"} ${table}: ${inserted} rânduri`);
    return { table, inserted };
  }

  // ---- Migrare din SQLite (biblioteca.db) -----------------------------------
  async function migrateSqlite(sb, file, log, opts) {
    const replace = !!(opts && opts.replace);
    log("Se citește baza SQLite…" + (replace ? " (mod înlocuire)" : ""));
    const buf = new Uint8Array(await file.arrayBuffer());
    const SQL = await initSqlJs({ locateFile: (f) => SQLJS_CDN + f });
    let db;
    try {
      db = new SQL.Database(buf);
    } catch (e) { log("✗ Fișier SQLite invalid: " + e.message); return; }
    try {
      const present = new Set();
      const res = db.exec("SELECT name FROM sqlite_master WHERE type='table'");
      if (res[0]) res[0].values.forEach((r) => present.add(r[0]));

      let total = 0;
      for (const t of ALL_TABLES) {
        if (!present.has(t)) continue;
        const q = db.exec(`SELECT * FROM "${t}"`);
        if (!q[0]) { log(`  · ${t}: gol`); continue; }
        const cols = q[0].columns;
        const rows = q[0].values.map((vals) => {
          const o = {}; cols.forEach((c, i) => (o[c] = vals[i])); return o;
        });
        const r = await insertRows(sb, t, rows, log, replace);
        total += r.inserted || 0;
      }
      log(`Gata. Total importat: ${total} rânduri.`);
    } finally {
      db.close();
    }
  }

  // ---- Import Excel (backup produs de această aplicație) --------------------
  function tableForSheet(name) {
    const p = (window.REGISTRU_PARTS || []).find((p) => `Partea ${p.nr}` === name);
    if (p) return p.key;
    if (ALL_TABLES.includes(name)) return name;
    return null;
  }

  async function importExcel(sb, file, log, opts) {
    const replace = !!(opts && opts.replace);
    log("Se citește Excel…" + (replace ? " (mod înlocuire)" : ""));
    const buf = new Uint8Array(await file.arrayBuffer());
    const wb = XLSX.read(buf, { type: "array" });
    let total = 0;
    for (const sheet of wb.SheetNames) {
      const table = tableForSheet(sheet);
      if (!table) { log(`  · foaie ignorată: „${sheet}" (necunoscută)`); continue; }
      const rows = XLSX.utils.sheet_to_json(wb.Sheets[sheet]);
      const r = await insertRows(sb, table, rows, log, replace);
      total += r.inserted || 0;
    }
    log(`Gata. Total importat: ${total} rânduri.`);
  }

  // ---- Restaurare din snapshot JSON (backup cloud/local) --------------------
  async function restoreJson(sb, obj, log, opts) {
    const replace = !!(opts && opts.replace);
    const tables = (obj && obj.tables) || {};
    let total = 0;
    for (const t of ALL_TABLES) {
      const rows = tables[t]; if (!rows || !rows.length) continue;
      const r = await insertRows(sb, t, rows, log, replace);
      total += r.inserted || 0;
    }
    log(`Gata. Total restaurat: ${total} rânduri.`);
  }

  window.RegistruImport = { migrateSqlite, importExcel, restoreJson };
})();
