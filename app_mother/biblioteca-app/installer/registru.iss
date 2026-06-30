; Inno Setup Script for Registru Digital Bibliotecă
; This script creates a professional Windows installer

#ifndef MyAppVersion
#define MyAppVersion "1.7.0"
#endif

#define MyAppName "Registru Digital Bibliotecă"
#define MyAppPublisher "Biblioteca"
#define MyAppExeName "RegistruDigital.exe"
#define MyAppIcon "..\dist\RegistruDigital\RegistruDigital.exe"

[Setup]
AppId={{8B7D6E5F-9A2C-4D1B-8E3F-5C9D7A6B2E1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=RegistruDigital_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE.txt
InfoBeforeFile=BEFORE_INSTALL.txt
InfoAfterFile=AFTER_INSTALL.txt

; Language and messages
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "romanian"; MessagesFile: "compiler:Languages\Romanian.isl"

; Custom pages
[CustomMessages]
english.WelcomeLabel2=This will install Registru Digital Bibliotecă on your computer. %n%nRegistru Digital is a digital register for libraries to track activities, users, and documents.%n%nClick Next to continue.
romanian.WelcomeLabel2=Aceasta va instala Registru Digital Bibliotecă pe calculatorul dvs.%n%nRegistru Digital este o evidență digitală pentru biblioteci care permite urmărirea activităților, utilizatorilor și documentelor.%n%nFaceți clic pe Următorul pentru a continua.

[Files]
; Copy all files from the PyInstaller output directory
Source: "..\dist\RegistruDigital\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\RegistruDigital\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: docs

[Icons]
; Desktop shortcut
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconIndex: 0; WorkingDir: "{app}"

; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\User Guide"; Filename: "{app}\docs\ghid_bibliotecar.pdf"; Components: docs
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Show user guide after installation (optional)
Filename: "{app}\docs\ghid_bibliotecar.pdf"; Description: "View User Guide"; Flags: shellexec postinstall skipifsilent unchecked; Components: docs

; Run the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Uninstall]
Type: files; Name: "{app}\*"
Type: dirsifempty; Name: "{app}"

[InstallDelete]
; Clean up old versions
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeLabel2');
end;
