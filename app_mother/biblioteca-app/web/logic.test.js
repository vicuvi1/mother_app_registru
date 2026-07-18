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

if (fails) { console.error("\n" + fails + " test(e) eșuate"); process.exit(1); }
console.log("\nTOATE TESTELE AU TRECUT");
