# Registru Digital Bibliotecă - Distribution Package

A professional digital register management system for libraries with complete Windows installer support.

## 📦 Quick Distribution Guide

### For Developers/IT Managers: Building the Installer

#### Prerequisites
- **Python 3.11+** (from python.org)
- **Inno Setup 6.0+** (from https://jrsoftware.org/isdl.php)
- Windows 7 or newer

#### Build Steps

1. **Navigate to the application directory:**
   ```cmd
   cd app_mother/biblioteca-app
   ```

2. **Run the build script:**
   ```cmd
   build_installer.bat
   ```

3. **Wait for completion** - the script automatically:
   - ✅ Sets up Python virtual environment
   - ✅ Installs all dependencies
   - ✅ Generates documentation
   - ✅ Builds standalone executable
   - ✅ Creates Windows installer

4. **Find your installer:**
   ```
   app_mother/biblioteca-app/installer/output/RegistruDigital_Setup_1.7.0.exe
   ```

---

### For End Users: Installation

**It's as simple as 1-2-3:**

1. **Download** the `RegistruDigital_Setup_1.7.0.exe` file
2. **Double-click** it
3. **Follow the prompts** and click "Finish"

A desktop shortcut is created automatically. Just click it to launch!

**No Python knowledge required.** No command line. No configuration. Just click and go.

---

## 🎯 What This Creates

### Professional Windows Installer
- ✅ Single `.exe` file for distribution
- ✅ Desktop shortcut automatically created
- ✅ Start Menu integration
- ✅ Uninstall support
- ✅ 100+ MB application with all dependencies included
- ✅ User guide PDF included
- ✅ Clean, professional installation wizard

### What Users Get
- ✅ Fully working desktop application
- ✅ All Python dependencies bundled
- ✅ No Python installation required
- ✅ Automatic daily backups
- ✅ User guide
- ✅ Quick setup wizard on first launch

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 7 | Windows 10/11 |
| RAM | 512 MB | 2+ GB |
| Disk Space | 100 MB | 500 MB |
| Network | Not required | Optional backup |

---

## 🚀 Features

### For Librarians
- 📚 User management (children and adults)
- 📖 Document registration and tracking
- 📊 Activity records and statistics
- 🔍 Search and filtering
- 📤 Export to Excel, PDF, Word
- 💾 Automatic daily backups
- 🔄 Data restoration from backups
- 📱 Easy-to-use interface

### For IT Administrators
- 🔧 Single-file deployment
- 💿 No server required
- 🔐 Local data storage (privacy)
- 🚀 Zero configuration needed
- 📦 Portable or installed version
- 🔌 Works offline
- 🎯 Optional network sharing

---

## 📁 Files Included

```
biblioteca-app/
├── build.bat                          # Build portable executable
├── build_installer.bat                # Build Windows installer (recommended)
├── run.bat                           # Run development version
├── run_app.bat                       # Run packaged application
├── DISTRIBUTION.md                  # Detailed distribution guide
├── QUICK_START.txt                  # User quick start guide
├── LICENSE.txt                      # License
├── requirements.txt                 # Python dependencies
├── registru.spec                    # PyInstaller configuration
├── app/                             # Application source code
├── installer/                       # Installer configuration
│   ├── registru.iss                # Inno Setup script
│   ├── BEFORE_INSTALL.txt          # Pre-install instructions
│   ├── AFTER_INSTALL.txt           # Post-install instructions
│   └── output/                     # Generated .exe installer
└── dist/                           # PyInstaller output
    └── RegistruDigital/            # Packaged application
        ├── RegistruDigital.exe     # Standalone executable
        ├── resources/              # Fonts, icons, guides
        └── lib/                    # Bundled Python libraries
```

---

## 🔧 Troubleshooting

### "Python not found" Error
```
Solution:
1. Install Python 3.11+ from python.org
2. During installation, CHECK "Add Python to PATH"
3. Restart command prompt
4. Run build_installer.bat again
```

### "Inno Setup not found" Error
```
Solution:
1. Download Inno Setup from https://jrsoftware.org/isdl.php
2. Install it
3. During installation, CHECK "Add to PATH"
4. Run build_installer.bat again
```

### "Permission denied" During Build
```
Solution:
1. Close any antivirus or security software temporarily
2. Run Command Prompt as Administrator
3. Run build_installer.bat again
```

### Installation Fails on Target Machine
```
Solution:
1. Ensure target machine has 100+ MB free disk space
2. Try running installer as Administrator
3. Check Windows Defender isn't blocking it
4. Try the portable version instead (no installation)
```

---

## 📦 Distribution Options

### Option 1: Professional Installer (Recommended)
- **File:** `RegistruDigital_Setup_1.7.0.exe`
- **Size:** ~100 MB
- **Distribution:** Email, shared drive, or CD
- **Installation:** Users run `.exe` installer
- **Data location:** `C:\Program Files\...`

### Option 2: Portable Executable
- **File:** `dist/RegistruDigital/RegistruDigital.exe`
- **Size:** ~100 MB
- **Distribution:** Zipped folder
- **Usage:** Extract and run directly
- **Installation:** No installation needed

### Option 3: USB Drive
- Copy entire `RegistruDigital_Setup_1.7.0.exe` to USB
- Users can run directly from USB

---

## 🔐 Security & Privacy

- ✅ **Local Storage:** All data stays on the user's computer
- ✅ **No Internet Required:** Works completely offline
- ✅ **No Account Needed:** No registration or login required
- ✅ **Automatic Backups:** Daily backups created automatically
- ✅ **Data Control:** Users have full control of their data
- ✅ **Export Anytime:** Can export data to external formats

---

## 📚 Documentation Included

1. **User Guide** (PDF)
   - Complete feature documentation
   - Step-by-step instructions
   - Screenshots and examples
   - Available in installer

2. **Quick Start** (Text file)
   - 5-minute getting started guide
   - Common tasks
   - Keyboard shortcuts
   - Troubleshooting

3. **Distribution Guide** (Markdown)
   - This document
   - For IT administrators
   - Deployment options
   - Troubleshooting

---

## 🔄 Updates & New Versions

To create an updated installer:

1. Update version number in `app/core/version.py`
2. Run `build_installer.bat` again
3. New `.exe` file will be created automatically
4. Users can install alongside or replace old version

---

## ⚙️ Advanced Options

### Silent Installation
```cmd
RegistruDigital_Setup_1.7.0.exe /S /D=C:\Program Files\Registru
```

### Network Deployment
```cmd
net use Z: \\server\installer
Z:\RegistruDigital_Setup_1.7.0.exe
```

### Customization
Edit `installer/registru.iss` to customize:
- Installation path
- Start menu location
- Desktop shortcut behavior
- License information

---

## 📞 Support

### For Users
1. Check User Guide in Help menu
2. Review Quick Start guide
3. Look for Help > About in application
4. Contact library administrator

### For Administrators
1. Read DISTRIBUTION.md
2. Check Troubleshooting section above
3. Review system requirements
4. Check Windows logs for errors

---

## 📝 License

MIT License - See LICENSE.txt for details

---

## ✨ Version Information

**Current Version:** 1.7.0
**Build Date:** 2026-06-22
**Python:** 3.11+
**Platform:** Windows 7+

---

## 🎉 You're Ready!

The installer is now ready to distribute to your library users. Simply share the `.exe` file with them, and they can install and use the application without any technical knowledge required.

**Happy distributing!**
