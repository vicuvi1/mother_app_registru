@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
)

set "PYTHONPATH=app"
echo [0/2] Ghid PDF bibliotecar...
venv\Scripts\python scripts\generate_user_guide.py
if errorlevel 1 exit /b 1

venv\Scripts\pip install pyinstaller -q
echo [1/2] PyInstaller...
venv\Scripts\pyinstaller registru.spec --noconfirm
if errorlevel 1 exit /b 1

echo [2/2] Copiere ghid in dist\docs...
if not exist dist\RegistruDigital\docs mkdir dist\RegistruDigital\docs
copy /Y app\resources\guides\ghid_bibliotecar.pdf dist\RegistruDigital\docs\ >nul

echo.
echo Gata: dist\RegistruDigital\RegistruDigital.exe
echo Ghid:  dist\RegistruDigital\docs\ghid_bibliotecar.pdf
pause
