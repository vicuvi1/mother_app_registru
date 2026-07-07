# Running Registru Digital on Windows 7

This app was written for **PyQt6 / Qt6 + Python 3.11+**, which **cannot run on Windows 7**:

- **Python 3.9+ dropped Windows 7.** The last Python that runs on Win7 is **3.8**.
- **Qt6 requires Windows 10+.** The last Qt that supports Win7 is **Qt5 (PyQt5 5.15)**.

The `win7-pyqt5-port` branch ports the code back to **Python 3.8 + PyQt5 5.15**, which does
run on Windows 7. This document explains how to build and deploy it.

---

## Windows 7 prerequisites (install these on the target PC first)

The app itself is fine, but Python 3.8 and the Qt5 libraries need these Windows components.
On a Win7 machine that has been kept up to date these are usually already present.

1. **Windows 7 Service Pack 1 (SP1)** — required.
2. **Universal C Runtime — KB2999226.** Without it, Python 3.8 won't start
   (`api-ms-win-crt-*.dll is missing`). Run full Windows Update, or install KB2999226 manually.
3. **Visual C++ 2015–2022 Redistributable (x86).** The Qt5 DLLs need it
   (`vcruntime140_1.dll`). Download from Microsoft (choose the **x86** file, `vc_redist.x86.exe`).

The installer below **checks for #2 and #3** and shows a clear message if either is missing.

---

## Recommended path: the one-click installer (no Python needed on your PC)

The `simple-installer/` produces a single `Install-RegistruDigital.exe`. The developer machine
only needs **Windows PowerShell** — **no Python required** — because the target Win7 PC
downloads Python 3.8 (32-bit) and PyQt5 itself on first install.

### 1. Build the installer `.exe` (on any Windows PC)

```powershell
cd app_mother\biblioteca-app\simple-installer
powershell -ExecutionPolicy Bypass -File build-setup-exe.ps1
```

This bundles the app source and compiles `Install-RegistruDigital.exe` (installs the `ps2exe`
module automatically the first time).

### 2. Deploy to the Windows 7 PC

1. Make sure the three prerequisites above are installed.
2. Copy `Install-RegistruDigital.exe` to the Win7 PC and double-click it.
3. It downloads Python 3.8 (32-bit) + PyQt5 into `%LOCALAPPDATA%\RegistruDigital`,
   installs the app, and creates a Desktop shortcut. **Internet is required only on first install.**

> 32-bit Python is used on purpose — it runs on both 32-bit and 64-bit Windows 7.

---

## Alternative path: bundled `.exe` with PyInstaller

This produces a self-contained `.exe` (no download at install time), but **you must build it on a
machine with Python 3.8 (32-bit)** — the built exe only runs on the OS family it was built for.

```bat
REM Install Python 3.8.10 (32-bit) from python.org first, then:
cd app_mother\biblioteca-app
install_dependencies.bat        REM creates venv, installs PyQt5 etc.
build_installer.bat             REM PyInstaller build + optional Inno Setup installer
```

Output: `dist\RegistruDigital\RegistruDigital.exe` (portable) and, if Inno Setup is installed,
`installer\output\RegistruDigital_Setup_<ver>.exe`.

> Build on **32-bit** Python 3.8 so the result runs on all Windows 7 editions. The prerequisites
> (KB2999226, VC++ x86 redist) still apply on the target PC.

---

## Running from source on Windows 7 (for testing)

```bat
REM With 32-bit Python 3.8 installed on the Win7 machine:
cd app_mother\biblioteca-app
run.bat            REM first run installs deps into venv, then launches
```

---

## What changed in the port (for reference)

- `PyQt6` → `PyQt5` in all imports (47 files).
- Qt6 scoped enums → PyQt5 unscoped form (`Qt.AlignmentFlag.AlignCenter` → `Qt.AlignCenter`, etc.).
- `QAction` / `QShortcut` moved from `QtGui` back to `QtWidgets` (they relocated in Qt6).
- `QMouseEvent.position().toPoint()` → `.pos()` (Qt5 API).
- High-DPI rounding-policy call wrapped in `try/except` (harmless if unavailable).
- Dependencies pinned to Win7/Python-3.8-compatible versions in `requirements*.txt`.
- `simple-installer/install.ps1` now fetches **Python 3.8.10 (win32)** and installs **PyQt5**,
  with preflight checks for the UCRT and VC++ redistributable.

**Note:** neither Windows 7 nor Python 3.8 receives security updates anymore. This build is
intended for an offline, controlled machine (e.g. a library PC with no internet exposure).
