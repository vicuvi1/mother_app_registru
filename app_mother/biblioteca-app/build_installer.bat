@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Color codes for output
color 0A

echo.
echo ============================================================
echo   REGISTRU DIGITAL - Build Installer
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not installed or not in PATH
  echo For Windows 7 builds install Python 3.8 (32-bit) from https://www.python.org
  echo   (see BUILD_WINDOWS7.md). Python 3.9+ will NOT run on Windows 7.
  echo.
  pause
  exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist venv\Scripts\python.exe (
  echo [1/5] Creating Python virtual environment...
  python -m venv venv
  if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
  )
  
  echo [2/5] Installing dependencies...
  venv\Scripts\pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
  )
) else (
  echo [1/5] Virtual environment exists
  echo [2/5] Dependencies already installed
)

set "PYTHONPATH=app"

echo [3/5] Generating user guide PDF...
venv\Scripts\python scripts\generate_user_guide.py
if errorlevel 1 (
  echo WARNING: Could not generate user guide, continuing anyway...
)

echo [4/5] Building executable with PyInstaller...
venv\Scripts\pip install pyinstaller -q
venv\Scripts\pyinstaller registru.spec --noconfirm
if errorlevel 1 (
  echo ERROR: PyInstaller build failed
  pause
  exit /b 1
)

echo [5/5] Preparing installer files...
if not exist dist\RegistruDigital\docs mkdir dist\RegistruDigital\docs
if exist app\resources\guides\ghid_bibliotecar.pdf (
  copy /Y app\resources\guides\ghid_bibliotecar.pdf dist\RegistruDigital\docs\ >nul
)

REM Get version
for /f %%V in ('venv\Scripts\python -c "from core.version import APP_VERSION; print(APP_VERSION)"') do set APP_VER=%%V
echo.
echo Application Version: %APP_VER%
echo.

REM Check if Inno Setup is installed
where iscc >nul 2>&1
if errorlevel 1 (
  echo.
  echo ============================================================
  echo   NOTE: Inno Setup is not installed
  echo ============================================================
  echo.
  echo To create the installer, you need to install Inno Setup:
  echo   1. Download from: https://jrsoftware.org/isdl.php
  echo   2. Install it (add to PATH during installation)
  echo   3. Run this script again
  echo.
  echo Portable executable created at:
  echo   dist\RegistruDigital\RegistruDigital.exe
  echo.
  echo You can distribute this EXE directly to users!
  echo.
  pause
  exit /b 0
)

REM Create output directory
if not exist installer\output mkdir installer\output

echo Creating Windows Installer...
iscc /DMyAppVersion=%APP_VER% installer\registru.iss
if errorlevel 1 (
  echo ERROR: Inno Setup build failed
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   SUCCESS!
echo ============================================================
echo.
echo Installer created: installer\output\RegistruDigital_Setup_%APP_VER%.exe
echo.
echo Next steps:
echo   1. Test the installer on your computer
echo   2. Distribute the .exe file to end users
echo   3. Users just need to double-click it to install!
echo.
pause
