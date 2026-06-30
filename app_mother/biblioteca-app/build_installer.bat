@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
)

set "PYTHONPATH=app"
echo [0/3] Ghid PDF bibliotecar...
venv\Scripts\python scripts\generate_user_guide.py
if errorlevel 1 exit /b 1

venv\Scripts\pip install pyinstaller -q
echo [1/3] PyInstaller...
venv\Scripts\pyinstaller registru.spec --noconfirm
if errorlevel 1 exit /b 1

echo [2/3] Copiere ghid in dist\docs...
if not exist dist\RegistruDigital\docs mkdir dist\RegistruDigital\docs
copy /Y app\resources\guides\ghid_bibliotecar.pdf dist\RegistruDigital\docs\ >nul

for /f %%V in ('venv\Scripts\python -c "from core.version import APP_VERSION; print(APP_VERSION)"') do set APP_VER=%%V
echo Versiune aplicatie: %APP_VER%

echo [3/3] Inno Setup (daca iscc este in PATH)...
where iscc >nul 2>&1
if errorlevel 1 (
  echo Inno Setup nu este instalat sau iscc nu e in PATH.
  echo Rulati manual: iscc /DMyAppVersion=%APP_VER% installer\registru.iss
  echo.
  echo Gata build portabil: dist\RegistruDigital\RegistruDigital.exe
  echo Ghid PDF: dist\RegistruDigital\docs\ghid_bibliotecar.pdf
  pause
  exit /b 0
)

iscc /DMyAppVersion=%APP_VER% installer\registru.iss
if errorlevel 1 exit /b 1
echo.
echo Gata: installer\output\RegistruDigital_Setup_%APP_VER%.exe
pause
