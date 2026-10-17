// Teste pentru logic.js — rulează cu: node logic.test.js
const L = require("./logic.js");
let fails = 0;
const eq = (a, b, msg) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) { console.error("FAIL:", msg, "\n  got:", JSON.stringify(a), "\n  exp:", JSON.stringify(b)); fails++; }
  else console.log("ok  -", msg);
};

// weekdays: iulie 2026 (1 iul = miercuri) → 23 zile lucrătoare, prima 01.07
eq(L.weekdays(2026, 7).length, 23, "iulie 2026 = 23 zile lucrătoare");
eq(L.weekdays(2026, 7).slice(0, 4), ["01.07", "02.07", "03.07", "06.07"], "iulie 2026 sare weekendul");

// rebalanceCZU
eq(L.rebalanceCZU([10, 20, 30], 30), [5, 10, 15], "rebalance 60→30 proporțional");
eq(L.rebalanceCZU([1, 1, 1], 30), [1, 1, 1], "fără rebalance sub total");
eq(L.rebalanceCZU([0, 0, 0], 0), [0, 0, 0], "rebalance total 0");

// genderSplit
eq(L.genderSplit(7), { f: 3, m: 4 }, "gen 7 → F3 M4 (impar la masculin)");
eq(L.genderSplit(0), { f: 0, m: 0 }, "gen 0");

// copiiSplit
eq(L.copiiSplit(2, 3, 0, "elevi"), { prescolari: 2, elevi: 3, copii_pana_16: 5 }, "copii: edit elevi → total");
eq(L.copiiSplit(2, 0, 5, "copii_pana_16"), { prescolari: 2, elevi: 3, copii_pana_16: 5 }, "copii: edit total → elevi");
eq(L.copiiSplit(4, 3, 5, "prescolari"), { prescolari: 4, elevi: 1, copii_pana_16: 5 }, "copii: edit preșcolari cu total>0");

// docLangSplit (Partea III): limba_romana = carti − alte_limbi
eq(L.docLangSplit(10, 0), { limba_romana: 10 }, "limbi: 10 cărți, 0 alte → 10 română");
eq(L.docLangSplit(10, 1), { limba_romana: 9 }, "limbi: 10 cărți, 1 altă → 9 română");
eq(L.docLangSplit(0, 0), { limba_romana: 0 }, "limbi: 0 cărți → 0 română");
eq(L.docLangSplit(3, 5), { limba_romana: 0 }, "limbi: alte > cărți → 0 română (fără negativ)");

// czuRemainder (Partea IV): 8 Limbi = Total − Σ(celelalte CZU)
eq(L.czuRemainder(10, [0, 0, 0, 0, 0, 0, 0, 0]), 10, "czu: total 10, fără altele → 10 la 8 Limbi");
eq(L.czuRemainder(10, [2, 0, 0, 1, 0, 0, 0, 0]), 7, "czu: total 10 − (2+1) → 7 la 8 Limbi");
eq(L.czuRemainder(10, [0, 0, 0, 12, 0, 0, 0, 0]), 0, "czu: altele > total → 0 (fără negativ)");
eq(L.czuRemainder(0, [0, 0, 0, 0, 0, 0, 0, 0]), 0, "czu: total 0 → 0");

// pairSplit (Partea IX): complement dintr-un total
eq(L.pairSplit(12, 5, 0, "f"), { f: 5, m: 7 }, "pair: 5 fete din 12 → 7 băieți");
eq(L.pairSplit(12, 0, 5, "m"), { f: 7, m: 5 }, "pair: 5 băieți din 12 → 7 fete");
eq(L.pairSplit(12, 2, 0, "f"), { f: 2, m: 10 }, "pair: 2 preșcolari din 12 → 10 elevi");
eq(L.pairSplit(12, 15, 0, "f"), { f: 15, m: 0 }, "pair: membru > total → complement 0 (fără negativ)");

// sumCols
eq(L.sumCols([["a", "A", "int"], ["b", "B", "bool", { ct: true }], ["t", "T", "text"]],
  [{ a: 2, b: true, t: "x" }, { a: 3, b: false, t: "" }]), { a: 5, b: 1 }, "sumCols: int sumă, bool ct = nr bifate");

