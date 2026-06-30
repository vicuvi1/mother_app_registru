# SPECIFICAȚIE TEHNICĂ COMPLETĂ
## Aplicație Desktop Offline — "Registru Digital de Evidență a Activității Bibliotecii"

---

## 0. CONTEXT ȘI SCOP

Trebuie creată o aplicație desktop, **100% offline**, în **Python**, care înlocuiește completarea manuală a unui registru fizic de bibliotecă (caiet cu 12 secțiuni active numite "Părți" (numerotate I-VII, IX, XI-XIV — fără VIII și X, care nu există în acest registru), fiecare cu tabele lunare pe 12 luni).

**Problema reală pe care o rezolvă:** bibliotecarul pierde ore completând manual, în fiecare zi lucrătoare, zeci de celule numerice (câți adulți, câți copii, câți tineri, etc. au vizitat biblioteca), calculând sume pe linii/coloane, copiind aceleași nume de responsabili peste tot, și scriind manual datele calendaristice verificând care zi e lucrătoare.

**Soluția:** o aplicație care:
1. Generează automat (cu un buton) date plauzibile, în limite (range-uri) definite de bibliotecar, pentru toate zilele lucrătoare ale unei luni;
2. Calculează automat toate totalurile/sumele;
3. Permite editare manuală oricând, pe orice celulă;
4. Reține constante (nume personal, range-uri) pentru reutilizare instant;
5. Exportă rezultatul în Excel / Word / PDF, identic ca structură cu registrul fizic, gata de printat.

---

## 1. STACK TEHNIC

- **Limbaj:** Python 3.11+
- **UI:** PyQt6 (preferat față de Tkinter pentru tabele editabile complexe, mai multe taburi, look modern). Dacă PyQt6 nu e disponibil/licențiabil ușor, fallback pe **PySide6** (LGPL, identic API).
- **Bază de date locală internă:** **SQLite** (fișier `.db` local, prin `sqlite3` din stdlib sau `SQLAlchemy` ca ORM ușor).
- **Export:**
  - Excel → `openpyxl`
  - Word → `python-docx`
  - PDF → `reportlab` SAU export Word→PDF via `docx2pdf`/`LibreOffice` headless (alege `reportlab` pentru control total al layout-ului tabelar, e mai sigur cross-platform fără dependențe externe)
- **Packaging final:** `PyInstaller` pentru a produce un `.exe` (Windows) rulabil fără Python instalat (biblioteca probabil are PC-uri cu Windows).
- **Fără conexiune internet necesară în nicio funcționalitate.**

---

## 2. ARHITECTURA GENERALĂ A APLICAȚIEI

```
app/
├── main.py                  # punct de pornire, inițializează DB + UI
├── database/
│   ├── models.py            # scheme SQLite (tabele pt fiecare Parte)
│   ├── db_manager.py        # conexiune, query-uri, migrări
│   └── seed_defaults.py     # placeholder-uri default (nume etape etc.)
├── core/
│   ├── date_engine.py       # calcul zile lucrătoare, validare dd/ll
│   ├── random_engine.py     # generare automată cu range-uri + validare sume
│   ├── autosave.py          # salvare periodică
│   └── constants_manager.py # gestionare nume personal / etichete custom
├── ui/
│   ├── main_window.py       # fereastră principală, meniu lateral cu cele 12 Părți (numerotate I-VII, IX, XI-XIV)
│   ├── setup_wizard.py      # ecran inițial: Personal, range-uri default
│   ├── part_01_utilizatori.py
│   ├── part_02_utilizatori_copii_adulti.py
│   ├── part_03_documente_inregistrate.py
│   ├── part_04_documente_continut.py
│   ├── part_05_cercetari_bibliografice.py
│   ├── part_06_activitati_informare.py
│   ├── part_07_documente_electronice.py
│   ├── part_09_instruiri.py
│   ├── part_11_activitati_culturale.py
│   ├── part_12_activitati_online.py
│   ├── part_13_parteneri.py
│   ├── part_14_voluntariat.py
│   ├── widgets/
│   │   ├── editable_table.py     # tabel reutilizabil cu celule editabile + sumă auto
│   │   ├── range_config_dialog.py
│   │   ├── date_picker_zile_lucratoare.py
│   │   └── responsabil_dropdown.py
│   └── export/
│       ├── export_excel.py
│       ├── export_word.py
│       └── export_pdf.py
├── resources/
│   └── icons, stylesheet.qss
└── data/
    └── biblioteca.db          # SQLite, creat la prima rulare
```

---

## 3. MODELUL DE DATE (SQLite) — PRINCIPII GENERALE

