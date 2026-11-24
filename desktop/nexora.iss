#define AppName "Nexora"
#define AppVersion "7.0.0"
[Setup]
AppId={{A73F4CB9-276C-4EAF-9E1E-8DF67B99C102}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\Nexora
DefaultGroupName={#AppName}
OutputDir=..\dist-installer
OutputBaseFilename=Nexora-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=nexora.ico
PrivilegesRequired=lowest
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
[Files]
Source: "..\dist\Nexora\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Nexora"; Filename: "{app}\Nexora.exe"
Name: "{autodesktop}\Nexora"; Filename: "{app}\Nexora.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\Nexora.exe"; Description: "Launch Nexora"; Flags: nowait postinstall skipifsilent
