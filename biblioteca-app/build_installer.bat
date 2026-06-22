@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
)
venv\Scripts\pip install pyinstaller cryptography -q
echo [1/2] PyInstaller...
venv\Scripts\pyinstaller registru.spec --noconfirm
if errorlevel 1 exit /b 1
echo.
echo [2/2] Inno Setup (daca iscc este in PATH)...
where iscc >nul 2>&1
if errorlevel 1 (
  echo Inno Setup nu este instalat sau iscc nu e in PATH.
  echo Rulati manual: iscc installer\registru.iss
  echo.
  echo Gata build portabil: dist\RegistruDigital\RegistruDigital.exe
  echo Datele se creeaza in dist\RegistruDigital\data\
  pause
  exit /b 0
)
iscc installer\registru.iss
echo.
echo Gata: installer\output\RegistruDigital_Setup_1.3.0.exe
pause
