@echo off
title Registru Digital Biblioteca
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Prima pornire — se instalează dependențele...
    echo.
    call "%~dp0install_dependencies.bat"
    if errorlevel 1 exit /b 1
    echo.
)

call venv\Scripts\activate.bat

echo Pornire aplicație...
python app\main.py
if errorlevel 1 (
    echo.
    echo Aplicația s-a închis cu o eroare. Verificați app\data\biblioteca.log
    pause
    exit /b 1
)
pause
