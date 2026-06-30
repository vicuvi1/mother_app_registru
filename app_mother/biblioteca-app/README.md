# Registru Digital de Evidență a Activității Bibliotecii

Aplicație desktop **100% offline** pentru înlocuirea registrului fizic de evidență a activității bibliotecii publice din România. Datele sunt stocate local pe calculator; nu este necesară conexiune la internet.

**Versiune curentă:** 1.7.0  
**Repository GitHub:** [mother_app_registru](https://github.com/vicuvi1/mother_app_registru.git)  
**Descărcare pentru biblioteci:** [GitHub Releases](https://github.com/vicuvi1/mother_app_registru/releases) — instalator Windows sau arhivă portabilă

**Ultima actualizare documentație:** 22 iunie 2026

---

## Cuprins

1. [Ce face aplicația](#ce-face-aplicația)
2. [Cele 12 părți ale registrului](#cele-12-părți-ale-registrului)
3. [Meniu și funcții](#meniu-și-funcții)
4. [Scurtături tastatură](#scurtături-tastatură)
5. [Salvare și siguranța datelor](#salvare-și-siguranța-datelor)
6. [Export, import și printare](#export-import-și-printare)
7. [Registru final și overview](#registru-final-și-overview)
8. [Fișiere locale și foldere](#fișiere-locale-și-foldere)
9. [Pornire și instalare](#pornire-și-instalare)
10. [Construire executabil (.exe)](#construire-executabil-exe)
11. [Teste automate](#teste-automate)
12. [Arhitectură tehnică](#arhitectură-tehnică)
13. [Istoric modificări (changelog)](#istoric-modificări-changelog)

---

## Ce face aplicația

Registrul digital permite bibliotecarilor să:

- **Înregistreze zilnic** utilizatori, documente, activități și evenimente conform structurii oficiale a registrului pe 12+ părți (numerotate în cifre romane).
- **Navigheze pe ani și luni** cu tab-uri rapide, totaluri automate și total cumulativ „de la începutul anului”.
- **Genereze automat** rânduri pentru zilele lucrătoare ale fiecărei luni (respectând zilele nelucrătoare / concediu).
- **Exporte** pagini, anul întreg sau registrul complet în **Word (.docx)**, **PDF** sau **Excel (.xlsx)**.
- **Importe** date din fișiere Excel exportate anterior (corecții în masă sau migrare).
- **Printeze** previzualizare cu numerotare pagini și orientare configurabilă.
- **Salveze automat** modificările (interval configurabil) și să creeze **copii de rezervă** ale bazei de date.
- **Restaureze** registrul dintr-o copie anterioară (cu repornire automată).
- **Verifice integritatea** bazei de date la pornire și **luni fără date** înainte de închiderea anului.
- **Lucreze offline** — toate datele rămân pe PC-ul bibliotecii sau pe un stick USB portabil.
- **Vadă progresul** pe panoul **Acasă** — părți complete, luni incomplete, ultimul backup.
- **Primească ghidare** la prima utilizare (tur rapid 5 pași) și stări goale prietenoase în lunile fără date.

La prima pornire, un **asistent de configurare** solicită numele bibliotecii, localitatea, personalul responsabil, range-urile pentru generarea automată și preferințele aplicației (autosalvare, temă, printare, sincronizare backup). Urmează un **tur ghidat** opțional și panoul **Acasă**.

---

## Cele 12 părți ale registrului

| Partea | Denumire | Mod | Descriere scurtă |
|--------|----------|-----|------------------|
| **I** | Evidența utilizatorilor | Zilnic | Utilizatori activi, statut, vârstă, sex — pe zile lucrătoare |
| **II** | Evidența utilizatorilor (Copii / Adulți) | Zilnic | Aceleași date, separate pe categorii Copii / Adulți |
| **III** | Evidența documentelor înregistrate | Zilnic | Documente înregistrate zilnic |
| **IV** | Evidența documentelor (conținut CZU) | Zilnic | Clasificare după conținut CZU |
| **V** | Evidența cercetărilor bibliografice | Evenimente | Listă de evenimente / cercetări (rânduri adăugabile) |
| **VI** | Evidența activităților de informare | Evenimente | Copii și adulți — activități de informare |
| **VII** | Evidența documentelor electronice online | Lunar | Câte un rând pe lună (ian.–dec.) |
| **IX** | Instruirea utilizatorilor bibliotecii | Evenimente | Sesiuni de instruire |
| **XI** | Activități culturale și științifice | Evenimente | Copii și adulți |
| **XII** | Activități culturale ONLINE | Evenimente | Activități online |
| **XIII** | Parteneri ai bibliotecii | CRUD | Tabel liber — adăugare/editare rânduri |
| **XIV** | Activități de voluntariat | CRUD | Voluntari și activități |

**Tipuri de pagină (mod):**

- **Zilnic (daily)** — câte un rând per zi lucrătoare; navigare pe 12 luni; totaluri zilnice + cumulativ anual.
- **Evenimente (events)** — rânduri adăugate manual; duplicare rând (Ctrl+D); pot avea tab Copii/Adulți.
- **Lunar (monthly)** — 12 rânduri fixe (câte o lună).
- **CRUD** — listă liberă fără structură zilnică/lunară fixă.

Toate părțile folosesc **QTableView** rapid, cu delegates pentru checkbox-uri, liste responsabil, text preset și câmpuri inline.

---

## Meniu și funcții

### Setări

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Setup… | Ctrl+, | Asistent: bibliotecă, personal, range-uri, autosalvare, temă, printare, folder cloud backup |
| Pagina de titlu (copertă)… | — | Editează datele pentru coperta registrului la export |
| Zile nelucrătoare (concediu)… | — | Marchează zilele excluse din calendarul lucrător (per an) |

**În Setup → Aplicație:** autosalvare (30s / 1 min / 5 min / dezactivat), temă deschisă/întunecată, orientare printare, copiere automată a backup-urilor într-un folder sincronizat (OneDrive/Dropbox).

### Fișier

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Acasă | Ctrl+H | Panou de ansamblu: progres pe an, backup, luni incomplete |
| Salvează pagina curentă | Ctrl+S | Salvare manuală imediată |
| Registru complet (overview)… | Ctrl+R | Dialog: selectați pagini/luni, previzualizare, export final |
| Luni fără date… | — | Raport: lunile goale sau cu toate valorile zero; dublu-click deschide partea |
| Asistent închidere an… | — | Pași ghidați: luni incomplete → copertă → export → backup |
| Exportă pagina curentă… | Ctrl+E | Export lună / an / registru complet pentru partea curentă |
| Importă din Excel… | — | Importă o lună dintr-un fișier Excel exportat din această aplicație |
| Salvează copie registru (backup)… | — | Copie manuală `biblioteca_manual_YYYYMMDD_HHMMSS.db` |
| Restaurează din copie… | — | Înlocuiește DB; creează copie pre-restaurare; **repornire automată** |
| Deschide folderul copii de rezervă… | — | Deschide folderul `backups/` în Explorer |
| Ieșire | Ctrl+Q | Închide aplicația (cu confirmare dacă există modificări nesalvate) |

### Ajutor

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Ghid rapid pentru bibliotecar… | — | Deschide PDF-ul de o pagină (instalare, lucru zilnic, backup) |
| Scurtături tastatură… | F1 | Lista completă de taste |
| Despre… | — | Versiune aplicație și credit |

### Panou lateral

- Buton **🏠 Acasă** — dashboard la pornire (progres an, continuă sesiunea).
- Listă cu toate părțile active (I–XIV), cu **badge-uri progres**: ✓ complet · ⚠ parțial · · neînceput.
- Buton **Registru final** — editor pe an cu pagini numerotate, bifare pagini, export.

### Bara de instrumente (pe fiecare parte)

- Selector **An** și (unde e cazul) **Lună**.
- **Regenerează zilele** — reconstruiește rândurile zilnice pentru luna curentă.
- **Generează automat** — completează valori aleatoare în range-urile configurate.
- **Copiază luna trecută** — duplică datele din luna anterioară (Ctrl+Shift+M).
- **Range-uri** — setează min/max per coloană numerică.
- **Liste text** — valori predefinite pentru celule tip listă (părți evenimente).
- **Salvează**, **Printează**, **Exportă**.

### Bara de status

- Mesaj contextual pentru acțiunea curentă.
- Indicator **Salvat ✓** cu ora ultimei salvări.
- Banner roșu dacă o salvare a eșuat (cu instrucțiuni de reîncercare).
- **Toast-uri** discrete (2–3 s) pentru salvare, backup, export reușit — fără popup-uri inutile.

### Panou Acasă

- Selector **an registru** și bară de progres (% părți complete).
- **Continuă unde am rămas** — deschide ultima parte / lună din sesiune.
- Status **backup** + butoane rapide salvare / deschidere folder.
- Listă **de completat** — dublu-click pe o lună incompletă deschide partea respectivă.
- Acces la **Asistent închidere an**.

---

## Scurtături tastatură

| Tastă | Acțiune |
|-------|---------|
| **Ctrl+H** | Panou Acasă |
| **Ctrl+S** | Salvează pagina curentă |
| **Ctrl+E** | Exportă pagina curentă |
| **Ctrl+R** | Registru complet (overview) |
| **Ctrl+F** | Găsește în tabel (bară de căutare) |
| **Ctrl+C / Ctrl+V** | Copiază / lipește bloc Excel (TSV) |
| **Ctrl+Shift+M** | Copiază luna trecută |
| **Ctrl+Z** | Anulează ultimele editări (**până la 10 pași**) |
| **Ctrl+← / Ctrl+→** | Luna anterioară / următoare |
| **Ctrl+D** | Duplică rândul selectat (părți evenimente) |
| **Tab / Enter** | Navigare între celule editabile în tabel |
| **Ctrl+,** | Setări bibliotecă |
| **Ctrl+Q** | Ieșire |
| **F1** | Ajutor — scurtături |

---

## Salvare și siguranța datelor

### Salvare automată

- La interval configurabil în Setup: **30 s**, **1 min** (implicit), **5 min** sau **dezactivat**.
- La **schimbarea părții** din meniul stâng.
- La **schimbarea lunii** — salvare amânată în fundal (UI rămâne fluid).
- La **închidere** — flush al modificărilor în așteptare.

### Confirmare la ieșire

Dacă există modificări nesalvate, la închidere apare dialogul: **Salvează / Renunță / Anulează**.

### Sesiune reținută

La repornire, aplicația deschide panoul **Acasă** sau restaurează ultima **parte**, **an** și **lună** (`data/session.json`) prin **Continuă unde am rămas**.

### Verificare integritate

La pornire rulează `PRAGMA integrity_check`. Dacă baza de date este coruptă, aplicația oferă restaurare din ultima copie automată.

### Backup

| Tip | Când | Păstrare |
|-----|------|----------|
| **Automat** | La fiecare pornire | Ultimele **5** copii (`biblioteca_auto_*.db`) |
| **Manual** | Din meniu Fișier | Nelimitat (în folderul backups) |
| **Pre-restaurare** | Înainte de restaurare | Copie `biblioteca_prerestore_*.db` |
| **Cloud (opțional)** | După fiecare backup | Copie în folder OneDrive/Dropbox configurat în Setup |

Backup-urile folosesc API-ul SQLite (`sqlite3.backup`) cu checkpoint WAL pentru consistență. Fișiere simple `.db` — fără parolă sau criptare.

### Bază de date

- **SQLite** cu mod **WAL** (Write-Ahead Logging) pentru performanță și integritate.
- **Indexuri** pe `(an, luna)` pentru interogări rapide.
- **Migrări** de schemă la actualizare (`schema_version`).
- **Timestamps** timezone-aware (UTC) pe înregistrări.

### Jurnal (log)

Evenimentele aplicației (pornire, salvare, export, erori) se scriu în `data/biblioteca.log` (rotație automată).

---

## Export, import și printare

### Formate

| Format | Extensie | Motor |
|--------|----------|-------|
| Word | `.docx` | python-docx |
| PDF | `.pdf` | ReportLab (fonturi cu diacritice românești incluse) |
| Excel | `.xlsx` | openpyxl |

### Domenii export

- **Luna curentă** — doar pagina deschisă.
- **Anul selectat** — toate lunile / categoriile părții curente.
- **Registru complet** — toate părțile (cu dialog de progres și posibilitate de anulare).

### Import Excel

**Fișier → Importă din Excel…** — citește exporturile generate de această aplicație, mapează coloanele și înlocuiește datele lunii selectate. Util pentru corecții în masă după editare în Excel.

### Caracteristici export

- Anteturi comune (`export_common.py`) pe toate formatele.
- Anteturi de grup pe coloane (subgrupări).
- Rânduri Total și Total de la început.
- Pagină de titlu (copertă) opțională.
- Validare date înainte de generare.
- Mesaje de eroare clare (fișier deschis în alt program, spațiu insuficient etc.).
- Dialog de **progres** la exporturi mari.
- Opțiune de deschidere fișier după export reușit.
- **Preset-uri** — reține ultimul folder de export și orientarea printării.

### Printare

Previzualizare print din pagina curentă sau din Registru final. Orientare **peisaj** sau **portret** configurabilă în Setup.

---

## Registru final și overview

### Registru complet (Ctrl+R)

Dialog modal: arbore cu toate părțile și lunile; bifați ce includeți; export sau previzualizare HTML.

### Registru final (buton lateral)

Pagină dedicată pentru **versiunea numerotată pe an** (încărcare lazy la prima deschidere):

- Arbore cu toate paginile registrului.
- Selectare an.
- Bifare pagini de inclus.
- Dublu-click pe pagină → navigare la editare în partea respectivă.
- Previzualizare și export document final.

### Asistent închidere an

Wizard pas cu pas: verificare luni incomplete → pagină de titlu → export final → backup de siguranță.

---

## Fișiere locale și foldere

### Dezvoltare (Python)

```
biblioteca-app/
├── app/
│   ├── main.py                 # Punct de intrare
│   ├── data/                   # Date locale în mod dev
│   │   ├── biblioteca.db       # Baza de date SQLite (NU ȘTERGEȚI)
│   │   ├── biblioteca.log
│   │   ├── session.json
│   │   └── backups/            # Copii de rezervă .db
│   ├── core/                   # Logică: autosave, sesiune, audit, progres, ghid PDF
│   ├── database/               # Modele SQLAlchemy, migrări, backup, integritate
│   ├── ui/                     # Interfață PyQt6, Acasă, onboarding, import Excel
│   └── resources/
│       ├── stylesheet.qss        # Temă deschisă
│       ├── stylesheet_dark.qss   # Temă întunecată
│       ├── registru.ico          # Icon aplicație
│       ├── fonts/                # Fonturi PDF (diacritice)
│       └── guides/               # Ghid bibliotecar PDF
├── tests/                      # 72 teste pytest (+ pytest-qt)
├── scripts/
│   ├── generate_user_guide.py  # Regenerează ghid_bibliotecar.pdf
│   └── generate_icon.py
├── installer/
│   └── registru.iss            # Script Inno Setup
├── install_dependencies.bat    # Instalare venv + runtime (PC nou)
├── run.bat                     # Pornire aplicație (Windows)
├── build.bat                   # PyInstaller portabil + ghid PDF
├── build_installer.bat         # PyInstaller + Inno Setup
├── registru.spec               # Configurare PyInstaller
├── requirements.txt            # Runtime + dev + build
└── requirements-runtime.txt    # Doar rulare (fără pytest/PyInstaller)
```

### Distribuție portabilă (.exe)

După `build.bat`, folderul `dist/RegistruDigital/` conține `RegistruDigital.exe` și `_internal/`. La prima rulare se creează **`data/` lângă executabil** (nu în `_internal`):

```
dist/RegistruDigital/
├── RegistruDigital.exe
├── _internal/                  # Resurse aplicație (read-only)
├── docs/
│   └── ghid_bibliotecar.pdf    # Ghid rapid 1 pagină
└── data/                       # Creat automat — DB, backup, log, sesiune
    ├── biblioteca.db
    ├── backups/
    └── session.json
```

Copiați întregul folder `RegistruDigital/` pe USB pentru utilizare portabilă. Override opțional: variabila de mediu `BIBLIOTECA_DATA_DIR`.

**Important:** Copiați periodic folderul `data/backups/` pe USB sau alt mediu sigur.

---

## Pornire și instalare

### Pentru biblioteci (recomandat)

1. Deschideți [GitHub Releases](https://github.com/vicuvi1/mother_app_registru/releases).
2. Descărcați **`RegistruDigital_Setup_X.X.X.exe`** (instalator) sau **`RegistruDigital-portable.zip`** (fără instalare).
3. Rulați instalatorul sau dezarhivați ZIP-ul și porniți **`RegistruDigital.exe`**.
4. La prima pornire: asistent configurare + tur rapid (opțional).
5. Consultați **Ghid rapid pentru bibliotecar** (PDF în Meniu Start sau **Ajutor** în aplicație).

Nu este nevoie de Python instalat pe PC-ul bibliotecii.

### Cerințe

- **Windows 10/11**
- **Python 3.11+** (doar pentru dezvoltare; utilizatorii finali folosesc `.exe`)

### Dezvoltare (surse Python)

**Variantă rapidă** — dublu-click pe `run.bat` (creează `venv` automat la prima rulare).

**Instalare manuală pe PC nou:**

```bat
cd biblioteca-app
install_dependencies.bat
run.bat
```

`install_dependencies.bat` instalează doar `requirements-runtime.txt` (PyQt6, SQLAlchemy, export). Pentru teste și build:

```bat
venv\Scripts\pip install -r requirements.txt
```

### Dependențe Python

| Fișier | Utilizare |
|--------|-----------|
| `requirements-runtime.txt` | Rulare aplicație (`install_dependencies.bat`, `run.bat`) |
| `requirements.txt` | Dezvoltare completă: runtime + **pytest**, **pytest-qt**, **PyInstaller** |

| Pachet | Rol |
|--------|-----|
| PyQt6 | Interfață desktop |
| SQLAlchemy | ORM SQLite |
| openpyxl | Export / import Excel |
| python-docx | Export Word |
| reportlab | Export PDF + ghid bibliotecar |

### Prima pornire

1. Ecran splash animat la inițializare.
2. Verificare integritate bază de date.
3. Asistent configurare (dacă e prima rulare).
4. Tur ghidat opțional (5 pași).
5. Panoul **Acasă** — progres pe anul curent; sau **Continuă unde am rămas**.

### Instalator Windows (dezvoltatori)

Cu [Inno Setup](https://jrsoftware.org/isinfo.php) instalat și `iscc` în PATH:

```bat
cd biblioteca-app
build_installer.bat
```

Generează ghidul PDF, build PyInstaller, copiază ghidul în `docs/`, apoi Inno Setup.

Rezultat: `installer/output/RegistruDigital_Setup_*.exe` — shortcut în Start Menu, ghid PDF, dezinstalare, ștergere `data/` la uninstall.

### Release automat (GitHub)

La push pe tag `v*` (ex. `v1.7.0`), workflow-ul `.github/workflows/release.yml` construiește ZIP portabil + instalator și publică pe **GitHub Releases**.

```bat
git tag v1.7.0
git push origin v1.7.0
```

---

## Construire executabil (.exe)

### Portabil (PyInstaller)

```bat
cd biblioteca-app
build.bat
```

Rezultat: `dist/RegistruDigital/RegistruDigital.exe` — folder portabil cu dependențe; datele utilizator în `data/` alături; ghid PDF în `docs/`.

### Cu instalator

```bat
build_installer.bat
```

Rulează PyInstaller, apoi Inno Setup dacă este disponibil.

---

## Teste automate

```bat
cd biblioteca-app
set PYTHONPATH=app
venv\Scripts\python.exe -m pytest tests\ -v
```

**72 teste** acoperă: backup/restaurare, export PDF/utilitare, salvare roundtrip, agregări SQL, motor date, sesiune, audit luni incomplete, model tabel, căi portabile, import Excel, cloud backup, integritate DB, autosalvare, progres părți (Sprint II), ghid PDF și release (Sprint III), **smoke tests PyQt** (`pytest-qt`).

**CI GitHub Actions:** la fiecare push pe `main`, rulează testele pe `windows-latest` cu Python 3.12. La tag `v*`, workflow **Release** publică `.exe` + ZIP pe GitHub Releases.

---

## Arhitectură tehnică

| Componentă | Tehnologie |
|------------|------------|
| Interfață | PyQt6 |
| Bază de date | SQLite + SQLAlchemy 2 |
| Export Word | python-docx |
| Export PDF | ReportLab + fonturi DejaVu bundled |
| Export Excel | openpyxl |
| Distribuție | PyInstaller + Inno Setup; GitHub Releases (tag `v*`) |
| Teste | pytest + pytest-qt |

### Performanță

- **Încărcare lazy** a părților — fiecare parte se încarcă la prima deschidere.
- **Cache în memorie** pentru lunile vizitate — revenirea la o lună e instantanee.
- **Preîncărcare** a celor 12 luni în fundal după deschiderea unei părți.
- **Agregări SQL** pentru totalul cumulativ (în loc de încărcarea tuturor rândurilor).
- **Salvare amânată** la schimbarea lunii.
- **Splash screen** la pornire.
- **QTableView + QAbstractTableModel** pentru **toate** părțile, cu delegates pentru bool, scope, responsabil, text preset/inline.

### Structură cod `PartPageBase`

Clasa de bază a paginilor este împărțită în mixin-uri (`app/ui/parts/mixins/`):

| Mixin | Responsabilitate |
|-------|------------------|
| `ui_mixin` | UI, navigare, sesiune, scurtături luni |
| `cache_mixin` | Cache în memorie, preload, salvare amânată |
| `data_mixin` | Persistență DB, generare, copiere lună |
| `export_mixin` | Export, print, construire pagini |

`app/ui/part_base.py` este un re-export subțire — sursa de adevăr sunt mixin-urile. Scriptul `scripts/split_part_base.py` este **arhival** (Batch D); nu îl rulați din nou.

### Module notabile (Batch E–H + Sprint I–III)

| Modul | Rol |
|-------|-----|
| `core/paths.py` | Căi portabile USB, override `BIBLIOTECA_DATA_DIR` |
| `core/cloud_backup.py` | Copiere backup în folder sincronizat |
| `core/part_progress.py` | Progres părți și badge-uri sidebar |
| `core/user_guide.py` | Deschidere ghid PDF bibliotecar |
| `database/integrity.py` | Verificare integritate la pornire |
| `ui/home_page.py` | Panou Acasă — dashboard progres |
| `ui/onboarding_tour.py` | Tur ghidat prima utilizare |
| `ui/widgets/toast.py` | Notificări discrete succes |
| `ui/widgets/empty_state.py` | Stări goale prietenoase în tabel |
| `ui/excel_import/` | Import din Excel |
| `ui/year_end_wizard.py` | Asistent închidere an |
| `ui/widgets/table_find_bar.py` | Căutare Ctrl+F în tabel |
| `ui/export/export_common.py` | Antete și formatare comună export |
| `scripts/generate_user_guide.py` | Generează `ghid_bibliotecar.pdf` |

---

## Istoric modificări (changelog)

Toate orele sunt **ora României (UTC+3)** din jurnalul Git.

### 22 iunie 2026 — Sprint I–III UX și distribuție (v1.5.0 → v1.7.0)

| Commit | Descriere |
|--------|-----------|
| `0e339a8` | **Sprint III — v1.7.0:** ghid PDF bibliotecar; instalator + GitHub Release automat; **Ajutor → Ghid rapid** |
| `97f905d` | **Sprint II — v1.6.0:** panou Acasă; badge-uri progres sidebar; tur onboarding 5 pași |
| `4ed3a64` | **Sprint I — v1.5.0:** toast-uri; evidențiere rând azi; stări goale; icon aplicație |

### 22 iunie 2026 — Batch E–H (v1.1.0 → v1.4.0)

| Commit | Descriere |
|--------|-----------|
| `b68540b` | **Batch H — Calitate cod (Tier 4):** timestamps UTC; deduplicare antet PDF; fix undo pe celule preset; teste `pytest-qt`; eliminare criptare backup |
| `826edf5` | **Batch G — Distribuție (Tier 3):** mod portabil USB (`data/` lângă exe); instalator Inno Setup; import Excel; sincronizare backup cloud |
| `da191e7` | **Batch F — UX (Tier 2):** Ctrl+F în tabel; copy/paste Excel; copiere lună anterioară; wizard închidere an; preset-uri print/export; dark mode; diacritice PDF |
| `67af96c` | **Batch E — Fiabilitate (Tier 1):** QTableView + delegates pe toate părțile; verificare integritate; autosalvare configurabilă; audit luni cu zerouri; dialog Despre; verificare PyInstaller |

### 22 iunie 2026 — Batch A–D (fundament)

| Ora | Commit | Descriere |
|-----|--------|-----------|
| **12:57** | `a00f579` | **Batch D — Arhitectură:** împărțire `PartPageBase` în 4 mixin-uri; `RegisterTableModel` + `RegisterTableView`; factory tabel |
| **12:50** | `8fc12a1` | **Batch C — Siguranță date:** backup SQLite online; banner eroare salvare; undo 10 niveluri; raport „Luni fără date” |
| **12:46** | `98eb9f7` | **Batch B — Fiabilitate:** repornire automată după restaurare; confirmare ieșire; reținere sesiune; Ctrl+←/→ navigare luni |
| **12:42** | `34d5aef` | **Batch A — UX:** fix splash CSS; an/lună curentă implicit; progres export; antete export comune; folder backup; lazy Registru final |
| **12:37** | `231e046` | **Fix critic:** import `QShortcut` din `QtGui` (PyQt6) |
| **12:33** | `12dd5a3` | **Performanță + backup + UX:** indexuri DB, agregări SQL, lazy părți, splash, backup/restaurare UI, CI |
| **12:11** | `b4b3a79` | **Fiabilitate export:** validare/erori export, jurnal rotativ, WAL SQLite |
| **11:56** | `d4099cb` | **Versiune inițială:** aplicație completă PyQt6, 12 părți registru, SQLite, export Word/PDF/Excel |

---

## Depanare rapidă

| Problemă | Soluție |
|----------|---------|
| Aplicația nu pornește | Rulați `run.bat`; verificați `data/biblioteca.log` |
| Bază de date coruptă | La pornire, acceptați restaurarea din ultima copie automată |
| „Fișier deschis în alt program” la export | Închideți Word/Excel/PDF deschis cu același nume |
| Date pierdute | Restaurați din `data/backups/` — cea mai recentă `biblioteca_auto_*.db` |
| Lună goală la export | Completați în parte sau folosiți „Luni fără date” |
| Salvare eșuată (banner roșu) | Ctrl+S; verificați spațiu pe disc |
| Diacritice lipsă în PDF | Reinstalați din build recent (fonturile sunt incluse în `.exe`) |
| Mod portabil USB | Copiați tot folderul `RegistruDigital/`; `data/` trebuie să stea lângă `.exe` |
| Ghid PDF lipsă | Reinstalați din Release sau rulați `scripts\generate_user_guide.py` |
| Prima instalare dev | Rulați `install_dependencies.bat`, apoi `run.bat` |

---

## Licență și credit

Proiect dezvoltat pentru evidența digitală a bibliotecilor publice. Consultați fișierul sursă `core/constants_manager.py` pentru creditul afișat în aplicație.

---

*Document actualizat pentru versiunea **1.7.0** (commit `0e339a8`, 22 iunie 2026).*
