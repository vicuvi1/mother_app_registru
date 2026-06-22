@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
)
venv\Scripts\pip install pyinstaller -q
venv\Scripts\pyinstaller registru.spec --noconfirm
echo.
echo Gata: dist\RegistruDigital\RegistruDigital.exe
pause
