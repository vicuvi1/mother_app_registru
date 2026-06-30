# Distribution Guide - Registru Digital Bibliotecă

## For Developers: Building the Installer

### Prerequisites
- Windows 7+
- Python 3.11+ installed and in PATH
- **Inno Setup 6.0+** (for creating the installer)
  - Download from: https://jrsoftware.org/isdl.php
  - During installation, **check "Add to PATH"**

### Option 1: Create Professional Installer (Recommended for Distribution)

1. **Run the build script:**
   ```
   double-click: build_installer.bat
   ```

2. **Wait for completion** - the script will:
   - ✅ Create Python virtual environment
   - ✅ Install all dependencies
   - ✅ Generate user guide PDF
   - ✅ Build standalone EXE with PyInstaller
   - ✅ Create Windows installer with Inno Setup

3. **Find your installer:**
   ```
   installer/output/RegistruDigital_Setup_1.7.0.exe
   ```

4. **Distribute this .exe file** to your users!

### Option 2: Portable Executable (No Installation Required)

If you don't have Inno Setup installed:

1. Run `build_installer.bat` - it will create the standalone executable
2. Find: `dist/RegistruDigital/RegistruDigital.exe`
3. Zip the entire `dist/RegistruDigital/` folder
4. Users can extract and run directly (no installation needed)

---

## For End Users: Installing the Application

### Requirements
- Windows 7 or newer
- 100 MB free disk space
- No Python knowledge required!

### Installation Steps (Option 1: Professional Installer)

1. **Download** `RegistruDigital_Setup_1.7.0.exe` from your IT staff
2. **Double-click** the installer
3. **Follow the prompts:**
   - Accept the license
   - Choose installation location (usually `C:\Program Files\...`)
   - Click "Install"
4. **Finish!** - Desktop shortcut is automatically created

### First Launch

1. **Click** the desktop shortcut or find it in Start Menu
2. **Setup wizard** will appear on first launch
3. **Configure** your library information
4. **Start using** the application!

### What Gets Installed

- ✅ Registru Digital application
- ✅ User guide (PDF)
- ✅ All required libraries
- ✅ Desktop shortcut
- ✅ Start Menu entry
- ✅ Uninstall option

### Data & Backups

- Your library data is stored in: `C:\Users\[YourName]\AppData\Local\Registru Digital Bibliotecă`
- **Automatic daily backups** are created
- You can export data to Excel, PDF, or Word anytime

### Getting Help

1. **In-app Help** - Look for Help menu
2. **User Guide** - Start Menu > Registru Digital > User Guide
3. **Contact** your system administrator

---

## For System Administrators

### Deployment Options

#### Option A: Individual User Installation
- Distribute installer to each library
- Users run it themselves
- Each computer is independent

#### Option B: Network Deployment
- Create a shared folder with the installer
- Users access it from the network
- Each installation is local

#### Option C: Automated Deployment
For large organizations, you can:
- Deploy using Group Policy
- Use deployment scripts
- Silent installation: `RegistruDigital_Setup_1.7.0.exe /S /D=C:\Program Files\Registru Digital`

### Network Considerations
- Application works **offline** - no internet required
- Optional cloud backup can be enabled
- No server installation needed

### Troubleshooting

**"Python not found"**
- Ensure Python 3.11+ is installed
- Add Python to PATH: https://docs.python.org/3/using/windows.html

**"Permission denied during installation"**
- Run installer as Administrator
- Check disk space (needs 100+ MB)

**"Application won't start"**
- Try reinstalling
- Clear temp files: `C:\Users\[YourName]\AppData\Local\Temp`
- Check Windows Defender isn't blocking it

---

## Building Without Inno Setup

If you can't install Inno Setup on your system:

1. Run `build.bat` instead of `build_installer.bat`
2. This creates a portable executable in `dist/RegistruDigital/`
3. Zip the folder and distribute to users
4. Users extract and run directly - no installation needed

---

## Version Information

Current Version: **1.7.0**
Build Date: **2026-06-22**

Check version in-app: Help > About

---

## Security & Privacy

- ✅ All data is stored **locally** on each computer
- ✅ No data sent to external servers (unless explicitly configured)
- ✅ Regular backups created automatically
- ✅ Standard Windows permissions apply
- ✅ Compliant with data protection regulations

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 7 | Windows 10/11 |
| RAM | 512 MB | 2+ GB |
| Disk Space | 100 MB | 500 MB |
| Screen Resolution | 1024x768 | 1920x1080 |

---

## Uninstallation

**Option 1: Standard Uninstall**
- Windows Settings > Apps > Registru Digital > Uninstall

**Option 2: Control Panel**
- Control Panel > Programs > Programs and Features
- Find "Registru Digital Bibliotecă"
- Click Uninstall

**Option 3: Desktop Shortcut**
- All application files can be deleted manually
- User data (if stored locally) will NOT be deleted

---

## Support

For issues or questions:
1. Check the User Guide (PDF)
2. Review in-app Help menu
3. Contact your system administrator
4. Check logs: `C:\Users\[YourName]\AppData\Local\Registru Digital Bibliotecă\logs`

---

**Ready to distribute!** 🎉