Fiecare "Parte" (1-14) are propriul tabel/tabele, cu coloane reflectând EXACT structura din registrul fizic (vezi secțiunea 5 pentru fiecare parte în detaliu). Reguli comune tuturor tabelelor:

```sql
-- Tabel generic exemplu (Parte 1)
CREATE TABLE evidenta_utilizatori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    an INTEGER NOT NULL,
    luna INTEGER NOT NULL,           -- 1-12
    data TEXT NOT NULL,              -- format "DD.MM" — vezi sectiunea 4
    -- Utilizatori activi
    adulti INTEGER DEFAULT 0,
    copii_pana_16 INTEGER DEFAULT 0,
    prescolari INTEGER DEFAULT 0,
    elevi INTEGER DEFAULT 0,
    studenti INTEGER DEFAULT 0,
    intelectuali INTEGER DEFAULT 0,
    muncitori INTEGER DEFAULT 0,
    pensionari INTEGER DEFAULT 0,
    someri INTEGER DEFAULT 0,
    alte_categorii INTEGER DEFAULT 0,
    -- După vârstă
    tineri_17_34 INTEGER DEFAULT 0,
    adulti_35_64 INTEGER DEFAULT 0,
    varstnici_65_plus INTEGER DEFAULT 0,
    -- După sex - copii 16 ani
    sex_copii_f INTEGER DEFAULT 0,
    sex_copii_m INTEGER DEFAULT 0,
    -- După sex - adulți
    sex_adulti_f INTEGER DEFAULT 0,
    sex_adulti_m INTEGER DEFAULT 0,
    is_auto_generated BOOLEAN DEFAULT 0,  -- ca să știm ce-i manual vs random
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(an, luna, data)
);
```

**Tabele suport globale (folosite de toate Părțile):**

```sql
-- Personal/Responsabili — definit o singură dată în Setup, reutilizat peste tot
CREATE TABLE personal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nume_prenume TEXT NOT NULL UNIQUE,  -- ex "Bărbuță O.", "Poleșciuc T."
    activ BOOLEAN DEFAULT 1
);

-- Range-uri configurabile per coloană per Parte (pt generare automată)
CREATE TABLE range_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parte TEXT NOT NULL,         -- ex "part_01"
    coloana TEXT NOT NULL,       -- ex "adulti"
    valoare_min INTEGER DEFAULT 0,
    valoare_max INTEGER DEFAULT 20,
    UNIQUE(parte, coloana)
);

-- Etichete custom (nume editabile ale etapelor/coloanelor, cu placeholder default)
CREATE TABLE etichete_custom (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parte TEXT NOT NULL,
    camp TEXT NOT NULL,          -- identificator intern
    eticheta_default TEXT NOT NULL,  -- ce arată în poze
    eticheta_custom TEXT,            -- ce a editat bibliotecarul (NULL = folosește default)
    UNIQUE(parte, camp)
);

-- Setări generale aplicație
CREATE TABLE app_settings (
    cheie TEXT PRIMARY KEY,
    valoare TEXT
);
```

> **Notă importantă:** fiecare Parte 2-9 (cele care separă Copii/Adulți) trebuie să aibă tabele DUPLICATE sau o coloană `categorie_varsta` ('copii'/'adulti') — vezi secțiunea 5 pentru care Părți necesită separarea și care nu.

---

## 4. MODULUL DE GESTIONARE A DATELOR CALENDARISTICE (`date_engine.py`)

### Cerințe funcționale:
1. Bibliotecarul selectează **An** (dropdown, ex. 2024-2030) și **Lună** (dropdown, Ianuarie-Decembrie).
2. La selecție, aplicația calculează automat **toate zilele lucrătoare** (Luni-Vineri) din luna respectivă, EXCLUZÂND sâmbăta și duminica.
3. Format afișat și stocat: **`DD.MM`** (exact ca în registrul fizic, ex. `01.03`, `15.03`).
4. Aceste zile populează automat rândurile tabelului pentru luna curentă selectată (un rând per zi lucrătoare).
5. **Sărbători legale (opțional, fază 2):** posibilitate de a marca manual o zi lucrătoare ca "liberă" (sărbătoare legală din Moldova) și să fie exclusă — dar NU e blocant pentru versiunea 1; se poate implementa ca listă editabilă de excepții.

### Funcții necesare:
```python
def get_working_days(year: int, month: int, excluded_dates: list[str] = None) -> list[str]:
    """
    Returnează listă de string-uri 'DD.MM' pentru toate zilele Luni-Vineri
    din luna/anul dat, excluzând datele din excluded_dates (format 'DD.MM').
    """

def is_working_day(date_obj: date) -> bool:
    """True dacă date_obj.weekday() < 5 (Luni=0 ... Vineri=4)"""

def validate_date_format(date_str: str) -> bool:
    """Validează că string-ul respectă strict formatul DD.MM"""
```

