// Teste pentru outbox.js — rulează cu: node outbox.test.js
const O = require("./outbox.js");
let fails = 0;
const eq = (a, b, msg) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) { console.error("FAIL:", msg, "\n  got:", JSON.stringify(a), "\n  exp:", JSON.stringify(b)); fails++; }
  else console.log("ok  -", msg);
};
function memStorage() { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, _m: m }; }

(async () => {
  // put + combinare câmpuri + persistență
  const st = memStorage(), q = O.create(st, "ob");
  q.put("instruiri", 5, { elevi: 1 });
  q.put("instruiri", 5, { elevi: 12, total_participanti: 14 });
  q.put("voluntariat", 2, { numar_ore: 3 });
  eq(q.size(), 2, "două rânduri în coadă (același rând combinat)");
  eq(q.pending("instruiri", 5), { elevi: 12, total_participanti: 14 }, "valoarea cea mai nouă câștigă");
  eq(O.create(st, "ob").pending("instruiri", 5), { elevi: 12, total_participanti: 14 }, "coada supraviețuiește „reîncărcării paginii”");

  // flush ok → coada se golește
  const sent = [];
  let r = await q.flush(async (t, id, f) => { sent.push([t, id, f]); return "ok"; });
  eq(r.sent, 2, "flush trimite ambele rânduri");
  eq(q.size(), 0, "după confirmare coada e goală");
  eq(O.create(st, "ob").size(), 0, "golirea e persistată");

  // rețea căzută → rămâne totul în coadă, se oprește la primul eșec
  q.put("a", 1, { x: 1 }); q.put("a", 2, { x: 2 });
  let calls = 0;
  r = await q.flush(async () => { calls++; return "retry"; });
  eq([r.stopped, r.left, calls], ["retry", 2, 1], "fără rețea: nimic pierdut, nu insistă");

  // sesiune expirată → oprește cu "auth", păstrează
  r = await q.flush(async () => "auth");
  eq([r.stopped, r.left], ["auth", 2], "sesiune expirată: păstrează coada");

  // excepție în send = retry
  r = await q.flush(async () => { throw new Error("Failed to fetch"); });
  eq([r.stopped, r.left], ["retry", 2], "excepție de rețea tratată ca reîncercare");

  // eroare permanentă → scos din coadă și raportat
  r = await q.flush(async (t, id) => (id === 1 ? { drop: "valoare invalidă" } : "ok"));
  eq([r.dropped.length, r.dropped[0].reason, r.left], [1, "valoare invalidă", 0], "eroare permanentă raportată, coada continuă");

  // editare în timpul trimiterii → rândul rămâne în coadă cu valoarea nouă
  q.put("a", 9, { x: 1 });
  r = await q.flush(async () => { q.put("a", 9, { x: 2 }); return "ok"; });
  eq(q.pending("a", 9), { x: 2 }, "editarea din timpul trimiterii nu se pierde");
  await q.flush(async () => "ok");
  eq(q.size(), 0, "a doua trimitere o confirmă");

  // flush-uri simultane → nu trimit de două ori în paralel
  q.put("a", 1, { x: 1 });
  let inFlight = 0, maxInFlight = 0;
  const slow = async () => { inFlight++; maxInFlight = Math.max(maxInFlight, inFlight); await new Promise((res) => setTimeout(res, 10)); inFlight--; return "ok"; };
  await Promise.all([q.flush(slow), q.flush(slow), q.flush(slow)]);
  eq([maxInFlight, q.size()], [1, 0], "flush-uri suprapuse rulează pe rând");

  // localStorage stricat → pornește gol, nu crapă
  const bad = memStorage(); bad.setItem("ob", "{nu e json");
  eq(O.create(bad, "ob").size(), 0, "date corupte în localStorage → coadă goală, fără crash");

  // classify
  eq(O.classify(null, 200, 1), "ok", "1 rând modificat = ok");
  eq(O.classify(null, 200, 0), "none", "0 rânduri = sesiune pierdută sau rând șters");
  eq(O.classify({ message: "JWT expired", code: "PGRST301" }, 401, 0), "auth", "JWT expirat = auth");
  eq(O.classify({ message: "TypeError: Failed to fetch", code: "" }, 0, 0), "retry", "rețea = retry");
  eq(O.classify({ message: "upstream", code: "" }, 503, 0), "retry", "503 = retry");
  eq(O.classify({ message: "duplicate key", code: "23505" }, 409, 0), { drop: "duplicate key" }, "constrângere = permanent");
  eq(O.classify({ message: "invalid input", code: "22P02" }, 400, 0), { drop: "invalid input" }, "tip greșit = permanent");

  if (fails) { console.error(`\n${fails} TESTE AU EȘUAT`); process.exit(1); }
  console.log("\nTOATE TESTELE OUTBOX AU TRECUT");
})();
