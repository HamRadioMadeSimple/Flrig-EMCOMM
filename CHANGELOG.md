# Changelog

## 1.19 (November 2026)

**New**
- Linux release as `FlrigEMCOMM_Ver_1.19_Linux.tar.gz`: ready-built, nothing to compile. Paste three lines (docs/Installing_Flrig_EMCOMM_on_Linux.pdf) and it unpacks into `~/Applications/Flrig EMCOMM Ver 1.19`, adds the menu entry and desktop icon, offers to remove older versions (never newer ones) and starts the app. Updates are the same three lines.
- Linux: the station list, settings and log now live in `~/.local/share/flrig-emcomm`, outside the program folder, so installing, updating or removing never touches them. The first start copies your list from the AppImage folder or the 1.18 install; the old copy is left as a backup.
- Windows: installs in **Program Files (x86)\Flrig EMCOMM** for all users (asks for administrator permission), like RigPanel and DigiApp Launcher. The station list, settings and log now live in `%APPDATA%\Flrig EMCOMM`. The installer removes the old per-user 1.18 install, and the first start copies your list over; the old copy is left as a backup.
- Windows installer: comes to the front after the permission prompt, instead of staying hidden behind other windows as a taskbar button.
- `bash build_linux.sh` makes the .tar.gz (`--appimage` also makes the AppImage), in `output/`.

## 1.18 (October 2026), first public release

**New**
- Windows installer (`FlrigEMCOMM_Setup_1.18.exe`, no admin needed), plus a plain Windows `.exe` and a Linux AppImage: nothing else to install. The app puts its own icon on the desktop (and in the Linux app menu) and keeps its list next to itself.
- App icon (HF rig with radio waves).
- First start asks for your location (grid square or lat, lon) so distances are right.
- ✔ Reliable mark for go-to stations (**R** key, column, "Reliable first" sort).
- Clone a station with a new frequency (Ctrl+D, right-click, or *Save + clone* in Edit); *Save + another freq* in Add.
- Frequency display: kHz, MHz or rig style (7.115.000). Click the big readout to switch.
- Nets split into **Nets-V** (voice) and **Nets-D** (digital).
- Hotkeys box (bottom right) and Help > Keyboard shortcuts (F1); many new shortcuts (Ctrl+Tab, Ctrl+1…9, Ctrl+A, Ctrl+I, Ctrl+L).
- Hovering over a cut-off comment shows all of it.
- Add station starts from the rig's current frequency, mode and filter.
- Window size and position are remembered.
- Linux: proper fonts, follows the system dark mode, dialogs open on the right monitor.
- Linux one-command install: `bash linux_install.sh` builds, installs (menu + desktop icon) and starts the app; `update_linux.sh` updates from the newest zip in Downloads. Your list is kept.
- Problems are written to `flrig_emcomm.log` for bug reports.

**Fixed**
- Import: a closing line from an AI ("Enjoy!") no longer shows up as a broken row.

**Inside**
- Code split from one 4,500-line file into focused modules; icons and the starter station list are now separate files; tests added.

## 1.1 (October 2026)
- Favorites, sorting, search, Emergency Guide stations; tabs, shared stations, import tool with AI prompts, dashboard look, light/dark themes, ATU Tune.

## 1.0
- First version: tabbed station list tuning the IC-7300 through flrig.
