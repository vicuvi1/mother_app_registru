// ============================================================================
// DOAR PENTRU TESTARE LOCALĂ — se încarcă numai cu index.html?mock=1.
// Înlocuiește Supabase cu o bază falsă ținută în localStorage-ul browserului,
// ca aplicația să poată fi testată fără cont și fără a atinge datele reale.
// Imită ce contează pentru salvare: RLS (fără login: citirile întorc [] și
// update-urile modifică 0 rânduri, FĂRĂ eroare), erori de rețea, JWT expirat,
// constrângeri unice, valori implicite.
//
// Comenzi în consolă (window.__mock):
//   offline = true      → orice cerere eșuează ca la căderea internetului
//   loggedOut = true    → sesiunea dispare „pe tăcute" (cazul care pierdea date)
//   expired = true      → serverul răspunde 401 JWT expired
//   signOutEvent()      → sesiunea expiră cu eveniment SIGNED_OUT
//   delay = 80          → latența fiecărei cereri (ms)
//   rows(t) / reset()   → vezi tabelul t / golește baza
// ============================================================================
(function () {
  const DBKEY = "mockdb_v1", SKEY = "mock_session";
  const M = (window.__mock = { offline: false, loggedOut: false, expired: false, delay: 80, requests: 0 });
  const UNIQUE = {
    evidenta_utilizatori: ["an", "luna", "data"],
    evidenta_utilizatori_copii_adulti: ["an", "luna", "data", "categorie_varsta"],
    documente_inregistrate: ["an", "luna", "data", "categorie_varsta"],
    documente_continut_czu: ["an", "luna", "data", "categorie_varsta"],
    documente_electronice: ["an", "luna", "categorie_varsta"],
    personal: ["nume_prenume"], app_settings: ["cheie"],
  };
  let db = load();
  function load() { try { return JSON.parse(localStorage.getItem(DBKEY)) || { tables: {}, seq: 1 }; } catch (e) { return { tables: {}, seq: 1 }; } }
  function save() { localStorage.setItem(DBKEY, JSON.stringify(db)); }
  const tbl = (t) => db.tables[t] || (db.tables[t] = []);
  M.rows = (t) => JSON.parse(JSON.stringify(tbl(t)));
  M.reset = () => { db = { tables: {}, seq: 1 }; save(); };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const same = (a, b) => String(a) === String(b);

  function defaults(t) {
    const p = (window.REGISTRU_PARTS || []).find((x) => x.key === t), o = {};
    if (p) [...p.cols, ...((p.extra && p.extra.adulti) || []), ...((p.extra && p.extra.copii) || [])].forEach(([k, l, ty]) => { o[k] = ty === "int" ? 0 : ty === "bool" ? false : null; });
    return o;
  }
  function conflict(t, row, ignoreId) {
    const u = UNIQUE[t]; if (!u) return null;
    return tbl(t).find((r) => r.id !== ignoreId && u.every((c) => same(r[c], row[c]))) || null;
  }

  class Query {
    constructor(t) { this.t = t; this.op = "select"; this.f = []; this.ord = null; this.one = false; this.rng = null; }
    select() { return this; }
    insert(rows) { this.op = "insert"; this.payload = rows; return this; }
    update(obj) { this.op = "update"; this.payload = obj; return this; }
    upsert(rows, opts) { this.op = "upsert"; this.payload = rows; this.opts = opts || {}; return this; }
    delete() { this.op = "delete"; return this; }
    eq(c, v) { this.f.push((r) => same(r[c], v)); return this; }
    lt(c, v) { this.f.push((r) => r[c] < v); return this; }
    gte(c, v) { this.f.push((r) => r[c] >= v); return this; }
    in(c, vs) { this.f.push((r) => vs.some((v) => same(r[c], v))); return this; }
    like(c, pat) { const re = new RegExp("^" + pat.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/%/g, ".*") + "$"); this.f.push((r) => re.test(String(r[c] || ""))); return this; }
    order(c, o) { this.ord = [c, o && o.ascending === false ? -1 : 1]; return this; }
    range(a, b) { this.rng = [a, b]; return this; }
    maybeSingle() { this.one = true; return this; }
    then(res, rej) { return this.exec().then(res, rej); }
    async exec() {
      M.requests++;
      await sleep(M.delay);
      if (M.offline) return { data: null, error: { message: "TypeError: Failed to fetch", code: "" }, status: 0 };
      if (M.expired) return { data: null, error: { message: "JWT expired", code: "PGRST301" }, status: 401 };
      const authed = !!getSession();
      const match = () => tbl(this.t).filter((r) => this.f.every((fn) => fn(r)));
      const out = (rows, status) => {
        let d = rows.map((r) => Object.assign({}, r));
        if (this.ord) { const [c, dir] = this.ord; d.sort((a, b) => (a[c] > b[c] ? dir : a[c] < b[c] ? -dir : 0)); }
        if (this.rng) d = d.slice(this.rng[0], this.rng[1] + 1);
        return { data: this.one ? d[0] || null : d, error: null, status: status || 200 };
      };
      if (!authed) { // RLS „to authenticated": anonimul nu vede și nu modifică nimic — fără eroare
        if (this.op === "select" || this.op === "update" || this.op === "delete") return out([]);
        return { data: null, error: { message: "new row violates row-level security policy", code: "42501" }, status: 401 };
      }
      const now = new Date().toISOString();
      if (this.op === "select") return out(match());
      if (this.op === "update") {
        const rows = match();
        for (const r of rows) { const nr = Object.assign({}, r, this.payload); if (conflict(this.t, nr, r.id)) return { data: null, error: { message: "duplicate key value violates unique constraint", code: "23505" }, status: 409 }; }
        rows.forEach((r) => Object.assign(r, this.payload, { updated_at: now })); save(); return out(rows);
      }
      if (this.op === "delete") { const rows = match(), ids = new Set(rows.map((r) => r.id)); db.tables[this.t] = tbl(this.t).filter((r) => !ids.has(r.id)); save(); return out(rows); }
      const list = Array.isArray(this.payload) ? this.payload : [this.payload], made = [];
      for (const p of list) {
        const row = Object.assign({ id: db.seq++, created_at: now, updated_at: now }, defaults(this.t), p);
        const dup = conflict(this.t, row);
        if (dup && this.op === "upsert") { if (!this.opts.ignoreDuplicates) Object.assign(dup, p, { updated_at: now }); made.push(dup); continue; }
        if (dup) return { data: null, error: { message: "duplicate key value violates unique constraint", code: "23505" }, status: 409 };
        tbl(this.t).push(row); made.push(row);
      }
      save(); return out(made, 201);
    }
  }

  // ---- auth ----
  const listeners = [];
  function getSession() { if (M.loggedOut) return null; try { return JSON.parse(localStorage.getItem(SKEY)); } catch (e) { return null; } }
  const emit = (ev, s) => listeners.forEach((cb) => setTimeout(() => cb(ev, s), 0));
  M.signOutEvent = () => { localStorage.removeItem(SKEY); emit("SIGNED_OUT", null); };
  const auth = {
    async signInWithPassword({ email, password }) {
      await sleep(M.delay);
      if (!email || !password) return { data: {}, error: { message: "Invalid login credentials" } };
      const s = { access_token: "mock-token", user: { email } };
      localStorage.setItem(SKEY, JSON.stringify(s)); M.loggedOut = false; M.expired = false; emit("SIGNED_IN", s);
      return { data: { session: s, user: s.user }, error: null };
    },
    async getUser() { const s = getSession(); return { data: { user: s ? s.user : null }, error: null }; },
    async getSession() { return { data: { session: getSession() }, error: null }; },
    async refreshSession() { const s = getSession(); return s && !M.expired ? { data: { session: s }, error: null } : { data: { session: null }, error: { message: "Auth session missing!" } }; },
    async signOut() { localStorage.removeItem(SKEY); emit("SIGNED_OUT", null); return { error: null }; },
    onAuthStateChange(cb) { listeners.push(cb); setTimeout(() => cb("INITIAL_SESSION", getSession()), 0); return { data: { subscription: { unsubscribe() {} } } }; },
  };

  // ---- storage (backups) ----
  const files = {};
  const storage = { from() { return {
    async upload(name, blob) { files[name] = await blob.text(); return { data: { path: name }, error: null }; },
    async list() { return { data: Object.keys(files).sort().reverse().map((name) => ({ name })), error: null }; },
    async download(name) { return files[name] != null ? { data: new Blob([files[name]]), error: null } : { data: null, error: { message: "not found" } }; },
    async remove(names) { names.forEach((n) => delete files[n]); return { data: [], error: null }; },
  }; } };

  const client = {
    from: (t) => new Query(t), auth, storage,
    channel() { const ch = { on() { return ch; }, subscribe(cb) { if (cb) setTimeout(() => cb("SUBSCRIBED"), 0); return ch; } }; return ch; },
    removeChannel() {},
  };
  window.supabase = { createClient: () => client };
  console.warn("[mock] Supabase FALS activ — datele stau doar în acest browser (window.__mock)");
})();
