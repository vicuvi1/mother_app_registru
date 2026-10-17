// ============================================================================
// Import / Migrare date — încarcă în Supabase datele existente, în browser.
//   • din baza SQLite a aplicației desktop (biblioteca.db) — recomandat
//   • dintr-un fișier Excel exportat de această aplicație (backup)
// Fără backend: SQLite prin sql.js, Excel prin SheetJS.
// ============================================================================
(function () {
  // sql-wasm.wasm din vendor/; deschis de pe disc (file://) browserul nu-l poate încărca → CDN
  const SQLJS_CDN = location.protocol === "file:" ? "https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/" : "./vendor/";
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

  // Semnătura unui rând pe câmpurile date (fără id / created_at / updated_at). Text gol = lipsă.
  const norm = (v) => (v === undefined || v === "" ? null : v);
  const sigOf = (o, keys) => JSON.stringify(keys.map((k) => norm(o[k])));
  async function fetchAllRows(sb, table) {
    let all = [];
    for (let from = 0; ; from += 1000) {
      const { data, error } = await sb.from(table).select("*").range(from, from + 999);
      if (error) throw new Error(`${table}: ${error.message}`);
      all = all.concat(data || []);
      if (!data || data.length < 1000) return all;
    }
  }
  // Tabele fără cheie naturală (evenimente, parteneri, voluntari…): adaugă doar rândurile care
  // nu există deja. Numără pe semnătură, ca două activități identice reale din fișier să rămână două.
  async function insertNew(sb, table, rows, log) {
    const clean = rows.map(cleanRow);
    if (!clean.length) return { table, inserted: 0 };
    const keys = [...new Set(clean.flatMap((r) => Object.keys(r)))].sort();
    const have = new Map();
    (await fetchAllRows(sb, table)).forEach((r) => { const s = sigOf(r, keys); have.set(s, (have.get(s) || 0) + 1); });
    const fresh = clean.filter((r) => { const s = sigOf(r, keys), n = have.get(s) || 0; if (n > 0) { have.set(s, n - 1); return false; } return true; });
    let inserted = 0;
    for (let i = 0; i < fresh.length; i += 200) {
      const { error } = await sb.from(table).insert(fresh.slice(i, i + 200));
      if (error) { log(`  ✗ ${table}: ${error.message}`); return { table, inserted, error: error.message }; }
      inserted += Math.min(200, fresh.length - i);
    }
    log(`  ✓ ${table}: ${inserted} rânduri noi${clean.length - fresh.length ? ` (${clean.length - fresh.length} existau deja — sărite)` : ""}`);
    return { table, inserted };
  }

  // Aplică datele citite dintr-un fișier: { tabel: [rânduri] }.
  //  • fără „Înlocuiește": tabelele cu cheie (zile/luni) se actualizează pe cheie, celelalte primesc
  //    doar rândurile noi → re-importul nu dublează nimic;
  //  • cu „Înlocuiește": toate tabelele din fișier sunt înlocuite DEODATĂ (restore_tables, totul-sau-nimic);
  //    setările (app_settings) se doar actualizează, nu se șterg.
  async function applyImport(sb, data, log, replace) {
    const tables = ALL_TABLES.filter((t) => data[t] && data[t].length);
    let total = 0;
    if (replace) {
      const repl = tables.filter((t) => t !== "app_settings"), payload = { created: null, tables: {} };
      repl.forEach((t) => (payload.tables[t] = data[t].map(cleanRow)));
      if (repl.length) {
        const { data: res, error } = await sb.rpc("restore_tables", { payload, tabele: repl });
        if (error && (error.code === "PGRST202" || /could not find the function/i.test(error.message || ""))) {
          log("  (baza de date fără migrarea 001 — înlocuire tabel cu tabel)");
          for (const t of repl) total += (await insertRows(sb, t, data[t], log, true)).inserted || 0;
        } else if (error) {
          log("✗ Importul a eșuat: " + error.message + "\n  Nimic nu s-a schimbat în registru."); return 0;
        } else Object.keys(res || {}).forEach((t) => { log(`  ⟳ ${t}: ${res[t]} rânduri`); total += res[t]; });
      }
      if (tables.includes("app_settings")) total += (await insertRows(sb, "app_settings", data.app_settings, log, false)).inserted || 0;
      return total;
    }
    for (const t of tables) {
      const r = CONFLICT[t] ? await insertRows(sb, t, data[t], log, false) : await insertNew(sb, t, data[t], log);
      total += r.inserted || 0;
    }
    return total;
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

      const data = {};
      for (const t of ALL_TABLES) {
        if (!present.has(t)) continue;
        const q = db.exec(`SELECT * FROM "${t}"`);
        if (!q[0]) { log(`  · ${t}: gol`); continue; }
        const cols = q[0].columns;
        data[t] = q[0].values.map((vals) => {
          const o = {}; cols.forEach((c, i) => (o[c] = vals[i])); return o;
        });
      }
      const total = await applyImport(sb, data, log, replace);
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
    const data = {};
    for (const sheet of wb.SheetNames) {
      const table = tableForSheet(sheet);
      if (!table) { log(`  · foaie ignorată: „${sheet}" (necunoscută)`); continue; }
      data[table] = (data[table] || []).concat(XLSX.utils.sheet_to_json(wb.Sheets[sheet]));
    }
    const total = await applyImport(sb, data, log, replace);
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