### UI:
- Selector An + Lună în partea de sus a fiecărei pagini de Parte.
- Buton **"Regenerează zilele lunii"** — repopulează rândurile tabelului curent cu zilele lucrătoare corecte (cu avertisment dacă există deja date introduse, să nu le șteargă fără confirmare).
- Rândurile sunt mereu sortate cronologic crescător.

---

## 5. MODULUL DE GENERARE AUTOMATĂ (`random_engine.py`)

### Principiu de bază
Pentru fiecare coloană numerică dintr-un tabel, bibliotecarul poate seta un **range (min, max)** printr-un dialog de configurare (`range_config_dialog.py`), accesibil printr-un buton "⚙ Configurează range-uri" în fiecare pagină de Parte.

### Reguli de generare logică (decizia ta, bazată pe analiza pozelor)

Am observat în registrul fizic 3 tipare de relații matematice între coloane care TREBUIE respectate de motorul de generare, altfel rezultatul ar fi absurd (ex. suma pe categorii ≠ total utilizatori):

**A. Coloane "Total" care sunt SUMA altor coloane** (ex. Partea I: `Total imprumuturi` = `Consultare pe loc` + `Imprumut pe loc` + `Imprumut la domiciliu` + `Imprumut inter bibliotecar`)
→ Generare: se generează random fiecare sub-coloană în range-ul ei, iar coloana Total se CALCULEAZĂ automat (nu se generează random), garantând consistență 100%.

**B. Categorii care reprezintă aceeași populație clasificată în 2 moduri diferite** (ex. Partea I: `Utilizatori activi` clasificați după statut social = clasificați după vârstă = clasificați după sex — toate 3 ar trebui să sumeze la ACELAȘI total de utilizatori activi din ziua respectivă)
→ Generare: 
  1. Se generează întâi un `Total Utilizatori Activi` random (în range-ul global setat).
  2. Acest total e distribuit proporțional-random pe sub-categoriile fiecărei clasificări (statut social / vârstă / sex), folosind un algoritm de "split aleatoriu cu sumă fixă" (ex. metoda "stars and bars" / `random.multinomial`), respectând range-urile min/max setate per coloană acolo unde sunt definite.
  3. Acest lucru asigură ce ai cerut explicit: dacă "tineri" are range 0-20, valoarea generată respectă acel range, DAR suma totală a tuturor sub-categoriilor de vârstă = suma totală a categoriilor de statut social = Total utilizatori activi din acea zi.

**C. Coloane independente, fără relație de sumă cu altele** (ex. Partea IX Instruiri: `Nr. participanți` per club nu trebuie să sume la nimic anume)
→ Generare: pur random uniform în range-ul [min, max] setat.

### Funcții necesare:
```python
def generate_random_in_range(min_val: int, max_val: int) -> int:
    """Random simplu uniform."""

def generate_split_sum(total: int, n_categories: int, mins: list[int], maxs: list[int]) -> list[int]:
    """
    Distribuie 'total' în n_categories valori, fiecare respectând [min_i, max_i],
    astfel încât suma = total exact. Dacă imposibil de respectat range-urile exact,
    relaxează proporțional și avertizează userul.
    """

def generate_month_data(parte: str, an: int, luna: int, range_config: dict) -> None:
    """
    Funcția master apelată de butonul 'Generează automat luna curentă'.
    Pentru fiecare zi lucrătoare:
      1. Generează/calculează toate coloanele conform regulilor A/B/C de mai sus
         specifice Părții respective (mapare definită per Parte în config).
      2. Salvează în DB cu is_auto_generated = True.
      3. Recalculează rândul TOTAL de la finalul lunii.
    """
```

### UI pentru range-uri:
- Buton **"⚙ Configurează range-uri"** deschide un dialog cu listă de toate coloanele numerice ale Părții curente, fiecare cu 2 input-uri (Min / Max).
- Aceste range-uri sunt **salvate persistent** (per Parte, per coloană) — nu trebuie resetate de fiecare dată, dar pot fi editate oricând.
- Range-urile default (dacă bibliotecarul nu le-a setat încă) — sugestie inițială generoasă: 0-30 pentru coloane gen "număr persoane/zi", 0-5 pentru coloane gen "instruiri/activități pe zi" (vezi secțiunea 5 detaliată per Parte pentru sugestii specifice unde e relevant).

