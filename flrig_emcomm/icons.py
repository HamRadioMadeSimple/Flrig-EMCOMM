"""The app icon: pictures in the assets folder, copied next to the program when needed
(Windows shortcuts use Icon.ico, Linux menus and desktops use Icon.png)."""

import logging
import os
import shutil

from .paths import ASSETS_DIR, DATA_DIR, make_data_dir

log = logging.getLogger(__name__)


def icon_path(size):
    """Path of the built-in icon picture, size 16, 24, 32, 48, 64 or 256."""
    return os.path.join(ASSETS_DIR, f"icon_{size}.png")


def _copy_next_to_app(src, name):
    # Kept with the station list: the program folder may be read-only (Program Files)
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        try:
            make_data_dir()
            shutil.copyfile(src, path)
        except OSError:
            log.warning("Could not write %s", path, exc_info=True)
            return None
    return path


def ensure_png_file():
    """Write Icon.png next to the program (Linux menus and desktop use it)."""
    return _copy_next_to_app(icon_path(256), "Icon.png")


def ensure_icon_file():
    """Write Icon.ico next to the program (Windows shortcut icon). Returns its path or None."""
    return _copy_next_to_app(os.path.join(ASSETS_DIR, "icon.ico"), "Icon.ico")
