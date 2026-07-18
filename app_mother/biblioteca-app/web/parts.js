// ============================================================================
// Definiția tuturor părților registrului (I–VII, IX, XI–XIV).
// Metadate portate 1:1 din aplicația desktop (ColumnDef): grupuri de antet,
// coloane calculate (sum), super-grup (Partea IX), cumulativ, validări.
//
// col: [key, label, type, opts?]
//   type: "int" | "text" | "txt" | "bool" | "date" | "staff"
//   opts: { req, g:group, sg:super_group, sum:[keys] (auto = Σ), ro:true (read-only/calc),
//           ct:true (bool numărat în „Total") }
//
// part: { key, nr, title, period, categorie, dateField, cumulative, cols, extra? }
//   period: "zi" | "lista" | "luna" | "crud"
//   cumulative: adaugă rând „Total de la început" (I,II,III,IV,V,VI,IX,XI,XII)
//   orderById: afișează rândurile în ordinea adăugării (după id), nu după dată —
//     rândurile noi se adaugă la sfârșit (jos), fiindcă userul completează de sus în jos
//   extra: { adulti:[...], copii:[...] } — coloane specifice tab-ului (Partea IX)
// ============================================================================
(function () {
  const G1 = "Utilizatori activi", GSOC = "După statutul ocupației și social",
    GVAR = "După vârstă", GSEXC = "După sex copii 16 ani", GSEXA = "După sex adulți",
    GDIN = "Din care", GDOC = "După categorii de documente", GLIMBI = "După limbi",
    GCZU = "După conținut (CZU)", GSOCIAL = "Indicatori ai rețelelor sociale";

  const PARTS = [
    {
      key: "evidenta_utilizatori", nr: "I", title: "Evidența utilizatorilor",
      period: "zi", categorie: false, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        ["adulti", "Adulți", "int", { g: G1 }], ["copii_pana_16", "Copii ≤16", "int", { g: G1 }],
        ["prescolari", "Preșcolari", "int", { g: GSOC }], ["elevi", "Elevi", "int", { g: GSOC }],
        ["studenti", "Studenți", "int", { g: GSOC }], ["intelectuali", "Intelectuali", "int", { g: GSOC }],
        ["muncitori", "Muncitori", "int", { g: GSOC }], ["pensionari", "Pensionari", "int", { g: GSOC }],
        ["someri", "Șomeri", "int", { g: GSOC }], ["alte_categorii", "Alte categorii", "int", { g: GSOC }],
        ["tineri_17_34", "17-34 ani", "int", { g: GVAR }], ["adulti_35_64", "35-64 ani", "int", { g: GVAR }],
        ["varstnici_65_plus", "65+ ani", "int", { g: GVAR }],
        ["sex_copii_f", "Fete", "int", { g: GSEXC }], ["sex_copii_m", "Băieți", "int", { g: GSEXC }],
        ["sex_adulti_f", "Femei", "int", { g: GSEXA }], ["sex_adulti_m", "Bărbați", "int", { g: GSEXA }],
      ],
    },
    {
      key: "evidenta_utilizatori_copii_adulti", nr: "II",
      title: "Evidența utilizatorilor (copii / adulți)",
      period: "zi", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        ["intrari_total_zi", "Intrări/zi", "int", { ro: true, sum: ["imprumut_carti", "sedinte_calculatoare", "activitati_culturale_stiintifice", "instruiri", "alte_scopuri_excursii"] }],
        ["imprumut_carti", "Împrumut cărți", "int", { g: GDIN }],
        ["sedinte_calculatoare", "Ședințe calc.", "int", { g: GDIN }],
        // Sincronizate bidirecțional cu Partea XI / IX (editabile aici)
        ["activitati_culturale_stiintifice", "Act. cult./șt.", "int", { g: GDIN, rev: "xi" }],
        ["instruiri", "Instruiri", "int", { g: GDIN, rev: "ix" }],
        ["alte_scopuri_excursii", "Alte scopuri", "int", { g: GDIN }],
        ["vizite_virtuale_total", "Total", "int", { ro: true, g: "Vizite virtuale", sum: ["vizite_virtuale_pagina_web", "vizite_virtuale_blog"] }],
        ["vizite_virtuale_pagina_web", "Pagină web", "int", { g: "Vizite virtuale" }],
        ["vizite_virtuale_blog", "Blog", "int", { g: "Vizite virtuale" }],
        ["vizitatori_virtuali_total", "Total", "int", { ro: true, g: "Vizitatori virtuali", sum: ["vizitatori_virtuali_pagina_web", "vizitatori_virtuali_blog"] }],
        ["vizitatori_virtuali_pagina_web", "Pagină web", "int", { g: "Vizitatori virtuali" }],
        ["vizitatori_virtuali_blog", "Blog", "int", { g: "Vizitatori virtuali" }],
        ["facebook_vizualizari", "FB vizualizări", "int", { g: GSOCIAL }], ["facebook_impact", "FB impact", "int", { g: GSOCIAL }],
        ["facebook_interactiuni", "FB interacț.", "int", { g: GSOCIAL }],
        ["instagram_vizualizari", "IG vizualizări", "int", { g: GSOCIAL }], ["instagram_impact", "IG impact", "int", { g: GSOCIAL }],
        ["instagram_interactiuni", "IG interacț.", "int", { g: GSOCIAL }],
        ["twitter_vizualizari", "TW vizualizări", "int", { g: GSOCIAL }], ["twitter_impact", "TW impact", "int", { g: GSOCIAL }],
        ["twitter_interactiuni", "TW interacț.", "int", { g: GSOCIAL }],
      ],
    },
    {
      key: "documente_inregistrate", nr: "III", title: "Documente înregistrate",
      period: "zi", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        ["total_imprumuturi", "Total împrumuturi", "int", { ro: true, sum: ["consultare_pe_loc", "imprumut_pe_loc", "imprumut_la_domiciliu", "imprumut_inter_bibliotecar"] }],
        ["consultare_pe_loc", "Consultare pe loc", "int", { g: GDIN }],
        ["imprumut_pe_loc", "Împrumut pe loc", "int", { g: GDIN }],
        ["imprumut_la_domiciliu", "Împrumut domiciliu", "int", { g: GDIN }],
        ["imprumut_inter_bibliotecar", "Împrumut interbibl.", "int", { g: GDIN }],
        ["carti", "Cărți", "int", { g: GDOC }], ["publicatii_seriale", "Publicații seriale", "int", { g: GDOC }],
        ["documente_muzica", "Doc. muzică", "int", { g: GDOC }],
        ["documente_audiovizuale", "Doc. audiovizuale", "int", { g: GDOC }],
        ["documente_electronice_cd_dvd", "Doc. CD/DVD", "int", { g: GDOC }],
        ["alte_documente", "Alte documente", "int", { g: GDOC }],
        // „Limba română" = „Cărți" − „Alte limbi" (calculat automat, vezi deriveRow)
        ["limba_romana", "Limba română", "int", { g: GLIMBI, ro: true }], ["alte_limbi", "Alte limbi", "int", { g: GLIMBI }],
      ],
    },
    {
      key: "documente_continut_czu", nr: "IV", title: "Documente după conținut (CZU)",
      period: "zi", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        // total_imprumuturi se preia implicit din Partea III (zilnic); editabil dacă lipsește Partea III
        ["total_imprumuturi", "Total împrumuturi", "int"],
        ["czu_0_generalitati", "0 Generalități", "int", { g: GCZU }], ["czu_1_filozofie", "1 Filozofie", "int", { g: GCZU }],
        ["czu_2_religie", "2 Religie", "int", { g: GCZU }], ["czu_3_stiinte_sociale", "3 Șt. sociale", "int", { g: GCZU }],
        ["czu_5_matematica", "5 Matematică", "int", { g: GCZU }], ["czu_6_stiinte_aplicate", "6 Șt. aplicate", "int", { g: GCZU }],
        // „8 Limbi" (literatură) = Total − Σ(celelalte categorii CZU) — categoria-rest (calculat automat, read-only)
        ["czu_7_arte", "7 Arte", "int", { g: GCZU }], ["czu_8_limbi", "8 Limbi", "int", { g: GCZU, ro: true }],
        ["czu_9_geografie", "9 Geografie/Istorie", "int", { g: GCZU }],
      ],
    },
    {
      key: "cercetari_bibliografice", nr: "V", title: "Cercetări bibliografice",
      period: "lista", categorie: true, dateField: "data_primirii_cererii", cumulative: true,
      cols: [
        ["data_primirii_cererii", "Data cererii", "date", { req: true }],
        ["total_referinte", "Total referințe", "int"],
        ["date_despre_solicitant", "Solicitant", "text"],
        ["statut_socio_profesional", "Statut socio-prof.", "text"],
        ["referinta", "Referință", "txt"],
        ["cercetare_bibliografica", "Cercetare bibl.", "text", { g: "Tema (titlul)" }],
        ["consultatie", "Consultație", "text", { g: "Tema (titlul)" }],
        ["referinta_tematica", "Tematică", "text", { g: "Tip de referință bibliografică" }],
        ["referinta_de_concretizare", "Concretizare", "text", { g: "Tip de referință bibliografică" }],
        ["referinta_de_adresa", "Adresă", "text", { g: "Tip de referință bibliografică" }],
        ["referinta_factologie", "Factologie", "text", { g: "Tip de referință bibliografică" }],
        ["limite_cronologice", "Limite cronologice", "text"],
        ["surse_consultatie", "Surse consultație", "int"],
        ["numar_descrieri_bibliografice", "Nr. descrieri", "int"],
        ["surse_recomandate", "Surse recomandate", "int"],
        ["data_finalizarii_cererii", "Data finalizării", "date"],
        ["responsabil", "Responsabil", "staff"],
      ],
    },
    {
      key: "activitati_informare", nr: "VI", title: "Activități de informare",
      period: "lista", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["grup_tinta_subiect", "Grup țintă / subiect", "text"],
        ["activitate_individuala", "Individuală", "text", { g: "Gen de activitate" }],
        ["activitate_grup", "Grup", "text", { g: "Gen de activitate" }],
        ["activitate_public_larg", "Public larg", "text", { g: "Gen de activitate" }],
        ["numar_participanti", "Nr. participanți", "int", { g: "Număr participanți" }],
        ["participanti_masculin", "Masculin", "int", { g: "Număr participanți" }],
        ["participanti_feminin", "Feminin", "int", { g: "Număr participanți" }],
        ["documente_consultate", "Doc. consultate", "int"],
        ["responsabil", "Responsabil", "staff"],
      ],
      split: { total: "numar_participanti", m: "participanti_masculin", f: "participanti_feminin" },
    },
    {
      key: "documente_electronice", nr: "VII", title: "Documente electronice online",
      period: "luna", categorie: true, dateField: null, cumulative: false,
      cols: [
        ["luna", "Luna", "monthlabel"],
        ["total_documente_electronice", "Total doc. electronice", "int"],
        ["mediu_email", "Prin email", "int", { g: "Mediu furnizare" }],
        ["mediu_skype_retele_sociale", "Skype/rețele sociale", "int", { g: "Mediu furnizare" }],
        ["carti", "Cărți", "int", { g: GDOC }], ["publicatii_seriale", "Publicații seriale", "int", { g: GDOC }],
        ["documente_muzica", "Doc. muzică", "int", { g: GDOC }],
        ["documente_audiovizuale", "Doc. audiovizuale", "int", { g: GDOC }],
        ["documente_electronice_cd_dvd", "Doc. CD/DVD", "int", { g: GDOC }],
        ["alte_documente", "Alte documente", "int", { g: GDOC }],
        // „Limba română" = „Cărți" − „Alte limbi" (calculat automat, vezi deriveRow)
        ["limba_romana", "Limba română", "int", { g: GLIMBI, ro: true }], ["alte_limbi", "Alte limbi", "int", { g: GLIMBI }],
      ],
    },
    {
      key: "instruiri", nr: "IX", title: "Instruirea utilizatorilor",
      period: "lista", categorie: true, dateField: "data", cumulative: true, orderById: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        ["format_online", "Online", "bool", { g: "Formatul instruirii", ct: true }],
        ["format_offline", "Offline", "bool", { g: "Formatul instruirii", ct: true }],
        ["forma_formala", "Formală", "bool", { g: "Forma de instruire continuă", ct: true }],
        ["ore_formala", "Ore", "int", { g: "Forma de instruire continuă" }],
        ["forma_non_formala", "Non-formală", "bool", { g: "Forma de instruire continuă", ct: true }],
        ["ore_non_formala", "Ore", "int", { g: "Forma de instruire continuă" }],
        ["forma_informala", "Informală", "bool", { g: "Forma de instruire continuă", ct: true }],
        ["tema_instruirii", "Tema instruirii", "txt"], ["formator", "Formator", "staff"],
      ],
      extra: {
        adulti: [
          ["total_participanti", "Total", "int", { g: "Total participanți", sg: "Participanți" }],
          ["studenti", "Studenți", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["intelectuali", "Intelectuali", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["pensionari", "Pensionari", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["someri", "Șomeri", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["muncitori", "Muncitori", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["alte_categorii", "Alte", "int", { g: "După statutul ocupației", sg: "Participanți" }],
          ["tineri_17_34", "17-34", "int", { g: "După vârstă", sg: "Participanți" }],
          ["adulti_35_64", "35-64", "int", { g: "După vârstă", sg: "Participanți" }],
          ["varstnici_65_plus", "65+", "int", { g: "După vârstă", sg: "Participanți" }],
          ["participanti_feminin", "Femei", "int", { g: "Maturi după sex", sg: "Participanți" }],
          ["participanti_masculin", "Bărbați", "int", { g: "Maturi după sex", sg: "Participanți" }],
        ],
        copii: [
          ["total_participanti", "Total", "int", { g: "Total participanți", sg: "Participanți" }],
          ["prescolari", "Preșcolari", "int", { g: "Copii", sg: "Participanți" }],
          // Elevi = Total − Preșcolari (restul copiilor sunt elevi; calculat automat, read-only)
          ["elevi", "Elevi", "int", { g: "Copii", sg: "Participanți", ro: true }],
          ["participanti_feminin", "Fete", "int", { g: "Copii ≤16 după sex", sg: "Participanți" }],
          ["participanti_masculin", "Băieți", "int", { g: "Copii ≤16 după sex", sg: "Participanți" }],
        ],
      },
      // Split pe sex bidirecțional: editezi Fete/Băieți → celălalt = Total − acela (ambele tab-uri)
      split: { total: "total_participanti", m: "participanti_masculin", f: "participanti_feminin", bidir: true },
    },
    {
      key: "activitati_culturale", nr: "XI", title: "Activități culturale și științifice",
      period: "lista", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date"],
        ["total_activitati", "Total activități", "int", { g: "Total număr" }],
        ["din_care_expozitii", "Din care expoziții", "int", { g: "Total număr" }],
        ["tipul_activitatii", "Tipul activității", "text"],
        ["denumirea_activitatii", "Denumirea activității", "txt"],
        ["total_participanti", "Total", "int", { g: "Număr participanți" }],
        ["participanti_masculin", "Masculin", "int", { g: "Număr participanți" }],
        ["participanti_feminin", "Feminin", "int", { g: "Număr participanți" }],
      ],
      // Split pe sex bidirecțional (ca Partea IX): editezi Masculin/Feminin → celălalt = Total − acela
      split: { total: "total_participanti", m: "participanti_masculin", f: "participanti_feminin", bidir: true },
    },
    {
      key: "activitati_online", nr: "XII", title: "Activități culturale online",
      period: "lista", categorie: true, dateField: "data", cumulative: true,
      cols: [
        ["data", "Data", "date", { req: true }],
        ["denumirea_activitatii", "Denumirea activității", "txt"],
        ["tipul_activitatii", "Tipul activității", "text"],
        ["platforma", "Platforma", "text"],
        ["vizualizari", "Vizualizări", "int"], ["impact", "Impact", "int"],
        ["participanti_total", "Total", "int", { g: "Participanți" }],
        ["participanti_masculin", "Masculin", "int", { g: "Participanți" }],
        ["participanti_feminin", "Feminin", "int", { g: "Participanți" }],
      ],
    },
    {
      key: "parteneri", nr: "XIII", title: "Parteneri",
      period: "crud", categorie: false, dateField: null, cumulative: false,
      cols: [
        ["partener", "Partener", "text", { req: true }],
        ["scope_local", "Local", "bool", { g: "Aria", ct: true }],
        ["scope_national", "Național", "bool", { g: "Aria", ct: true }],
        ["scope_international", "Internațional", "bool", { g: "Aria", ct: true }],
        ["date_contact", "Date contact", "text"],
        ["tip_contract", "Tip contract", "text"],
        ["data_semnarii", "Data semnării", "text"],
        ["termen_realizare", "Termen realizare", "text"],
        ["modalitati_realizare", "Modalități realizare", "txt"],
        ["participanti_total", "Total particip.", "int"],
        ["participanti_adulti", "Adulți", "int"], ["participanti_copii", "Copii", "int"],
        ["impact", "Impact", "int"],
      ],
    },
    {
      key: "voluntariat", nr: "XIV", title: "Voluntariat",
      period: "crud", categorie: false, dateField: null, cumulative: false,
      cols: [
        ["nume_prenume", "Nume și prenume", "text", { req: true }],
        ["nr_contract", "Nr. contract", "text"],
        ["data_inceperii", "Data începerii", "text"],
        ["data_incheierii", "Data încheierii", "text"],
        ["numar_ore", "Număr ore", "int"],
        ["activitati_realizate", "Activități realizate", "txt"],
        ["coordonator", "Coordonator", "staff"],
      ],
    },
  ];

  // Părți cu validare „activități/zi" (max 5); restul cu coloane int au max 30.
  const MAX5 = new Set(["cercetari_bibliografice", "activitati_informare", "instruiri",
    "activitati_culturale", "activitati_online"]);

  // Coloanele efective ale unei părți pentru o categorie (Partea IX diferă pe tab).
  function partCols(part, cat) {
    if (part.extra) return part.cols.concat(part.extra[cat] || part.extra.copii || []);
    return part.cols;
  }

  // part_id ca în desktop (pentru etichete_custom / text_presets compatibile la migrare)
  const PID = { I: "part_01", II: "part_02", III: "part_03", IV: "part_04", V: "part_05",
    VI: "part_06", VII: "part_07", IX: "part_09", XI: "part_11", XII: "part_12",
    XIII: "part_13", XIV: "part_14" };
  PARTS.forEach((p) => (p.pid = PID[p.nr]));

  window.REGISTRU_PARTS = PARTS;
  window.REGISTRU_MAX5 = MAX5;
  window.partCols = partCols;
})();
