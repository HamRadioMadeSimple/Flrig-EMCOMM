; Inno Setup script for the Windows installer (FlrigEMCOMM_Setup_<version>.exe).
; build_windows.bat runs this after building the .exe.  Needs Inno Setup 6 (free):
; https://jrsoftware.org/isinfo.php
;
; Installs for all users into Program Files (asks for administrator permission), like
; RigPanel and DigiApp Launcher. The station list and log are in each user's
; %APPDATA%\Flrig EMCOMM, so installing, updating or uninstalling never touches them.
; Removes the old per-user install of version 1.18 and older first (its station list is
; left in place, and the app copies it to %APPDATA% on first start).

#ifndef AppVersion
  #define AppVersion "1.19"
#endif

[Setup]
AppId={{6D1C2F43-6A0E-4C58-9B7E-2E5F3A9C1D84}
AppName=Flrig EMCOMM
AppVersion={#AppVersion}
AppVerName=Flrig EMCOMM {#AppVersion}
AppPublisher=KW3KW
AppComments=Station list that tunes your radio through flrig
DefaultDirName={autopf}\Flrig EMCOMM
DefaultGroupName=Flrig EMCOMM
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=FlrigEMCOMM_Setup_{#AppVersion}
SetupIconFile=flrig_emcomm\assets\icon.ico
UninstallDisplayIcon={app}\FlrigEMCOMM.exe
LicenseFile=LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\FlrigEMCOMM.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Flrig EMCOMM"; Filename: "{app}\FlrigEMCOMM.exe"
Name: "{group}\Uninstall Flrig EMCOMM"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Flrig EMCOMM"; Filename: "{app}\FlrigEMCOMM.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FlrigEMCOMM.exe"; Description: "{cm:LaunchProgram,Flrig EMCOMM}"; Flags: nowait postinstall skipifsilent

[Code]
// After the Windows permission prompt, Setup can open behind other windows and show
// only as a taskbar button. Bring it to the front once, when its first page appears.
const
  FRONT_RESTORE = 9;            // SW_RESTORE
  FRONT_TOPMOST = -1;           // HWND_TOPMOST
  FRONT_NOTOPMOST = -2;         // HWND_NOTOPMOST
  FRONT_FLAGS = $0043;          // SWP_NOSIZE or SWP_NOMOVE or SWP_SHOWWINDOW

var
  BroughtToFront: Boolean;

function FrontShowWindow(hWnd: HWND; nCmdShow: Integer): BOOL;
  external 'ShowWindow@user32.dll stdcall';
function FrontSetWindowPos(hWnd: HWND; hWndInsertAfter: Integer; X, Y, cx, cy: Integer;
  uFlags: Cardinal): BOOL;
  external 'SetWindowPos@user32.dll stdcall';
function FrontSetForeground(hWnd: HWND): BOOL;
  external 'SetForegroundWindow@user32.dll stdcall';

procedure CurPageChanged(CurPageID: Integer);
begin
  if not BroughtToFront then
  begin
    BroughtToFront := True;
    FrontShowWindow(WizardForm.Handle, FRONT_RESTORE);
    FrontSetWindowPos(WizardForm.Handle, FRONT_TOPMOST, 0, 0, 0, 0, FRONT_FLAGS);
    FrontSetWindowPos(WizardForm.Handle, FRONT_NOTOPMOST, 0, 0, 0, 0, FRONT_FLAGS);
    FrontSetForeground(WizardForm.Handle);
  end;
end;

// Version 1.18 and older installed just for the user, in %LOCALAPPDATA%\Programs.
// Uninstall that copy quietly so there is only one Flrig EMCOMM. Its uninstaller only
// removes the files it installed, so the station list stays for the app to copy.
procedure CurStepChanged(CurStep: TSetupStep);
var
  Uninst: String;
  Code: Integer;
begin
  if CurStep = ssInstall then
    if RegQueryStringValue(HKCU,
        'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6D1C2F43-6A0E-4C58-9B7E-2E5F3A9C1D84}_is1',
        'UninstallString', Uninst) then
      Exec(RemoveQuotes(Uninst), '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '',
           SW_HIDE, ewWaitUntilTerminated, Code);
end;
