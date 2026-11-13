"""Where the program and its files live (works for .py, .exe and AppImage)."""

import os
import sys


FROZEN = getattr(sys, "frozen", False)  # True when running as the .exe or the AppImage

# This package's own folder (built-in pictures and the starter station list live here)
PKG_DIR = getattr(sys, "_MEIPASS", None)
PKG_DIR = (os.path.join(PKG_DIR, "flrig_emcomm") if PKG_DIR
           else os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PKG_DIR, "assets")

# The file people double-click: the .AppImage (Linux), the .exe (Windows),
# or run.py when running from the source code.
if FROZEN:
    APP_FILE = os.environ.get("APPIMAGE") or sys.executable
else:
    APP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run.py")

APP_DIR = os.path.dirname(os.path.abspath(APP_FILE))
LINUX = sys.platform.startswith("linux")

# The station list, settings and log live outside the program folder, so installing,
# updating or removing the program never touches them:
#  Windows: %APPDATA%\Flrig EMCOMM   (the program is in Program Files)
#  Linux:   ~/.local/share/flrig-emcomm   (the program is in ~/Applications)
HOME = os.path.expanduser("~")
if sys.platform == "win32":
    DATA_DIR = os.path.join(os.environ.get("APPDATA")
                            or os.path.join(HOME, "AppData", "Roaming"), "Flrig EMCOMM")
elif LINUX:
    DATA_DIR = os.path.join(os.environ.get("XDG_DATA_HOME")
                            or os.path.join(HOME, ".local", "share"), "flrig-emcomm")
else:
    DATA_DIR = APP_DIR
DATA_FILE = os.path.join(DATA_DIR, "flrig_stations.json")
OLD_FILE = os.path.join(APP_DIR, "flrig_freqs.json")  # v1 list, imported once
LOG_FILE = os.path.join(DATA_DIR, "flrig_emcomm.log")

# Where versions 1.18 and older kept the list: next to the program (.exe, AppImage or
# source code), the 1.18 Windows installer's folder, or the Linux AppImage folder.
OLD_LIST_DIRS = [APP_DIR,
                 os.path.join(os.environ.get("LOCALAPPDATA")
                              or os.path.join(HOME, "AppData", "Local"), "Programs", "Flrig EMCOMM"),
                 os.path.join(HOME, "Applications", "Flrig EMCOMM")]


def make_data_dir():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError:
        pass


def bring_over_old_list():
    """First start of 1.19 or later: copy the list from where an older version kept it.
    Copy, not move, so the old copy stays as a backup. Returns the folder or None."""
    import shutil
    if os.path.abspath(DATA_DIR) == os.path.abspath(APP_DIR) or os.path.exists(DATA_FILE):
        return None
    for d in OLD_LIST_DIRS:
        src = os.path.join(d, "flrig_stations.json")
        if os.path.abspath(d) != os.path.abspath(DATA_DIR) and os.path.isfile(src):
            try:
                make_data_dir()
                shutil.copy2(src, DATA_FILE)
                return d
            except OSError:
                return None
    return None
