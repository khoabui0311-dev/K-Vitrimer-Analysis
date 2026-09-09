#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{FE35CE06-96C6-4B7F-A692-6785A084BAF0}
AppName=K Vitrimer Analysis
AppVersion={#AppVersion}
AppPublisher=Vo Khoa Bui
DefaultDirName={localappdata}\Programs\K Vitrimer Analysis
DefaultGroupName=K Vitrimer Analysis
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=K_Vitrimer_Analysis_Setup_{#AppVersion}_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\K_Vitrimer_Analysis.exe
CloseApplications=yes
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\K_Vitrimer_Analysis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\K Vitrimer Analysis"; Filename: "{app}\K_Vitrimer_Analysis.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\K Vitrimer Analysis"; Filename: "{app}\K_Vitrimer_Analysis.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\K_Vitrimer_Analysis.exe"; Description: "Launch K Vitrimer Analysis"; Flags: nowait postinstall skipifsilent
