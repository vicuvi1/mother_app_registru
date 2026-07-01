# Instalator simplu — Registru Digital Bibliotecă (build Windows 7/8/10/11)

Un instalator **cu un singur click** pentru utilizatorii non-tehnici. Persoana care
primește aplicația nu are nevoie de Python, de linia de comandă sau de vreo cunoștință
tehnică — dă dublu-click pe un `.exe`, așteaptă câteva minute și aplicația pornește.

> **Compatibilitate:** această variantă (ramura `pyqt5-win7`) folosește **PyQt5** și
> **Python 3.8**, deci rulează pe **Windows 7 SP1, 8, 8.1, 10 și 11** (64-bit). Pe
> Windows 7/8 instalatorul instalează automat și componentele **Visual C++ 2015–2019**
> necesare (poate apărea o cerere UAC). Ramura `main` folosește PyQt6 + Python 3.12 și
> rulează doar pe Windows 10/11.

Spre deosebire de pipeline-ul PyInstaller + Inno Setup din folderul `installer/`
(care necesită să instalezi Inno Setup și un build de 5–15 min ce produce un `.exe` de
~120 MB), acest instalator:

- **nu necesită Inno Setup** și niciun build greu pe partea de dezvoltator;
- produce un `.exe` **mic** (~5 MB) care poate fi urcat direct pe GitHub;
- **nu necesită drepturi de administrator** — se instalează în `%LOCALAPPDATA%`;
- **nu atinge Python-ul din sistem** — folosește un Python „embeddable" izolat, doar
  pentru această aplicație.

---

## Pentru utilizatorul final

1. Descarcă `Install-RegistruDigital.exe`.
2. Dublu-click pe el.
3. Așteaptă (prima instalare descarcă ~60 MB: Python izolat + bibliotecile aplicației).
4. Aplicația pornește singură, iar pe Desktop apare scurtătura **Registru Digital**.

Data viitoare se pornește direct de pe scurtătura de pe Desktop. Este necesară o conexiune
la internet **doar la prima instalare**.

### Ce se instalează și unde
```
%LOCALAPPDATA%\RegistruDigital\
├── python\        Python 3.8 izolat + bibliotecile (PyQt5, SQLAlchemy, openpyxl, ...)
├── app\           codul aplicației
│   └── data\      baza de date + backup-uri (datele tale)
└── uninstall.ps1  dezinstalator
```

### Dezinstalare
Meniul Start → folderul **Registru Digital** → **Dezinstalare Registru Digital**.
(Șterge scurtăturile și folderul din `%LOCALAPPDATA%`.)

---

## Pentru dezvoltator — cum regenerezi `.exe`-ul

Fișierele aplicației sunt **incluse** (bundle) în interiorul `.exe`-ului, ca o arhivă ZIP
codificată base64. După ce modifici aplicația, regenerează instalatorul:

```powershell
cd app_mother\biblioteca-app\simple-installer
powershell -ExecutionPolicy Bypass -File build-setup-exe.ps1
```

Scriptul:
1. împachetează `app\` (fără folderul `data`) + `requirements-runtime.txt`;
2. inserează arhiva în `install.ps1`;
3. compilează totul într-un singur `Install-RegistruDigital.exe` cu modulul `ps2exe`
   (se instalează automat din PowerShell Gallery dacă lipsește).

### Fișiere
| Fișier | Rol |
|--------|-----|
| `install.ps1` | logica instalatorului (creierul din spatele `.exe`-ului) |
| `uninstall.ps1` | dezinstalator |
| `build-setup-exe.ps1` | împachetează aplicația și compilează `.exe`-ul |
| `registru.ico` | pictograma instalatorului și a scurtăturilor |
| `Install-RegistruDigital.exe` | instalatorul gata de distribuit |

### Testare fără compilare
Poți rula logica direct, cu sursa locală, fără să atingi Desktop-ul:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 `
  -InstallRoot "$env:TEMP\rd_test" `
  -AppSource "..\..\biblioteca-app" `
  -NoShortcut -NoLaunch
```

### Parametri `install.ps1`
| Parametru | Efect |
|-----------|-------|
| `-InstallRoot <cale>` | schimbă folderul de instalare (implicit `%LOCALAPPDATA%\RegistruDigital`) |
| `-AppSource <cale>` | folosește o copie locală a `biblioteca-app` în loc de aplicația inclusă |
| `-NoShortcut` | nu crea scurtături |
| `-NoLaunch` | nu porni aplicația la final |

> Notă: dacă payload-ul inclus lipsește (rulezi `install.ps1` neîmpachetat) și nu dai
> `-AppSource`, scriptul încearcă să descarce aplicația din GitHub. Repo-ul fiind privat,
> distribuția reală se bazează pe aplicația **inclusă** în `.exe`.