### UI pentru generare:
- Buton mare, vizibil: **"🎲 Generează automat toată luna"** — populează toate zilele lucrătoare ale lunii selectate.
- Buton secundar: **"🎲 Regenerează doar ziua selectată"** — regenerează un singur rând.
- **Avertisment de confirmare** înainte de suprascriere dacă există deja date manuale introduse pentru zilele respective ("Atenție: X zile au date introduse manual. Sigur vrei să le suprascrii?").
- Orice celulă generată automat rămâne **liber editabilă manual** după generare (un simplu click + tastare suprascrie valoarea, indiferent că a fost auto sau manuală) — recalculul sumelor se face live, la fiecare modificare de celulă (folosind regulile A/B de mai sus, dar PERMIȚÂND inconsistențe dacă userul editează manual — nu blocăm input manual, doar recalculăm Total-urile automat unde are sens).

---

## 6. ECRANUL DE SETUP INIȚIAL (`setup_wizard.py`)

Apare la prima rulare a aplicației (și accesibil oricând din meniu: "Setări → Setup").

### Secțiuni:

**6.1 Personal/Responsabili**
- Tabel editabil simplu: listă de nume (ex. "Bărbuță O.", "Poleșciuc T.", "Darii Elena", "Poleșciuc Valeriu").
- Butoane: Adaugă / Editează / Șterge nume.
- Aceste nume populează AUTOMAT toate dropdown-urile "Responsabil" din toate cele 12 Părți implementate (oriunde apare coloana "Responsabil" sau "Formator" sau "Coordonator voluntari" în registru).
- Bibliotecarul poate alege dintr-un dropdown SAU scrie un nume nou direct (care se adaugă automat și în lista de Personal pentru reutilizare viitoare).

**6.2 Range-uri Default Globale**
- Posibilitate de a seta range-uri generale (ex. "majoritatea coloanelor de tip persoane/zi: 0-X") care se aplică ca punct de plecare la toate Părțile, urmând a fi rafinate per-Parte din butonul individual "⚙ Configurează range-uri" din fiecare pagină.

**6.3 Date Bibliotecă**
- Câmpuri simple: Nume bibliotecă, Localitate (apar opțional în antetul exporturilor PDF/Word).

---

## 7. STRUCTURA DETALIATĂ A CELOR 14 PĂRȚI

> Toate cele 12 Părți active sunt numerotate exact conform registrului fizic: I, II, III, IV, V, VI, VII, IX, XI, XII, XIII, XIV (NU există Partea VIII sau Partea X în acest registru — numerotarea trebuie păstrată identică, cu salturile reale, NU renumerotată secvențial). Fiecare pagină din aplicație (tab/secțiune în meniul lateral) corespunde unei Părți. Fiecare Parte are propriul selector de An+Lună independent (datele diferă pe lună).

### PARTEA I — Evidența utilizatorilor în luna X anul Y
**(Copii ȘI Adulți ÎMPREUNĂ, pe același tabel — NU se separă aici)**

Coloane (toate INT, editabile/generabile):
- **Data** (auto, DD.MM, needitabilă manual — vine din date_engine)
- **Utilizatori activi:** Adulți, Copii până la 16 ani, Preșcolari, Elevi, Studenți, Intelectuali, Muncitori, Pensionari, Șomeri, Alte categorii
- **După vârstă:** Tineri (17-34 ani), Adulți (35-64 ani), Vârstnici după 65 ani
- **După sex copii 16 ani:** F, M
- **După sex adulți:** F, M

Rând final: **Total** = sumă pe coloană pentru toate zilele lunii (auto-calculat, needitabil).

Relație de tip B (vezi secțiunea 5): coloanele "Utilizatori activi" (statut social) și coloanele "După vârstă" ar trebui să tindă spre aceeași sumă totală de utilizatori/zi — generare conform regulii B.

---

### PARTEA II — Evidența utilizatorilor în luna X anul Y
**(SEPARAT: o pagină/tab pentru "Copii" și un tab separat pentru "Adulți" — identice structural, date diferite)**

Coloane:
- **Data**, **Intrări total zi**
- **Din care:** Împrumut cărți, Ședințe Calculatoare, Activități Culturale/Științifice și altele, Instruiri, Alte scopuri/excursii
- **Vizite virtuale:** Total vizite virtuale, Pagină web, Blog
- **Vizitatori virtuali:** Total vizitatori virtuali, Pagină web, Blog
- **Indicatori rețele sociale (Facebook, Instagram, Twitter):** Vizualizări, Impact, Interacționări

