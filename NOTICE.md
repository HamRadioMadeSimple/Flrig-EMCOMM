# Notices and credits

Flrig EMCOMM is Copyright © 2026 KW3KW and is free software under the
GNU General Public License v3.0 or later (see [LICENSE](LICENSE)).

## Programs it works with (not included)

- **flrig** by Dave Freese, W1HKJ, and contributors (GPL), <http://www.w1hkj.org/>.
  Flrig EMCOMM talks to flrig's XML-RPC server. It is an independent project
  and is not part of flrig.

## Included in the ready-built programs

The Windows `.exe`, the Linux `.tar.gz` and the AppImage are made with
**PyInstaller** and carry their own copy of:

- **Python** (Python Software Foundation License), <https://www.python.org/>
- **Tcl/Tk** (BSD-style Tcl/Tk license), <https://www.tcl-lang.org/>
- on Linux, the shared libraries Tk needs (X11, fontconfig, FreeType and
  similar), each under its own free license.

The PyInstaller bootloader is GPL with an exception that allows it in programs
under any license, <https://pyinstaller.org/>. The Windows installer is made
with **Inno Setup** by Jordan Russell, <https://jrsoftware.org/isinfo.php>.

## Starter station list

`flrig_emcomm/data/stations_default.json` lists publicly published
frequencies and schedules of nets, time and weather stations and broadcasters
(for example NIST WWV, USCG and VOLMET weather, the Hurricane Watch Net). The
names belong to their owners. Schedules change: check each organization's own
site before relying on one.

## Icon and screenshots

The app icon and the screenshots in `docs/` were made for this project.
