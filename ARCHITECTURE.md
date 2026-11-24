# Flrig EMCOMM — Architecture

How the program is built, for anyone (person or AI session) about to change it.
Version 1.18, October 2026. Read this before touching code; keep it current when the structure changes.

## 1. In one paragraph

Flrig EMCOMM is a desktop station list that tunes a radio through **flrig**. It is plain **Python 3 (3.7+)** using only the standard library: **Tk/ttk** for the window and **xmlrpc.client** to talk to flrig. The same source runs on **Windows and Linux**. It is shipped as a Windows installer / one-file `.exe` and a Linux AppImage, built with **PyInstaller**. It is planned to be published as open source on **GitHub** under the **GNU GPL v3**.

```
                 ┌──────────────────────── App window (Tk) ────────────────────────┐
  you ─clicks──▶ │ header · toolbar · tabs · station table · Edit / Import windows │
                 └──────┬───────────────────────────────▲────────────────┬─────────┘
                  tune job (queue)                status (queue)     save after
                        ▼                               │            every change
                 ┌─────────────── worker thread ────────┴──┐               ▼
                 │ sends newest job · polls rig every 1 s  │      flrig_stations.json
                 └──────────────┬──────────────────────────┘      (next to the program)
                          rig.py (XML-RPC, 2 s timeout)
                                ▼
                    flrig  127.0.0.1:12345  ──CAT──▶  radio (IC-7300 …)
```

The window never waits on the radio. All radio traffic happens on the worker thread; results come back through a queue that the window checks every 100 ms.

## 2. Project layout

```
flrig-emcomm/
├── run.py                     start the app from source (double-click or: python3 run.py)
├── flrig_emcomm/              the program (a Python package)
│   ├── __init__.py            APP_TITLE, APP_VERSION, APP_NAME
│   ├── __main__.py            main(): logging, hide Windows console, start App
│   ├── paths.py               where things live (.py / .exe / AppImage aware)
│   ├── app.py                 class App(tk.Tk) = the mixins below + startup/shutdown
│   ├── app_layout.py          LayoutMixin: header, toolbars, menus, tab bar, Hotkeys box, F1
│   ├── app_list.py            ListMixin: fill table, filters, sort, clicks, details bar, comment pop-up
│   ├── app_stations.py        StationsMixin: add/edit/clone/delete, ★/✔, move, export CSV
│   ├── app_tabs.py            TabsMixin: new/rename/delete/drag tabs
│   ├── app_rig.py             RigMixin: tune, worker thread, ATU, rig + home settings
│   ├── app_look.py            LookMixin: theme, text size, frequency format, all ttk styles
│   ├── desktop.py             DesktopMixin: desktop/menu icons; hide_console_window()
│   ├── entry_dialog.py        Add / Edit / Clone window
│   ├── import_dialog.py       Import window (AI prompt, paste, review, import)
│   ├── importer.py            prompt builder + CSV / Markdown / AI-reply reader
│   ├── stations.py            load, save, upgrade the list; starter list
│   ├── rig.py                 Flrig class (XML-RPC client)
│   ├── freq.py                bands, frequency parsing/formatting, filter widths
│   ├── geo.py                 grid squares, lat/lon, distance, reach
│   ├── look.py                colors (THEMES), font picking, monitor placement, dark title bar
│   ├── columns.py             table columns (COLDEFS) and sort orders (SORTS)
│   ├── hotkeys.py             SHORTCUTS list (Hotkeys box + F1 window)
│   ├── icons.py               icon files; copies Icon.ico / Icon.png next to the program
│   ├── assets/                icon_16…256.png, icon.ico
│   └── data/stations_default.json   starter list for new users
├── tests/                     test_core.py, test_gui.py, fake_flrig.py
├── build_windows.bat          → dist\FlrigEMCOMM.exe, output\FlrigEMCOMM_Setup_<ver>.exe
├── FlrigEMCOMM.spec           PyInstaller recipe (Windows one-file exe)
├── FlrigEMCOMM.iss            Inno Setup 6 installer script
├── build_linux.sh             → output/FlrigEMCOMM_Ver_<ver>_Linux.tar.gz (--appimage: also the AppImage)
├── linux_install.sh           from source: build the .tar.gz, unpack to ~/Applications, run its installer
├── update_linux.sh            newest zip in ~/Downloads → ~/flrig-emcomm → linux_install.sh
├── packaging/flrig-emcomm.desktop   menu entry inside the AppImage
├── packaging/linux_install.sh       installer inside the .tar.gz (POSIX sh): icons, old-version removal, start
├── requirements.txt           build tool only (pyinstaller); the app needs nothing
├── .github/workflows/         tests.yml (every push), release.yml (tag v* → builds + Release)
├── docs/                      user guides only (PDF): user guide, features, Windows and Linux install
├── images/                    icon and screenshots shown on the README page
├── extras/                    KW3KW_Station_List.csv (optional import, attached to each release)
└── README.md, ARCHITECTURE.md (this file), CHANGELOG.md, CONTRIBUTING.md, NOTICE.md, LICENSE (GPL-3.0)
```