Rând final: **Total**, plus un rând **"Total de la început"** (cumulativ — needitabil, se calculează ca sumă a tuturor lunilor anterioare ale anului + luna curentă).

---

### PARTEA III — Evidența documentelor înregistrate (după categorii și limbi)
**(SEPARAT Copii/Adulți, identic structural)**

Coloane:
- **Data**, **Total împrumuturi**
- **Din care:** Consultare pe loc, Împrumut pe loc, Împrumut la domiciliu, Împrumut inter-bibliotecar
- **După categorii de documente:** Cărți, Publicații seriale, Documente de muzică tipărită, Documente audiovizuale, Documente electronice (CDROM/DVD), Alte documente
- **După limbi:** În limba română, Alte limbi

Relație tip A: `Total împrumuturi` = `Consultare pe loc` + `Împrumut pe loc` + `Împrumut la domiciliu` + `Împrumut inter-bibliotecar` (vezi pozele — coloanele "Din care" sumează la Total).
Relație tip A: `Total împrumuturi` ar trebui ≈ suma coloanelor "După categorii de documente" (Cărți + Publicații + ... ).

Rând final: **Total** + **Total de la început**.

---

### PARTEA IV — Evidența documentelor (după conținut CZU)
**(SEPARAT Copii/Adulți)**

Coloane:
- **Data**, **Total împrumuturi**
- **După conținut CZU:** 0-Generalități, 1-Filozofie/Psihologie, 2-Religie/Teologie, 3-Științe sociale, 5-Matematică/Științe sociale, 6-Științe aplicate/Medicină/Tehnologie, 7-Arte/Recreație/Sport, 8-Limbi/Lingvistică/Literatură, 9-Geografie/Biografie/Istorie

Relație tip A: Total împrumuturi = suma celor 9 categorii CZU.

Rând final: **Total** + **Total de la început**.

---

### PARTEA V — Evidența cercetărilor bibliografice și a referințelor
**(SEPARAT Copii/Adulți)**

Aceasta NU e un tabel zilnic — e un tabel pe **cereri individuale** (fiecare rând = o cerere de la un solicitant specific, nu o zi).

Coloane:
- **Data primirii cererii**
- **Total referințe**
- **Date despre solicitant:** Statut socio-profesional (text liber sau dropdown: elev, casnică, pensionar, student, etc.)
- **Tema (titlul)** — text liber
- **Tip de referință bibliografică:** Referință, Cercetare bibliografică, Consultație
- **Tip de referință (alt grup):** tematică, de concretizare, de adresă, factologie, limite cronologice
- **Surse consultație**, **Număr de descrieri bibliografice**, **Surse recomandate**
- **Data finalizării cererii**
- **Responsabil** (dropdown din Personal)

> Important: acest tabel are rânduri ADĂUGATE manual (buton "+ Adaugă cerere nouă"), NU generate automat pe zile lucrătoare, pentru că nu există o cerere în fiecare zi. Totuși, butonul de generare automată poate exista opțional pentru a popula N cereri random distribuite pe zile lucrătoare alese random din lună, dacă bibliotecarul vrea asta — dar implicit acest tabel e ÎN PRIMUL RÂND manual.

Rând final: **Total** + **Total de la început**.

---

### PARTEA VI — Evidența activităților de informare
**(SEPARAT Copii/Adulți)**

Tabel pe evenimente (similar Partea V — rânduri adăugate, nu neapărat zilnic).

Coloane:
- **Data**, **Grup țintă/Subiect** (text liber, ex. "Ziua păsărilor")
- **Gen de activitate:** Individuală (DSI etc.), Pentru un grup (Ziua specialistului, Ziua Catedrei etc.), Pentru publicul larg (Ziua de Informare, Expoziții de informare)
- **Număr participanți**
- **Documente consultate**
- **Responsabil** (dropdown din Personal)

Rând final: **Total** + **Total de la început**.

---

### PARTEA VII — Evidența documentelor electronice furnizate printr-un mediu online
**(SEPARAT Copii/Adulți — opțional, verifică dacă există separare în poze; din pozele furnizate pare un singur tabel anual, nu lunar — se completează pe luni Ianuarie-Decembrie ca și coloane, nu ca pagini separate)**

Coloane:
- **Total documente electronice furnizate**
- **Mediu furnizare:** E-mail, Skype/rețele sociale
- **După categorii de documente:** Cărți, Publicații seriale, Documente de muzică tipărită, Documente audiovizuale, Documente Electronice (CD/DVD), Alte documente
- **După limbi:** În limba română, Alte limbi

Acest tabel pare structurat ca: rânduri = lunile anului (Ianuarie...Decembrie), nu zile. Implementare: selector de AN, tabel cu 12 rânduri fixe (lunile), fără generare "zi lucrătoare" — generare automată pe lună direct.

