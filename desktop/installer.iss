#ifndef AppVersion
  #error AppVersion must be passed by build_windows.ps1
#endif

[Setup]
AppId={{FE35CE06-96C6-4B7F-A692-6785A084BAF0}
AppName=VitriFit
AppVersion={#AppVersion}
AppPublisher=Vo Khoa Bui
DefaultDirName={localappdata}\Programs\VitriFit
DefaultGroupName=VitriFit
UsePreviousGroup=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=VitriFit_Setup_{#AppVersion}_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\VitriFit.exe
CloseApplications=yes
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\VitriFit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Only obsolete launchers and shortcuts; retain the existing AppId for upgrades.
Type: files; Name: "{app}\K_Vitrimer_Analysis.exe"
Type: files; Name: "{autodesktop}\K Vitrimer Analysis.lnk"
Type: files; Name: "{userprograms}\K Vitrimer Analysis\K Vitrimer Analysis.lnk"

[Icons]
Name: "{group}\VitriFit"; Filename: "{app}\VitriFit.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\VitriFit"; Filename: "{app}\VitriFit.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\VitriFit.exe"; Description: "Launch VitriFit"; Flags: nowait postinstall skipifsilent
