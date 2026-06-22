; Inno Setup — Registru Digital Bibliotecă
; Rulează după: build_installer.bat (PyInstaller + copiere ghid)

#ifndef MyAppVersion
#define MyAppVersion "1.7.0"
#endif

#define MyAppName "Registru Digital Biblioteca"
#define MyAppPublisher "Victor Bărbuță"
#define MyAppExeName "RegistruDigital.exe"
#define BuildDir "..\dist\RegistruDigital"

[Setup]
AppId={{A8F3C2E1-9B4D-4A2F-8E1C-REGISTRU2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=RegistruDigital_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\app\resources\registru.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "romanian"; MessagesFile: "compiler:Languages\Romanian.isl"

[Tasks]
Name: "desktopicon"; Description: "Scurtătură pe desktop"; GroupDescription: "Scurtături:"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BuildDir}\docs\ghid_bibliotecar.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{#BuildDir}\docs\ghid_bibliotecar.pdf'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Ghid rapid bibliotecar"; Filename: "{app}\docs\ghid_bibliotecar.pdf"; Check: FileExists(ExpandConstant('{app}\docs\ghid_bibliotecar.pdf'))
Name: "{group}\Dezinstalare {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Pornește {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
