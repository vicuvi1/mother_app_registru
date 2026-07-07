// ============================================================================
// Definiția tuturor părților registrului (I–VII, IX, XI–XIV).
// Motorul (app.js) construiește tabelele editabile din aceste definiții.
//
// col: [key, label, type, opts?]
//   type: "int" | "text" | "txt" (text lung) | "bool" | "date" | "staff"
//   opts: { req:true (obligatoriu la inserare) }
//
// period: "zi"    -> an, luna + coloana de dată per rând (mai multe zile)
//         "lista" -> an, luna + mai multe rânduri (evenimente/cereri)
//         "luna"  -> an, luna (+ categorie) — un rând pe lună
//         "crud"  -> listă independentă (fără an/lună)
// categorie: true -> filtrare/împărțire pe "copii" / "adulti"
// dateField: coloana de dată obligatorie folosită la inserarea unui rând nou
// ============================================================================
(function () {
  const PARTS = [
    {
      key: "evidenta_utilizatori", nr: "I", title: "Evidența utilizatorilor",
      period: "zi", categorie: false, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["adulti", "Adulți", "int"], ["copii_pana_16", "Copii ≤16", "int"],
        ["prescolari", "Preșcolari", "int"], ["elevi", "Elevi", "int"],
        ["studenti", "Studenți", "int"], ["intelectuali", "Intelectuali", "int"],
        ["muncitori", "Muncitori", "int"], ["pensionari", "Pensionari", "int"],
        ["someri", "Șomeri", "int"], ["alte_categorii", "Alte categorii", "int"],
        ["tineri_17_34", "17-34 ani", "int"], ["adulti_35_64", "35-64 ani", "int"],
        ["varstnici_65_plus", "65+ ani", "int"],
        ["sex_copii_f", "Copii F", "int"], ["sex_copii_m", "Copii M", "int"],
        ["sex_adulti_f", "Adulți F", "int"], ["sex_adulti_m", "Adulți M", "int"],
      ],
    },
    {
      key: "evidenta_utilizatori_copii_adulti", nr: "II",
      title: "Evidența utilizatorilor (copii / adulți)",
      period: "zi", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["intrari_total_zi", "Intrări/zi", "int"], ["imprumut_carti", "Împrumut cărți", "int"],
        ["sedinte_calculatoare", "Ședințe calc.", "int"],
        ["activitati_culturale_stiintifice", "Act. cult./șt.", "int"],
        ["instruiri", "Instruiri", "int"], ["alte_scopuri_excursii", "Alte scopuri", "int"],
        ["vizite_virtuale_total", "Vizite virt. total", "int"],
        ["vizite_virtuale_pagina_web", "Vizite web", "int"],
        ["vizite_virtuale_blog", "Vizite blog", "int"],
        ["vizitatori_virtuali_total", "Vizitatori virt.", "int"],
        ["vizitatori_virtuali_pagina_web", "Vizitatori web", "int"],
        ["vizitatori_virtuali_blog", "Vizitatori blog", "int"],
        ["facebook_vizualizari", "FB vizualizări", "int"], ["facebook_impact", "FB impact", "int"],
        ["facebook_interactiuni", "FB interacț.", "int"],
        ["instagram_vizualizari", "IG vizualizări", "int"], ["instagram_impact", "IG impact", "int"],
        ["instagram_interactiuni", "IG interacț.", "int"],
        ["twitter_vizualizari", "TW vizualizări", "int"], ["twitter_impact", "TW impact", "int"],
        ["twitter_interactiuni", "TW interacț.", "int"],
      ],
    },
    {
      key: "documente_inregistrate", nr: "III", title: "Documente înregistrate",
      period: "zi", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["total_imprumuturi", "Total împrumuturi", "int"],
        ["consultare_pe_loc", "Consultare pe loc", "int"],
        ["imprumut_pe_loc", "Împrumut pe loc", "int"],
        ["imprumut_la_domiciliu", "Împrumut domiciliu", "int"],
        ["imprumut_inter_bibliotecar", "Împrumut interbibl.", "int"],
        ["carti", "Cărți", "int"], ["publicatii_seriale", "Publicații seriale", "int"],
        ["documente_muzica", "Doc. muzică", "int"],
        ["documente_audiovizuale", "Doc. audiovizuale", "int"],
        ["documente_electronice_cd_dvd", "Doc. CD/DVD", "int"],
        ["alte_documente", "Alte documente", "int"],
        ["limba_romana", "Limba română", "int"], ["alte_limbi", "Alte limbi", "int"],
      ],
    },
    {
      key: "documente_continut_czu", nr: "IV", title: "Documente după conținut (CZU)",
      period: "zi", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["total_imprumuturi", "Total împrumuturi", "int"],
        ["czu_0_generalitati", "0 Generalități", "int"], ["czu_1_filozofie", "1 Filozofie", "int"],
        ["czu_2_religie", "2 Religie", "int"], ["czu_3_stiinte_sociale", "3 Șt. sociale", "int"],
        ["czu_5_matematica", "5 Matematică", "int"], ["czu_6_stiinte_aplicate", "6 Șt. aplicate", "int"],
        ["czu_7_arte", "7 Arte", "int"], ["czu_8_limbi", "8 Limbi", "int"],
        ["czu_9_geografie", "9 Geografie/Istorie", "int"],
      ],
    },
    {
      key: "cercetari_bibliografice", nr: "V", title: "Cercetări bibliografice",
      period: "lista", categorie: true, dateField: "data_primirii_cererii",
      cols: [
        ["data_primirii_cererii", "Data cererii", "date", { req: true }],
        ["total_referinte", "Total referințe", "int"],
        ["date_despre_solicitant", "Solicitant", "text"],
        ["statut_socio_profesional", "Statut socio-prof.", "text"],
        ["referinta", "Referință", "txt"],
        ["cercetare_bibliografica", "Cercetare bibl.", "text"],
        ["consultatie", "Consultație", "text"],
        ["referinta_tematica", "Ref. tematică", "text"],
        ["referinta_de_concretizare", "Ref. concretizare", "text"],
        ["referinta_de_adresa", "Ref. adresă", "text"],
        ["referinta_factologie", "Ref. factologie", "text"],
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
      period: "lista", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["grup_tinta_subiect", "Grup țintă / subiect", "text"],
        ["activitate_individuala", "Act. individuală", "text"],
        ["activitate_grup", "Act. grup", "text"],
        ["activitate_public_larg", "Act. public larg", "text"],
        ["numar_participanti", "Nr. participanți", "int"],
        ["participanti_masculin", "Masculin", "int"],
        ["participanti_feminin", "Feminin", "int"],
        ["documente_consultate", "Doc. consultate", "int"],
        ["responsabil", "Responsabil", "staff"],
      ],
    },
    {
      key: "documente_electronice", nr: "VII", title: "Documente electronice online",
      period: "luna", categorie: true, dateField: null,
      cols: [
        ["total_documente_electronice", "Total doc. electronice", "int"],
        ["mediu_email", "Prin email", "int"],
        ["mediu_skype_retele_sociale", "Skype/rețele sociale", "int"],
        ["carti", "Cărți", "int"], ["publicatii_seriale", "Publicații seriale", "int"],
        ["documente_muzica", "Doc. muzică", "int"],
        ["documente_audiovizuale", "Doc. audiovizuale", "int"],
        ["documente_electronice_cd_dvd", "Doc. CD/DVD", "int"],
        ["alte_documente", "Alte documente", "int"],
        ["limba_romana", "Limba română", "int"], ["alte_limbi", "Alte limbi", "int"],
      ],
    },
    {
      key: "instruiri", nr: "IX", title: "Instruiri",
      period: "lista", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["format_online", "Online", "bool"], ["format_offline", "Offline", "bool"],
        ["forma_formala", "Formală", "bool"], ["ore_formala", "Ore formală", "int"],
        ["forma_non_formala", "Non-formală", "bool"], ["ore_non_formala", "Ore non-form.", "int"],
        ["forma_informala", "Informală", "bool"], ["ore_informala", "Ore informală", "int"],
        ["tema_instruirii", "Tema instruirii", "txt"], ["formator", "Formator", "staff"],
        ["total_participanti", "Total particip.", "int"],
        ["prescolari", "Preșcolari", "int"], ["elevi", "Elevi", "int"],
        ["studenti", "Studenți", "int"], ["intelectuali", "Intelectuali", "int"],
        ["pensionari", "Pensionari", "int"], ["someri", "Șomeri", "int"],
        ["muncitori", "Muncitori", "int"], ["alte_categorii", "Alte categorii", "int"],
        ["tineri_17_34", "17-34 ani", "int"], ["adulti_35_64", "35-64 ani", "int"],
        ["varstnici_65_plus", "65+ ani", "int"],
        ["participanti_feminin", "Feminin", "int"], ["participanti_masculin", "Masculin", "int"],
      ],
    },
    {
      key: "activitati_culturale", nr: "XI", title: "Activități culturale și științifice",
      period: "lista", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date"],
        ["total_activitati", "Total activități", "int"],
        ["din_care_expozitii", "Din care expoziții", "int"],
        ["tipul_activitatii", "Tipul activității", "text"],
        ["denumirea_activitatii", "Denumirea activității", "txt"],
        ["total_participanti", "Total particip.", "int"],
        ["participanti_masculin", "Masculin", "int"],
        ["participanti_feminin", "Feminin", "int"],
      ],
    },
    {
      key: "activitati_online", nr: "XII", title: "Activități culturale online",
      period: "lista", categorie: true, dateField: "data",
      cols: [
        ["data", "Data", "date", { req: true }],
        ["denumirea_activitatii", "Denumirea activității", "txt"],
        ["tipul_activitatii", "Tipul activității", "text"],
        ["platforma", "Platforma", "text"],
        ["vizualizari", "Vizualizări", "int"], ["impact", "Impact", "int"],
        ["participanti_total", "Total particip.", "int"],
        ["participanti_masculin", "Masculin", "int"],
        ["participanti_feminin", "Feminin", "int"],
        ["participanti_adulti", "Adulți", "int"],
        ["participanti_copii", "Copii", "int"],
      ],
    },
    {
      key: "parteneri", nr: "XIII", title: "Parteneri",
      period: "crud", categorie: false, dateField: null,
      cols: [
        ["partener", "Partener", "text", { req: true }],
        ["scope_local", "Local", "bool"], ["scope_national", "Național", "bool"],
        ["scope_international", "Internațional", "bool"],
        ["date_contact", "Date contact", "text"],
        ["tip_contract", "Tip contract", "text"],
        ["data_semnarii", "Data semnării", "date"],
        ["termen_realizare", "Termen realizare", "text"],
        ["modalitati_realizare", "Modalități realizare", "txt"],
        ["participanti_total", "Total particip.", "int"],
        ["participanti_adulti", "Adulți", "int"], ["participanti_copii", "Copii", "int"],
        ["impact", "Impact", "int"],
      ],
    },
    {
      key: "voluntariat", nr: "XIV", title: "Voluntariat",
      period: "crud", categorie: false, dateField: null,
      cols: [
        ["nume_prenume", "Nume și prenume", "text", { req: true }],
        ["nr_contract", "Nr. contract", "text"],
        ["data_inceperii", "Data începerii", "date"],
        ["data_incheierii", "Data încheierii", "date"],
        ["numar_ore", "Număr ore", "int"],
        ["activitati_realizate", "Activități realizate", "txt"],
        ["coordonator", "Coordonator", "staff"],
      ],
    },
  ];

  window.REGISTRU_PARTS = PARTS;
})();
