// ============================================================================
// Coada de salvare („outbox") — fiecare modificare de celulă e scrisă ÎNTÂI
// în localStorage (sincron, supraviețuiește închiderii filei / căderii
// internetului / pierderii sesiunii), apoi trimisă la Supabase. Iese din coadă
// DOAR după ce serverul confirmă că rândul s-a modificat. La repornirea
// aplicației, ce a rămas în coadă se retrimite.
//
// Logică pură (fără DOM / Supabase) — testată de outbox.test.js în Node.
//   create(storage, key) → { put, pending, list, size, flush, clear, remove }
//   flush(send): send(table, id, fields) → "ok" | "retry" | "auth" | { drop: motiv }
// ============================================================================
(function () {
  function create(storage, key) {
    let items = load(), stored = true;
    let flushing = null, queued = null;

    function load() {
      try { const o = JSON.parse(storage.getItem(key) || "{}"); return o && typeof o === "object" ? o : {}; }
      catch (e) { return {}; }
    }
    function persist() {
      try { storage.setItem(key, JSON.stringify(items)); stored = true; return true; } catch (e) { stored = false; return false; }
    }
    // Aplicația poate fi deschisă în două file: coada stă în localStorage, comun tuturor.
    // Recitim înainte de fiecare operație, ca o filă să nu șteargă modificările celeilalte.
    // (Dacă scrierea a eșuat — spațiu plin — memoria e singura copie: nu o înlocuim.)
    function sync() { if (stored) items = load(); }
    const k = (table, id) => table + ":" + id;

    // Adaugă/combină câmpurile unui rând. Valorile mai noi le înlocuiesc pe cele vechi.
    // Întoarce false dacă nu s-a putut scrie în localStorage (spațiu plin / blocat).
    function put(table, id, fields) {
      sync();
      const it = items[k(table, id)] || (items[k(table, id)] = { table, id, fields: {}, v: 0 });
      Object.assign(it.fields, fields);
      it.v++; it.ts = Date.now();
      return persist();
    }
    function pending(table, id) { sync(); const it = items[k(table, id)]; return it ? it.fields : null; }
    function list() { sync(); return Object.keys(items).map((x) => items[x]); }
    function size() { sync(); return Object.keys(items).length; }
    function clear() { items = {}; persist(); }
    // Rândul a fost șters intenționat → nu mai are sens să-l trimitem.
    function remove(table, id) { sync(); if (items[k(table, id)]) { delete items[k(table, id)]; persist(); } }

    // Trimite tot ce e în coadă, pe rând. Se oprește la prima problemă de rețea
    // sau de autentificare (nu insistă inutil); erorile permanente (ex. valoare
    // respinsă de baza de date) scot rândul din coadă și sunt raportate.
    async function runFlush(send) {
      const res = { sent: 0, dropped: [], stopped: null };
      for (const it of list()) {
        const key = k(it.table, it.id), v = it.v, fields = Object.assign({}, it.fields);
        let r;
        try { r = await send(it.table, it.id, fields); } catch (e) { r = "retry"; }
        sync();
        const cur = items[key];
        if (r === "ok") {
          // Dacă între timp s-a mai editat rândul, rămâne în coadă (se retrimite).
          if (cur && cur.v === v) { delete items[key]; persist(); }
          res.sent++;
        } else if (r && typeof r === "object" && r.drop) {
          if (cur && cur.v === v) { delete items[key]; persist(); }
          res.dropped.push({ table: it.table, id: it.id, fields, reason: r.drop });
        } else {
          res.stopped = r === "auth" ? "auth" : "retry";
          break;
        }
      }
      res.left = size();
      return res;
    }
    // Un singur flush odată; cererile venite între timp se adună într-o singură
    // rulare următoare (care prinde și modificările făcute între timp).
    function flush(send) {
      if (!flushing) { flushing = runFlush(send).finally(() => { flushing = null; }); return flushing; }
      if (!queued) queued = flushing.catch(() => {}).then(() => { queued = null; return flush(send); });
      return queued;
    }

    return { put, pending, list, size, flush, clear, remove };
  }

  // Clasificarea unui răspuns Supabase la un update (folosit de app.js).
  //   error: { code, message } | null ; status: HTTP ; rows: rânduri modificate
  function classify(error, status, rows) {
    if (error) {
      const code = String(error.code || ""), msg = String(error.message || "");
      if (status === 401 || /jwt|token/i.test(msg) || code === "PGRST301" || code === "PGRST303") return "auth";
      // Erori permanente: date/constrângeri/coloană inexistentă — retrimiterea n-ar ajuta.
      if (/^(22|23|42)/.test(code) || /^PGRST[12]/.test(code) || status === 400 || status === 404 || status === 409) return { drop: msg || code };
      return "retry"; // rețea (status 0), 5xx, timeout
    }
    return rows > 0 ? "ok" : "none"; // "none" = 0 rânduri: sesiune pierdută SAU rând șters
  }

  const api = { create, classify };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.RegistruOutbox = api;
})();