// backupsToDelete — retenție pe niveluri
{
  const now = new Date(2026, 9, 17, 12, 0, 0); // 17 oct 2026
  const pad = (n) => String(n).padStart(2, "0");
  const name = (y, m, d, h) => `registru_${y}-${pad(m)}-${pad(d)}_${pad(h)}0000.json`;
  const all = [];
  for (let d = 1; d <= 17; d++) for (let h = 8; h <= 17; h++) all.push(name(2026, 10, d, h)); // 10/zi în octombrie
  for (let d = 1; d <= 30; d++) all.push(name(2026, 9, d, 9), name(2026, 9, d, 15));          // 2/zi în septembrie
  for (let m = 1; m <= 8; m++) for (let d = 1; d <= 3; d++) all.push(name(2026, m, d, 10));  // ian–aug
  all.push("registru_backup.json", "registru_inainte-de-restaurare_2026-10-01_100000.json");
  const del = new Set(L.backupsToDelete(all, now)), kept = all.filter((n) => !del.has(n));
  // ultimele 24 = 17 oct (10) + 16 oct (10) + 15 oct orele 14–17 (4)
  eq(kept.includes(name(2026, 10, 17, 17)) && kept.includes(name(2026, 10, 15, 14)) && !kept.includes(name(2026, 10, 15, 13)), true, "retenție: exact ultimele 24 copii păstrate");
  eq(kept.includes(name(2026, 10, 3, 17)) && !kept.includes(name(2026, 10, 3, 9)), true, "retenție: din zilele mai vechi rămâne cea mai nouă copie a zilei");
  eq(kept.includes(name(2026, 9, 20, 15)) && !kept.includes(name(2026, 9, 20, 9)), true, "retenție: o copie/zi în ultimele 31 de zile");
  eq(kept.includes(name(2026, 9, 10, 15)), false, "retenție: zilele de peste 31 de zile nu se mai păstrează zilnic…");
  eq(kept.includes(name(2026, 9, 30, 15)), true, "…dar ultima copie a lunii septembrie rămâne");
  eq([1, 2, 3, 4, 5, 6, 7, 8].every((m) => kept.includes(name(2026, m, 3, 10))), true, "retenție: câte o copie pe lună, pentru totdeauna");
  eq(kept.includes("registru_backup.json") && kept.includes("registru_inainte-de-restaurare_2026-10-01_100000.json"), true, "retenție: alte fișiere nu sunt șterse niciodată");
  eq(kept.length < 90, true, "retenție: numărul de copii rămâne mic (" + kept.length + ")");
}

// normDate — date scrise de om → ZZ.LL
eq(L.normDate("5", 2026, 10), { value: "05.10", month: 10 }, "data: doar ziua → luna curentă");
eq(L.normDate("5.3", 2026, 10), { value: "05.03", month: 3 }, "data: 5.3 → 05.03");
eq(L.normDate("05/10", 2026, 1).value, "05.10", "data: slash");
eq(L.normDate(" 7-11-2026 ", 2026, 1).value, "07.11", "data: cu an și spații");
eq(L.normDate("01.10.", 2026, 1).value, "01.10", "data: punct final");
eq(L.normDate("", 2026, 10), { value: "" }, "data: goală rămâne goală");
eq(L.normDate("31.02", 2026, 2).error, "ziua", "data: 31 februarie e invalidă");
eq(L.normDate("29.02", 2028, 2).value, "29.02", "data: 29 februarie în an bisect");
eq(L.normDate("29.02", 2026, 2).error, "ziua", "data: 29 februarie în an nebisect");
eq(L.normDate("12.13", 2026, 1).error, "luna", "data: luna 13");
eq(L.normDate("ieri", 2026, 1).error, "format", "data: text oarecare");

// snapshotLooksWrong — gardă împotriva copiilor goale
eq(L.snapshotLooksWrong(0, 5000), true, "copie goală după una plină = suspectă");
eq(L.snapshotLooksWrong(2000, 5000), true, "copie la sub jumătate = suspectă");
eq(L.snapshotLooksWrong(4800, 5000), false, "câteva rânduri șterse = normal");
eq(L.snapshotLooksWrong(0, 0), false, "registru nou, gol = normal");
eq(L.snapshotLooksWrong(10, null), false, "prima copie = normal");

if (fails) { console.error("\n" + fails + " test(e) eșuate"); process.exit(1); }
console.log("\nTOATE TESTELE AU TRECUT");