### Dependency direction

Lower layers never import upper ones:

```
app.py ─▶ app_*.py, desktop.py ─▶ entry_dialog, import_dialog ─▶ importer, stations, rig,
                                                                  look, columns, hotkeys, icons
                                                                  ─▶ freq, geo, paths, __init__
```

`look.UI_FONT`, `UI_BOLD`, `MONO`, `BOLD_WEIGHT` are chosen at startup by `look.pick_fonts()`. Other modules must read them as `look.UI_FONT` (not `from .look import UI_FONT`) so they see the chosen value. `freq.FREQ_FMT` is a dict for the same reason.

## 3. The main window (`App`)

`App` is one Tk window assembled from mixins, each in its own file. All mixins share the same `self`; the table below shows who owns which state.

| State on `self` | Owner | Meaning |
| --- | --- | --- |
| `data` | app.py (load) | The whole list: `{"version", "settings", "tabs": [{"id","name","entries":[…]}]}` |
| `views` | app_layout `_build_views` | One per tab button: Favorites, All Stations, then each tab. Each has `tree`, `kind` (`fav`/`all`/`tab`), `key`, `label` |
| `by_id` | app_list `reindex` | station id → (tab index, station dict) |
| `rig`, `rig_state`, `connected` | app_rig | flrig client, last readout, connection flag |
| `tune_q`, `ui_q`, `stop_evt` | app.py / app_rig | worker queues and stop signal |
| `pal`, `style` | app_look | current color palette and ttk styles |

**Views:** a hidden `ttk.Notebook` holds one page (Treeview) per view; the visible tab buttons are drawn by `_layout_tabbar`. A station lives in exactly one tab (its *home*); `also` lists extra tabs it is shown on (lavender rows). Favorites and All Stations are computed views, not stored tabs.

**Refresh:** after any change call `self._persist()` (save) then `self.refresh_all(keep=[ids])` (rebuild every table, keep selection). `refresh_view` applies search + band + reach filters (`matches`) and the view's sort (`SORTS`, saved per view in `settings.sorts`).

**Row colors:** a Treeview tag created first wins. `_style_tree` order: on-rig green, shared, out-of-range, favorite, stripe.

**Fonts:** every size is set in `apply_theme` and scales with Text size. Never hard-code a font elsewhere.

## 4. Tuning flow (double-click)

1. `_on_double` → `tune_selected` → `tune_entry` (app_rig): range check, count the use, remember the station, put a job on `tune_q`.
2. `_worker` thread takes the **newest** job only and calls `Flrig.tune()` (rig.py): `rig.set_mode`, `rig.set_bandwidth`, `rig.set_vfo`.
3. Every second the worker calls `Flrig.status()` and puts the result on `ui_q`.
4. `_process_ui_queue` (every 100 ms, on the Tk thread) updates the header readout and `_mark_current` moves the single green "on rig" row.

