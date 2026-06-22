@echo off
title Registru Digital Biblioteca
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creare mediu virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Pornire aplicatie...
python app\main.py
pause