---

> **Notă privind numerotarea Părților:** Registrul fizic al acestei biblioteci NU conține o "Partea VIII" — numerotarea sare direct de la Partea VII la Partea IX (confirmat de bibliotecar). De asemenea, materialul sursă furnizat nu a inclus o "Partea X" explicită — secțiunile documentate sunt exact: I, II, III, IV, V, VI, VII, IX, XI, XII, XIII, XIV. Aplicația trebuie să respecte ACEASTĂ numerotare exactă (cu salturile reale), nu să renumeroteze secvențial 1-12, ca să corespundă identic cu registrul fizic atunci când bibliotecarul printează/exportă (un bibliotecar care verifică numărul Părții pe foaia printată trebuie să vadă "Partea IX", nu "Partea VIII", pentru secțiunea de Instruiri). Meniul lateral al aplicației trebuie să afișeze Părțile cu numerele lor romane reale (I, II, III, IV, V, VI, VII, IX, XI, XII, XIII, XIV) — fără intrare pentru VIII sau X.

---

### PARTEA IX — Instruirea utilizatorilor bibliotecii
**(Tabel comun, fără separare Copii/Adulți explicită în poze — dar conține coloana "Din care copii până la 16 ani" — deci o SINGURĂ pagină cu coloana asta inclusă)**

Coloane:
- **Data**
- **Formatul instruirii:** Online, Offline (checkbox/bifă)
- **Forma de instruire continuă:** Formală, Non-formală, Informală — fiecare cu Nr. de ore academice
- **Tema instruirii** (text liber, ex. "Clubul de dame - pe table și online", "Engleza este amuzantă cu jocuri și cântece")
- **Formator (nume, prenume)** — dropdown din Personal
- **Total participanți**
- **Adulți**
- **Din care copii până la 16 ani**

Rând final: **Total** + **Total de la început**.

> Notă: acest tabel are MULTIPLE rânduri pe aceeași zi (mai multe instruiri diferite în aceeași zi, cu formatori diferiți) — deci NU e strict "un rând per zi lucrătoare", ci suportă multiple rânduri per dată. Implementare: butonul de "generare automată" creează N rânduri random distribuite pe zilele lucrătoare ale lunii (N configurabil, ex. 1-3 instruiri pe zi), fiecare cu temă aleasă random dintr-o listă predefinită (editabilă) de teme posibile.

---

### PARTEA XI — Evidența activităților culturale și științifice
**(SEPARAT Copii/Adulți)**

Coloane:
- **Total număr:** Activități culturale/științifice, Din care expoziții
- **Tipul activității** (dropdown: Expoziție, Activitate literar-culturală, Oră educativă, Activitate/Expoziție, Oră de lectură, Oră de desen, Oră de poezie, Competiție joc de dame, Excursie, etc. — listă editabilă)
- **Denumirea activității** (text liber, ex. "Mihai Eminescu - Lumina Poeziei Românești")
- **Total participanți**

Rând final: **Total** + **Total de la început**.

> Similar Părții V/VI — rânduri pe evenimente, nu obligatoriu un rând per zi lucrătoare.

---

### PARTEA XII — Evidența activităților culturale și științifice ONLINE
**(Copii — pare să aibă pagină proprie "COPII PÂNĂ LA 16 ANI" conform poză; posibil și Adulți simetric)**

Coloane:
- **Data**, **Denumirea activității**, **Tipul activității**
- **Platforma** (text liber, ex. Facebook, Zoom)
- **Vizualizări**, **Impact**
- **Participanți:** Total, Adulți, Copii până la 16 ani

Rând final: **Total** + **Total de la început**.

---

### PARTEA XIII — Parteneri ai bibliotecii
**(Un singur tabel, fără separare Copii/Adulți, fără caracter lunar — e un tabel de tip "listă de parteneri", needitat pe zile)**

Coloane:
- **Partener** (text liber, ex. "Casa de Cultură", "Grupul Seniori Sofienii")
- **Local / Național / Internațional** (bifă tip checkbox pe una din cele 3)
- **Date de contact**
- **Tip de contract**
- **Data semnării**
- **Termenul de realizare**
- **Modalități de realizare a parteneriatului** (text liber)
- **Participanți:** Total, Adulți, Copii până la 16 ani
- **Impact**

> Acest tabel NU necesită date_engine (nu are zile lucrătoare) — e CRUD simplu de rânduri (Adaugă/Editează/Șterge partener), fără generare automată by-default (opțional generare de N parteneri fictivi pentru testare, dar nu central pentru bibliotecar).

