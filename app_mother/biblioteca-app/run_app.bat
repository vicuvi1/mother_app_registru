@echo off
REM Simple launcher for end users - just run the application

cd /d "%~dp0"

if exist "dist\RegistruDigital\RegistruDigital.exe" (
    start "" "dist\RegistruDigital\RegistruDigital.exe"
) else (
    echo Error: RegistruDigital.exe not found
    echo Please run build_installer.bat first to create the application
    pause
)
