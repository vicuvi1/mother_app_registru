; Inno Setup — Registru Digital Bibliotecă
; Rulează după: pyinstaller registru.spec

#define MyAppName "Registru Digital Biblioteca"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Victor Bărbuță"
#define MyAppExeName "RegistruDigital.exe"
#define BuildDir "..\dist\RegistruDigital"

[Setup]
AppId={{A8F3C2E1-9B4D-4A2F-8E1C-REGISTRU2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
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

[Languages]
Name: "romanian"; MessagesFile: "compiler:Languages\Romanian.isl"

[Tasks]
Name: "desktopicon"; Description: "Scurtătură pe desktop"; GroupDescription: "Scurtături:"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Dezinstalare {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Pornește {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