---

### PARTEA XIV — Activități de voluntariat
**(Un singur tabel, fără separare Copii/Adulți, CRUD simplu, nu pe zile lucrătoare)**

Coloane:
- **Numele, prenumele** (al voluntarului)
- **Nr. contractului**
- **Perioada activității de voluntariat:** Data începerii, Data încheierii
- **Numărul de ore de voluntariat**
- **Activități realizate** (text liber)
- **Semnătura coordonatorului de voluntari** (text/nume — dropdown din Personal)

> CRUD simplu, similar Partea XIII.

---

## 8. INTERFAȚA UTILIZATOR (UI/UX) — CERINȚE GENERALE

### 8.1 Layout general
- **Fereastră principală** cu meniu lateral (sidebar) listând toate cele 12 Părți active (I-VII, IX, XI-XIV), click pe fiecare deschide pagina respectivă în zona principală.
- Fiecare pagină de Parte are antet cu: Selector An, Selector Lună (dacă aplicabil pentru acea Parte), butoane: **"🎲 Generează automat"**, **"⚙ Configurează range-uri"**, **"💾 Salvează"**, **"🖨 Printează"**, **"📤 Exportă"**.

### 8.2 Tabel editabil (`editable_table.py`)
- Folosește `QTableWidget` (PyQt6) cu celule editabile direct prin dublu-click sau tastare.
- Coloanele "Total"/calculate sunt **needitabile** (fundal gri, font diferit) — actualizate live la fiecare schimbare de celulă din coloanele sursă.
- Validare input: doar numere întregi ≥ 0 acceptate în celulele numerice (input invalid respins cu mesaj scurt, nu cu popup blocant).
- Highlight vizual diferit pentru celule generate automat (ex. fundal albastru pal) vs. editate manual (fundal alb normal) — ajută bibliotecarul să vadă ce a fost generat și ce a modificat el.

### 8.3 Editare nume etape/coloane
- Lângă fiecare titlu de coloană din tabel, un buton mic "✏" (editează eticheta) deschide un mic input inline pentru a redenumi coloana. Default = numele exact din pozele registrului (stocat în `etichete_custom.eticheta_default`). Dacă bibliotecarul redenumește, se salvează în `eticheta_custom` și se afișează acel nume de atunci încolo (dar exportul Excel/Word păstrează opțiunea de a alterna între eticheta originală și cea custom, configurabil).

### 8.4 Autosave
- Funcție de autosave la fiecare **60 de secunde** (configurabil în Setări) și la fiecare schimbare de pagină/tab.
- Indicator vizual mic "Salvat ✓" / "Se salvează..." în colțul ferestrei.
- Toate datele introduse merg direct în SQLite la fiecare editare de celulă (debounce de ~1-2 secunde după ultima tastare, ca să nu facă query la fiecare apăsare de tastă) — autosave-ul de 60s e un backup suplimentar, nu principalul mecanism de persistare.

### 8.5 Printare
- Buton "🖨 Printează" deschide preview de printare (folosind `QPrintPreviewDialog` din PyQt6) afișând tabelul curent formatat similar cu pagina din registrul fizic (cu antet "Registru de evidență a activității bibliotecii", numărul Părții, luna/anul).

### 8.6 Export
- **Export Excel (`export_excel.py`):** generează `.xlsx` cu `openpyxl`, replică exactă a structurii tabelului (coloane, sub-coloane, rând Total/Total de la început), cu formatare similară registrului fizic (borduri, antet bold, lățimi coloane potrivite).
- **Export Word (`export_word.py`):** generează `.docx` cu `python-docx`, tabel Word cu aceeași structură, util pentru printare/arhivare oficială.
- **Export PDF (`export_pdf.py`):** generează `.pdf` cu `reportlab`, tabel paginat corect (dacă tabelul e prea lat, se rotește landscape automat, similar paginilor din registrul fizic care sunt landscape).
- Toate exporturile includ opțiunea: "Exportă doar luna curentă" SAU "Exportă tot anul (toate lunile completate)" SAU "Exportă toate Părțile completate (registru complet)".
- Numire fișiere export sugerată automat: `Partea_I_Evidenta_Utilizatori_Martie_2024.xlsx` etc.

---

## 9. FLUX TIPIC DE UTILIZARE (USER STORY DE VALIDARE)

