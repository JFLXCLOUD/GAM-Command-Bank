; Inno Setup script for the GAM Command Bank Windows installer.
;
; Build the app folder first, then compile this script:
;   $env:GCB_ONEDIR = "1"; pyinstaller --noconfirm GAM_Command_Bank.spec
;   & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=4.1.0 installer\GAM_Command_Bank.iss
; Output: dist\GAM_Command_Bank_Setup_<version>.exe
;
; Installs per user by default (no admin prompt) into
; %LOCALAPPDATA%\Programs\GAM Command Bank; the first page also offers an
; all-users install into Program Files. User data is never stored in the
; program folder (see installed.marker), so upgrades and uninstalls keep
; the user's commands in %APPDATA%\GAM Command Bank.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "GAM Command Bank"
#define AppExe "GAM_Command_Bank.exe"
#define AppUserModelID "JFLX.GAMCommandBank"
#define RepoURL "https://github.com/JFLXCLOUD/GAM-Command-Bank"

[Setup]
; Never change AppId: it's how upgrades find the existing install.
AppId={{9931015D-45F8-4F34-9E63-B396C894AE10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=JFLX.CLOUD
AppPublisherURL={#RepoURL}
AppSupportURL={#RepoURL}/issues
AppUpdatesURL={#RepoURL}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany=JFLX.CLOUD
VersionInfoDescription={#AppName} Setup

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

OutputDir=..\dist
OutputBaseFilename=GAM_Command_Bank_Setup_{#AppVersion}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\icon.ico
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardSmallImageFile=wizard-small-55.bmp,wizard-small-110.bmp
Compression=lzma2/max
SolidCompression=yes

; close a running copy before upgrading or uninstalling
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; clear the previous version's runtime so no stale files linger after upgrades
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\GAM_Command_Bank\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installed.marker"; DestDir: "{app}"; Flags: ignoreversion
; the app icon, used by the shortcuts and the Apps & features entry
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; AppUserModelID matches the one the app sets, so a pinned shortcut and the
; running window share one taskbar button.
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\icon.ico"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\icon.ico"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
