@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Instalare dependențe — Registru Digital Bibliotecă
cd /d "%~dp0"

echo.
echo ============================================================
echo   Registru Digital Biblioteca - Instalare dependente
echo ============================================================
echo.
echo Acest script pregătește PC-ul pentru prima rulare:
echo   - verifică Python 3.11+
echo   - creează mediul virtual (folder venv)
echo   - instalează PyQt6, SQLite/SQLAlchemy, export Word/PDF/Excel
echo.
echo Durează câteva minute la prima instalare (descărcare pachete).
echo.

REM --- Găsește Python ---
set "PY_CMD="
where python >nul 2>&1
if %errorlevel%==0 (
    python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if !errorlevel!==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    where py >nul 2>&1
    if !errorlevel!==0 (
        for %%V in (3.12 3.13 3.11) do (
            if not defined PY_CMD (
                py -%%V -c "import sys" >nul 2>&1
                if !errorlevel!==0 set "PY_CMD=py -%%V"
            )
        )
    )
)

if not defined PY_CMD (
    echo [EROARE] Python 3.11 sau mai nou nu este instalat.
    echo.
    echo Descărcați Python de la: https://www.python.org/downloads/
    echo La instalare bifați: "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python găsit: %PY_CMD%
%PY_CMD% --version
echo.

REM --- Mediu virtual ---
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creare mediu virtual (venv)...
    %PY_CMD% -m venv venv
    if errorlevel 1 (
        echo [EROARE] Nu s-a putut crea venv.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Mediul virtual există deja — se actualizează pachetele.
)

REM --- pip + dependențe ---
echo [2/3] Actualizare pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
if errorlevel 1 (
    echo [EROARE] pip nu a putut fi actualizat.
    pause
    exit /b 1
)

echo [3/3] Instalare dependențe aplicație...
python -m pip install -r requirements-runtime.txt
if errorlevel 1 (
    echo.
    echo [EROARE] Instalarea dependențelor a eșuat.
    echo Verificați conexiunea la internet și încercați din nou.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Instalare finalizată cu succes!
echo ============================================================
echo.
echo Porniți aplicația dublu-click pe:  run.bat
echo.
echo (Opțional, pentru dezvoltare/teste complete:)
echo   venv\Scripts\pip install -r requirements.txt
echo.
pause
exit /b 0
