# Registru Digital de Evidență a Activității Bibliotecii

Aplicație desktop **100% offline** pentru înlocuirea registrului fizic de evidență a activității bibliotecii publice din România. Datele sunt stocate local pe calculator; nu este necesară conexiune la internet.

**Repository GitHub:** [mother_app_registru](https://github.com/vicuvi1/mother_app_registru.git)

**Ultima actualizare documentație:** 22 iunie 2026

---

## Cuprins

1. [Ce face aplicația](#ce-face-aplicația)
2. [Cele 12 părți ale registrului](#cele-12-părți-ale-registrului)
3. [Meniu și funcții](#meniu-și-funcții)
4. [Scurtături tastatură](#scurtături-tastatură)
5. [Salvare și siguranța datelor](#salvare-și-siguranța-datelor)
6. [Export și printare](#export-și-printare)
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
- **Printeze** previzualizare cu numerotare pagini.
- **Salveze automat** modificările și să creeze **copii de rezervă** ale bazei de date.
- **Restaureze** registrul dintr-o copie anterioară (cu repornire automată).
- **Verifice luni fără date** înainte de închiderea anului.
- **Lucreze offline** — toate datele rămân pe PC-ul bibliotecii.

La prima pornire, un **asistent de configurare** solicită numele bibliotecii, localitatea, personalul responsabil și range-urile pentru generarea automată a valorilor.

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

---

## Meniu și funcții

### Setări

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Setup… | Ctrl+, | Redeschide asistentul: nume bibliotecă, localitate, personal, range-uri |
| Pagina de titlu (copertă)… | — | Editează datele pentru coperta registrului la export |
| Zile nelucrătoare (concediu)… | — | Marchează zilele excluse din calendarul lucrător (per an) |

### Fișier

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Salvează pagina curentă | Ctrl+S | Salvare manuală imediată |
| Registru complet (overview)… | Ctrl+R | Dialog: selectați pagini/luni, previzualizare, export final |
| Luni fără date… | — | Raport: lunile fără rânduri salvate în DB; dublu-click deschide partea |
| Exportă pagina curentă… | Ctrl+E | Export lună / an / registru complet pentru partea curentă |
| Salvează copie registru (backup)… | — | Copie manuală `biblioteca_manual_YYYYMMDD_HHMMSS.db` |
| Restaurează din copie… | — | Înlocuiește DB; creează copie pre-restaurare; **repornire automată** |
| Deschide folderul copii de rezervă… | — | Deschide `app/data/backups/` în Explorer |
| Ieșire | Ctrl+Q | Închide aplicația (cu confirmare dacă există modificări nesalvate) |

### Ajutor

| Opțiune | Scurtătură | Descriere |
|---------|------------|-----------|
| Scurtături tastatură… | F1 | Lista completă de taste |

### Panou lateral

- Listă cu toate părțile active (I–XIV).
- Buton **Registru final** — editor pe an cu pagini numerotate, bifare pagini, export.

### Bara de instrumente (pe fiecare parte)

- Selector **An** și (unde e cazul) **Lună**.
- **Regenerează zilele** — reconstruiește rândurile zilnice pentru luna curentă.
- **Generează automat** — completează valori aleatoare în range-urile configurate.
- **Range-uri** — setează min/max per coloană numerică.
- **Liste text** — valori predefinite pentru celule tip listă (părți evenimente).
- **Salvează**, **Printează**, **Exportă**.

### Bara de status

- Mesaj contextual pentru acțiunea curentă.
- Indicator **Salvat ✓** cu ora ultimei salvări.
- Banner roșu dacă o salvare a eșuat (cu instrucțiuni de reîncercare).

---

## Scurtături tastatură

| Tastă | Acțiune |
|-------|---------|
| **Ctrl+S** | Salvează pagina curentă |
| **Ctrl+E** | Exportă pagina curentă |
| **Ctrl+R** | Registru complet (overview) |
| **Ctrl+Z** | Anulează ultimele editări în celulă (**până la 10 pași**) |
| **Ctrl+←** | Luna anterioară (părți zilnice/evenimente) |
| **Ctrl+→** | Luna următoare |
| **Ctrl+D** | Duplică rândul selectat (părți evenimente) |
| **Ctrl+,** | Setări bibliotecă |
| **Ctrl+Q** | Ieșire |
| **F1** | Ajutor — scurtături |

---

## Salvare și siguranța datelor

### Salvare automată

- La fiecare **60 de secunde** (dacă există modificări).
- La **schimbarea părții** din meniul stâng.
- La **schimbarea lunii** — salvare amânată în fundal (UI rămâne fluid).
- La **închidere** — flush al modificărilor în așteptare.

### Confirmare la ieșire

Dacă există modificări nesalvate, la închidere apare dialogul: **Salvează / Renunță / Anulează**.

### Sesiune reținută

La repornire, aplicația restaurează ultima **parte**, **an** și **lună** deschise (`app/data/session.json`).

### Backup

| Tip | Când | Păstrare |
|-----|------|----------|
| **Automat** | La fiecare pornire | Ultimele **5** copii (`biblioteca_auto_*.db`) |
| **Manual** | Din meniu Fișier | Nelimitat (în folderul backups) |
| **Pre-restaurare** | Înainte de restaurare | Copie `biblioteca_prerestore_*.db` |

Backup-urile folosesc API-ul SQLite (`sqlite3.backup`) cu checkpoint WAL pentru consistență.

### Bază de date

- **SQLite** cu mod **WAL** (Write-Ahead Logging) pentru performanță și integritate.
- **Indexuri** pe `(an, luna)` pentru interogări rapide.
- **Migrări** de schemă la actualizare (`schema_version`).

### Jurnal (log)

Evenimentele aplicației (pornire, salvare, export, erori) se scriu în `app/data/biblioteca.log` (rotație automată).

---

## Export și printare

### Formate

| Format | Extensie | Motor |
|--------|----------|-------|
| Word | `.docx` | python-docx |
| PDF | `.pdf` | ReportLab |
| Excel | `.xlsx` | openpyxl |

### Domenii export

- **Luna curentă** — doar pagina deschisă.
- **Anul selectat** — toate lunile / categoriile părții curente.
- **Registru complet** — toate părțile (cu dialog de progres și posibilitate de anulare).

### Caracteristici export

- Anteturi de grup pe coloane (subgrupări).
- Rânduri Total și Total de la început.
- Pagină de titlu (copertă) opțională.
- Validare date înainte de generare.
- Mesaje de eroare clare (fișier deschis în alt program, spațiu insuficient etc.).
- Dialog de **progres** la exporturi mari.
- Opțiune de deschidere fișier după export reușit.

### Printare

Previzualizare print din pagina curentă sau din Registru final (orientare landscape, A4).

---

## Registru final și overview

### Registru complet (Ctrl+R)

Dialog modal: arbore cu toate părțile și lunile; bifați ce includeți; export sau previzualizare HTML.

### Registru final (buton lateral)

Pagină dedicată pentru **versiunea numerotată pe an**:

- Arbore cu toate paginile registrului.
- Selectare an.
- Bifare pagini de inclus.
- Dublu-click pe pagină → navigare la editare în partea respectivă.
- Previzualizare și export document final.

---

## Fișiere locale și foldere

```
biblioteca-app/
├── app/
│   ├── main.py                 # Punct de intrare
│   ├── data/
│   │   ├── biblioteca.db       # Baza de date SQLite (NU ȘTERGEȚI)
│   │   ├── biblioteca.log      # Jurnal aplicație
│   │   ├── biblioteca.db-wal   # WAL SQLite (generat automat)
│   │   ├── biblioteca.db-shm   # Shared memory WAL
│   │   ├── session.json        # Ultima parte/an/lună (generat automat)
│   │   └── backups/            # Copii de rezervă .db
│   ├── core/                   # Logică: autosave, sesiune, audit, părți
│   ├── database/               # Modele SQLAlchemy, migrări, backup
│   ├── ui/                     # Interfață PyQt6
│   └── resources/
│       └── stylesheet.qss      # Temă vizuală
├── tests/                      # 29 teste pytest
├── run.bat                     # Pornire aplicație (Windows)
├── build.bat                   # Construire PyInstaller
├── registru.spec               # Configurare PyInstaller
└── requirements.txt
```

**Important:** Copiați periodic folderul `app/data/backups/` pe USB sau alt mediu sigur.

---

## Pornire și instalare

### Cerințe

- **Windows 10/11**
- **Python 3.11+** (doar pentru dezvoltare; utilizatorii finali pot folosi `.exe`)

### Dezvoltare

```bat
cd biblioteca-app
run.bat
```

`run.bat` creează mediul virtual (`venv`), instalează dependențele și pornește aplicația.

### Prima pornire

1. Ecran splash animat la inițializare.
2. Asistent configurare (dacă e prima rulare).
3. Se încarcă ultima sesiune sau Partea I, anul și luna curente.

---

## Construire executabil (.exe)

```bat
cd biblioteca-app
build.bat
```

Rezultat: `dist/RegistruDigital/RegistruDigital.exe` (folder portabil cu dependențe).

---

## Teste automate

```bat
cd biblioteca-app
venv\Scripts\python.exe -m pytest tests\ -v
```

**29 teste** acoperă: backup/restaurare, export PDF/utilitare, salvare roundtrip, agregări SQL, motor date, sesiune, audit luni incomplete, model tabel.

**CI GitHub Actions:** la fiecare push pe `main`, rulează testele pe `windows-latest` cu Python 3.12.

---

## Arhitectură tehnică

| Componentă | Tehnologie |
|------------|------------|
| Interfață | PyQt6 |
| Bază de date | SQLite + SQLAlchemy 2 |
| Export Word | python-docx |
| Export PDF | ReportLab |
| Export Excel | openpyxl |
| Distribuție | PyInstaller |
| Teste | pytest |

### Performanță

- **Încărcare lazy** a părților — fiecare parte se încarcă la prima deschidere.
- **Cache în memorie** pentru lunile vizitate — revenirea la o lună e instantanee.
- **Preîncărcare** a celor 12 luni în fundal după deschiderea unei părți.
- **Agregări SQL** pentru totalul cumulativ (în loc de încărcarea tuturor rândurilor).
- **Salvare amânată** la schimbarea lunii.
- **Splash screen** la pornire.
- **QTableView + QAbstractTableModel** pentru părțile I, III, IV (fără widget-uri complexe în celule).
- **QTableWidget** (legacy) pentru părți cu checkbox-uri, dropdown-uri, text preset.

### Structură cod `PartPageBase`

Clasa de bază a paginilor este împărțită în mixin-uri (`app/ui/parts/mixins/`):

- `ui_mixin` — construire UI, navigare
- `cache_mixin` — cache, preload
- `data_mixin` — persistență DB, generare
- `export_mixin` — export, print, construire pagini

---

## Istoric modificări (changelog)

Toate orele sunt **ora României (UTC+3)** din jurnalul Git.

### 22 iunie 2026

| Ora | Commit | Descriere |
|-----|--------|-----------|
| **12:57** | `a00f579` | **Batch D — Arhitectură:** împărțire `PartPageBase` în 4 mixin-uri; `RegisterTableModel` + `RegisterTableView` (QTableView) pentru părțile I/III/IV; factory tabel automat |
| **12:50** | `8fc12a1` | **Batch C — Siguranță date:** backup SQLite online; banner eroare salvare; undo 10 niveluri; raport „Luni fără date” |
| **12:46** | `98eb9f7` | **Batch B — Fiabilitate:** repornire automată după restaurare; confirmare ieșire cu modificări nesalvate; reținere sesiune (parte/an/lună); Ctrl+←/→ navigare luni |
| **12:42** | `34d5aef` | **Batch A — UX:** fix splash CSS; an/lună curentă implicit; progres export peste tot; antete export comune; folder backup; lazy Registru final; fix Ctrl+R overview |
| **12:37** | `231e046` | **Fix critic:** import `QShortcut` din `QtGui` (PyQt6) — aplicația nu pornea |
| **12:33** | `12dd5a3` | **Performanță + backup + UX:** indexuri DB, agregări SQL, lazy părți, splash, backup/restaurare UI, scurtături F1, export progres, PyInstaller, CI, 22 teste |
| **12:11** | `b4b3a79` | **Fiabilitate export:** validare/erori export, jurnal rotativ, WAL SQLite, autosave la export, teste export |
| **11:56** | `d4099cb` | **Versiune inițială:** aplicație completă PyQt6, 12 părți registru, SQLite, export Word/PDF/Excel |

---

## Depanare rapidă

| Problemă | Soluție |
|----------|---------|
| Aplicația nu pornește | Rulați `run.bat`; verificați `biblioteca.log` |
| „Fișier deschis în alt program” la export | Închideți Word/Excel/PDF deschis cu același nume |
| Date pierdute | Restaurați din `app/data/backups/` — cea mai recentă `biblioteca_auto_*.db` |
| Lună goală la export | Completați în parte sau folosiți „Luni fără date” pentru identificare |
| Salvare eșuată (banner roșu) | Ctrl+S; verificați spațiu pe disc |

---

## Licență și credit

Proiect dezvoltat pentru evidența digitală a bibliotecilor publice. Consultați fișierul sursă `core/constants_manager.py` pentru creditul afișat în aplicație.

---

*Document generat pentru versiunea din commit `a00f579` (22 iunie 2026, 12:57).*