ATU Tune calls `rig.tune` the same way and locks the button for 4 s. Only the Tk thread touches widgets.

## 5. Data: `flrig_stations.json`

Saved after every change (`stations.save_data`: write `.tmp`, then swap) in `paths.DATA_DIR`:

| Platform | Folder |
| --- | --- |
| Windows (1.19+) | `%APPDATA%\Flrig EMCOMM`; the installer puts the program in `Program Files (x86)\Flrig EMCOMM` (admin, all users) |
| Linux (1.19+) | `~/.local/share/flrig-emcomm` (`$XDG_DATA_HOME`), for the .tar.gz install, the AppImage and `run.py` alike, so versioned program folders in `~/Applications` never hold user data |

The log `flrig_emcomm.log` (200 KB, one backup) lives in the same folder; so do the generated `Icon.png` / `Icon.ico` (the program folder may be read-only). The first start of 1.19+ copies (never moves, never overwrites) an older list from `APP_DIR`, `%LOCALAPPDATA%\Programs\Flrig EMCOMM` or `~/Applications/Flrig EMCOMM` (`paths.bring_over_old_list`). The 1.19 installer silently uninstalls the old per-user install first; that leaves the list behind for the copy.

**Station fields:** `id` (never changes), `freq_hz`, `mode`, `bw` (Hz or null), `name`, `sched` (US Eastern), `comment`, `location`, `lat`, `lon`, `scope` (Local/State/Region/National/International), `fav`, `rel` (✔ reliable), `uses`, `last_used`, `also` (tab ids).

**Settings:** `host`, `port`, `rig_min_hz`, `rig_max_hz`, `theme`, `ui_scale`, `freq_format`, `geometry`, `maximized`, `sorts`, `view_orders`, `home_lat`, `home_lon`, `home_label`, `home_asked`, `import_preset`, `import_dist`, `import_tab`, `import_requests`, `shortcut_asked`, `auto_shortcut`, `shortcut_for`.

**Upgrades:** `stations.upgrade_data()` brings any older list up to the current version, step by step, and returns notes shown once. **Every change to what is saved needs a new version step here.** A missing settings key must mean "the old behavior".

| Version | Step |
| --- | --- |
| 9 | ✔ Reliable mark (`rel`) on every station |
| 8 | "Nets" split into Nets-V (voice) and Nets-D (digital), with sorts, orders and shares moved |
| 7 | "FM (10m)" → "10m FM"; empty FM Broadcast tab |
| 6 | Reach filled in for built-in stations |
| 5 | Tab ids and shared-station links |
| 4 | Empty CW tab |
| 3 | CB removed; Nets tab added |

Load order: read file → `upgrade_data` → defaults merged into settings → `normalize_entry` on every station → `tidy_tabs`. Unreadable file → renamed `.bad`, starter list loaded, user told. New user → `default_data()` from `data/stations_default.json`, and `home_asked = False` so the first start asks for a location.

**CSV export/import columns:** `tab, frequency_khz, mode, bw, name, schedule, comment, favorite, uses, also_on, location, lat, lon, scope, reliable`. The reader (`importer.parse_station_table`) also accepts the AI format `name, frequency, mode, bw, schedule, comment, location, lat, lon, scope`, Markdown tables, many column spellings, and skips chatter around the table.

## 6. Windows and Linux

One code base. Anything platform-specific is wrapped (`sys.platform == "win32"` / `startswith("linux")`) and fails quietly to the log.

