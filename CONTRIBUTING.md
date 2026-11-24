# Helping with Flrig EMCOMM

Thanks for helping! Bug reports, station lists and code are all welcome.

## Reporting a problem

Open an issue with:
- what you did and what happened (a screenshot helps a lot)
- Windows or Linux version, and your radio
- the file `flrig_emcomm.log` (in `%APPDATA%\Flrig EMCOMM` on Windows, `~/.local/share/flrig-emcomm` on Linux) (start the app with `--debug` for more detail)

## Running from source

Python 3.8+ with Tk, nothing else. No radio needed for testing: start the pretend flrig first.

```
python3 tests/fake_flrig.py      # in one terminal: a pretend radio on port 12345
python3 run.py                   # in another
```

Tests (on Linux servers, wrap with `xvfb-run`):

```
python3 -m unittest discover -s tests -v
```

## Where things are

The full picture (how the parts fit, the data file, upgrades, builds) is in [ARCHITECTURE.md](ARCHITECTURE.md).

| File | What it does |
| --- | --- |
| `run.py` | Starts the app (also `python -m flrig_emcomm`) |
| `flrig_emcomm/app.py` | The main window; its work is split into the `app_*.py` mixins |
| `app_layout.py` | Header, toolbars, menus, tab buttons, Hotkeys box |
| `app_list.py` | The station table: filling it, filters, sorting, clicks, pop-ups |
| `app_stations.py` | Add, edit, clone, delete, favorite/reliable, move, export |
| `app_tabs.py` | New, rename, delete and drag tabs |
| `app_rig.py` | Tuning: background worker, ATU, rig and home settings |
| `app_look.py` | Themes, text size, frequency display format |
| `desktop.py` | Desktop/menu icons, hiding the Windows console |
| `entry_dialog.py`, `import_dialog.py` | The Add/Edit and Import windows |
| `rig.py` | Talking to flrig (XML-RPC) |
| `stations.py` | Loading, saving and upgrading the station list |
| `importer.py` | AI prompt builder and the CSV / AI-reply reader |
| `freq.py`, `geo.py` | Frequencies, bands, grid squares, distances |
| `look.py` | Colors, fonts, monitors |
| `columns.py`, `hotkeys.py` | Table columns and sorts; the shortcut list |
| `data/stations_default.json` | The starter station list for new users |
| `assets/` | Icon pictures |
| `build_windows.bat` | Builds `dist\FlrigEMCOMM.exe` and, with Inno Setup 6, the installer in `output\` |
| `FlrigEMCOMM.spec`, `FlrigEMCOMM.iss` | The PyInstaller recipe and the Inno Setup installer script |
| `build_linux.sh` | Builds `output/FlrigEMCOMM_Ver_<ver>_Linux.tar.gz` (`--appimage` also makes the AppImage) |
| `linux_install.sh` | Builds the .tar.gz, installs it into `~/Applications/Flrig EMCOMM Ver <ver>` and starts it (`--remove` uninstalls, list kept) |
| `update_linux.sh` | Unpacks the newest `flrig-emcomm*.zip` from ~/Downloads into ~/flrig-emcomm, then runs `linux_install.sh` |
| `.gitattributes` | Keeps `.sh` LF and `.bat`/`.iss` CRLF |

How tuning works: the window never talks to the radio directly. `app_rig.py` queues a job; a background thread (`_worker`) sends it to flrig through `rig.py` and polls the rig once a second; results come back through a queue so the window never freezes.

## Rules the app follows

Please keep these unless there's a good reason (open an issue first):

- **Your list is never changed behind your back.** Imports are reviewed first; no silent duplicates; sharing a station on another tab is done by hand.
- **Old lists always load.** Any change to what's saved needs an upgrade step in `stations.upgrade_data()` and a new data version.
- **Single click highlights, double-click or Enter tunes.** No scanning on HF.
- **The green row is only the station actually on the rig.**
- **No popups for routine actions;** use the status bar.
- **Out-of-range stations stay** in the list, greyed out.
- **Look:** dark header with green readouts, strong contrast, bold text, real buttons.
- **Schedule column is US Eastern time;** original time zones go in Comments.
- **Works on Windows and Linux.** Wrap anything platform-specific so the other one skips it.
- **Standard library only** for the app itself.

## Making a release

Update `APP_VERSION` in `flrig_emcomm/__init__.py` and `CHANGELOG.md`, then push a tag like `v1.19`. GitHub builds the Windows installer and the Linux .tar.gz and AppImage, and publishes the release with that version's CHANGELOG section as its notes. The user guides are PDFs in `docs/`; their Word masters are kept outside the repository.

To build by hand: double-click `build_windows.bat` on Windows, or run `bash build_linux.sh` on Linux.