1. Bibliotecarul deschide aplicația prima dată → vede **Setup Wizard** → introduce numele personalului (Bărbuță O., Poleșciuc T., Darii Elena) → salvează.
2. Click pe "Partea I — Evidența utilizatorilor" din meniul lateral.
3. Selectează An = 2025, Luna = Martie → aplicația populează automat 21 de rânduri (zilele lucrătoare din martie 2025, excluzând weekend-urile).
4. Click pe "⚙ Configurează range-uri" → setează Adulți: 2-6, Copii: 1-5, Tineri: 0-3, etc.
5. Click pe "🎲 Generează automat" → toate cele 21 de rânduri se populează cu valori random respectând range-urile și relațiile de sumă (regula B din secțiunea 5) → rândul Total se calculează automat.
6. Bibliotecarul observă că pe 15.03 vrea o valoare specifică (nu cea generată) → dă dublu-click pe celulă, scrie manual 7 → Total-ul liniei și coloanei se recalculează instant.
7. Click pe "💾 Salvează" (deși autosave rulează deja în fundal).
8. Click pe "📤 Exportă" → alege Excel → fișierul se salvează local, gata de trimis/arhivat/printat.
9. Repetă pentru celelalte 13 Părți, mult mai rapid decât completarea manuală în caiet.

---

## 10. ORDINEA DE IMPLEMENTARE RECOMANDATĂ (PENTRU AI-UL CARE CODEAZĂ)

Implementează în această ordine, testând funcțional după fiecare etapă:

1. **Fundație:** `main.py`, `database/models.py`, `db_manager.py` — creează schema SQLite completă pentru toate cele 12 Părți active (I-VII, IX, XI-XIV) dintr-o dată (chiar dacă UI nu există încă).
2. **date_engine.py** — funcțiile de calcul zile lucrătoare, testate independent cu unit tests simple.
3. **UI de bază:** `main_window.py` cu sidebar funcțional (navigare goală, fără conținut încă).
4. **setup_wizard.py** — ecranul de Personal + Range-uri default.
5. **Widget reutilizabil `editable_table.py`** — componenta centrală de tabel, testată separat cu date mock.
6. **random_engine.py** — implementează regulile A/B/C de generare, testate cu assert-uri pe sume.
7. **Partea I completă** (cel mai complex caz, cu toate cele 3 tipuri de relații A/B/C) — folosește ca șablon pentru restul.
8. **Părțile II-IV** (cu separare Copii/Adulți, structuri similare Părții I/III).
9. **Părțile V, VI, XI** (structuri CRUD pe evenimente, nu pe zile).
10. **Partea IX** (instruiri, structură specială cu multiple rânduri/zi).
11. **Părțile VII, XII** (structuri pe lună, nu pe zi).
12. **Părțile XIII, XIV** (CRUD simplu, fără date_engine).
13. **Modulele de export** (Excel → Word → PDF, în această ordine de prioritate).
14. **Autosave + printare + polish UI final.**
15. **Packaging cu PyInstaller** → testare `.exe` final pe Windows curat (fără Python instalat).

---

## 11. CERINȚE NON-FUNCȚIONALE

- Aplicația trebuie să pornească și să funcționeze **fără nicio conexiune la internet**, din primul moment al instalării.
- Toate datele rămân **100% locale** pe calculatorul bibliotecarului (fișier `biblioteca.db` în folderul aplicației sau `%APPDATA%`).
- Limba interfeței: **Română** (toate etichetele, mesajele, butoanele).
- Aplicația trebuie să pornească rapid (sub 3 secunde) chiar cu câțiva ani de date acumulate.
- Recomandare backup: la fiecare export reușit, aplicația poate sugera și o copie automată a `.db`-ului într-un folder `backups/` cu timestamp în nume.

---

## 12. ÎNTREBĂRI DESCHISE PENTRU FAZE ULTERIOARE (nu blochează versiunea 1)

- Lista exactă de sărbători legale din Republica Moldova de exclus din zilele lucrătoare (poate fi adăugată ca listă hardcodată editabilă într-o fază 2).
- Posibilitate de generare a unui "raport anual consolidat" automat din toate cele 12 Părți implementate (fază 2, după ce versiunea de bază e validată de bibliotecar).
- Dacă bibliotecarul identifică ulterior conținut pentru o eventuală "Partea X" (neconfirmată ca existentă în registrul actual), structura modulară a aplicației (fiecare Parte = un fișier separat `part_XX_nume.py` + tabel SQLite propriu) permite adăugarea ei ulterior fără refactorizare majoră.

---

**Sfârșitul specificației.** Acest document este suficient de detaliat pentru a fi folosit direct ca prompt/brief tehnic pentru un AI de dezvoltare (ex. Claude Code) sau pentru un dezvoltator uman, fără alte clarificări necesare pentru a începe implementarea versiunii 1 funcționale.