| Area | Windows | Linux | Code |
| --- | --- | --- | --- |
| Fonts | Segoe UI / Semibold / Consolas | best installed (Ubuntu, Noto, Inter, DejaVu…), bold instead of semibold | `look.pick_fonts` |
| Follow system theme | registry `AppsUseLightTheme` | `gsettings` color-scheme / gtk-theme | `look.windows_prefers_dark` |
| Dark title bar | DWM attribute | n/a | `look.set_titlebar_dark` |
| Monitor for dialogs | `MonitorFromWindow` | `xrandr --listmonitors` | `look.monitor_work_area` |
| Desktop icon | PowerShell `.lnk` on the real Desktop (OneDrive aware) | `.desktop` file on Desktop + `~/.local/share/applications` | `desktop.py` |
| Console window | hidden when the .py is double-clicked (`--console` keeps it) | n/a | `desktop.hide_console_window` |
| Dock grouping | — | Tk class `Flrigemcomm` = `StartupWMClass` | `App.__init__` |

**Desktop icon rules:** the built program (`.exe` / AppImage) makes its own icon on first start and repairs it if the program moves (`settings.shortcut_for`), unless File > Keep a desktop icon is off, or the Windows installer put it there (`unins000.exe` next to the exe). Running from source asks once instead. Old "Flrig Station Manager" icons are removed.

## 7. Building and releasing

| Output | How | Notes |
| --- | --- | --- |
| `dist\FlrigEMCOMM.exe` | `build_windows.bat` (uses `FlrigEMCOMM.spec`) | one file, no console; needs Python on the build PC only |
| `output\FlrigEMCOMM_Setup_<ver>.exe` | same .bat, if Inno Setup 6 is installed (`FlrigEMCOMM.iss`) | installs in Program Files for all users (admin prompt); uninstall keeps the list |
| `output/FlrigEMCOMM_Ver_<ver>_Linux.tar.gz` | `bash build_linux.sh` | PyInstaller one-folder in `Flrig EMCOMM Ver <ver>/` + `linux_install.sh` + the Linux install guide and user guide (PDF); build on the oldest Linux to support |
| `output/FlrigEMCOMM-x86_64.AppImage` | `bash build_linux.sh --appimage` | the same program + appimagetool |
| All of the above on GitHub | push tag `vX.Y` | `release.yml`: Windows on windows-latest, .tar.gz and AppImage on Ubuntu 22.04 (run on Mint 21+) |

The version number lives only in `flrig_emcomm/__init__.py` (`APP_VERSION`); the .bat passes it to the installer. Assets and the starter list are bundled with `--add-data`; at run time `paths.PKG_DIR` finds them inside the .exe / AppImage (`sys._MEIPASS`).

## 8. Testing

No radio needed: `tests/fake_flrig.py` is a pretend flrig (XML-RPC on 127.0.0.1) that records calls.

```
python3 -m unittest discover -s tests -v        # on a Linux server: xvfb-run -a python3 -m unittest …
```

- `test_core.py`: frequency typing and formats, bands, grid squares and distance, the import reader (AI reply, export round trip), starter list, upgrading a v7 list, save/load.
- `test_gui.py`: opens the real window against the fake flrig; tunes WWV, toggles ★/✔, clones, switches frequency format, checks it was saved.

GitHub runs these on every push (`tests.yml`). For visual changes also take screenshots in both themes.

## 9. Rules for changing the code

- **Patch, don't rewrite.** Small, tested steps; run all tests after each.
- **Never break an existing list.** New saved field or setting → upgrade step in `upgrade_data` + data version bump + a test.
- **Standard library only** for the app (the build may use PyInstaller / Inno Setup).
- **Both platforms.** Wrap platform code; log, don't crash, when an optional step fails (`log.debug(..., exc_info=True)`).
- **Widgets only on the Tk thread.** The worker talks to flrig and the queues, nothing else.
- **Fonts and colors only in `apply_theme` / `THEMES`.**
- **The user's design rules** (README/CONTRIBUTING): nothing changes the list behind the user's back, single click highlights / double-click tunes, no HF scanning, one green on-rig row, no popups for routine actions, out-of-range stations stay greyed, Schedule is US Eastern, dashboard look with strong contrast.
