#!/bin/bash
# Build script for Linux/Mac users
# Note: The installer .exe can only be built on Windows with Inno Setup
# But you can create the portable executable on any platform with Python

echo "Registru Digital - Build Script (Linux/Mac)"
echo "=============================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1)
if [[ ! $python_version =~ "3.11" ]] && [[ ! $python_version =~ "3.12" ]]; then
    echo "ERROR: Python 3.11+ is required"
    echo "Found: $python_version"
    exit 1
fi

echo "✓ Python found: $python_version"

# Navigate to app directory
cd "$(dirname "$0")/app_mother/biblioteca-app" || exit 1

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q
pip install pyinstaller -q

# Set PYTHONPATH
export PYTHONPATH=app

# Generate user guide (if possible)
echo "Generating user guide..."
python3 scripts/generate_user_guide.py 2>/dev/null || echo "⚠ User guide generation skipped"

# Build with PyInstaller
echo "Building executable with PyInstaller..."
pyinstaller registru.spec --noconfirm

# Prepare output
mkdir -p dist/RegistruDigital/docs
if [ -f "app/resources/guides/ghid_bibliotecar.pdf" ]; then
    cp app/resources/guides/ghid_bibliotecar.pdf dist/RegistruDigital/docs/
fi

echo ""
echo "=============================================="
echo "✓ Build complete!"
echo "=============================================="
echo ""
echo "Portable executable created at:"
echo "  dist/RegistruDigital/RegistruDigital.exe"
echo ""
echo "For Windows Installer:"
echo "  - You must run build_installer.bat on Windows with Inno Setup installed"
echo ""
echo "To run the application now:"
echo "  dist/RegistruDigital/RegistruDigital.exe"
echo ""
