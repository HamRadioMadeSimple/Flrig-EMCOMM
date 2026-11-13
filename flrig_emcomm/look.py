"""Colors, fonts, light/dark mode and multi-monitor placement."""

import logging
import re
import sys
from tkinter import font as tkfont

log = logging.getLogger(__name__)


# ==========================================================================
# Themes
# ==========================================================================
THEMES = {
    # header bar stays dark in both themes, like the JS8FastChat dashboard
    "light": dict(bg="#e7ebf1", fg="#0b0f14", field="#ffffff", alt="#d5deeb", head="#c3cedd",
                  head_fg="#151b24", head_border="#7d8aa0", input="#ffffff", input_border="#7d8aa0", button="#d5dce6", active="#c3ccd8", border="#c3cbd6",
                  select="#2563eb", selfg="#ffffff", muted="#475162", fav="#8a5a00", outrange="#7c8696",
                  onfreq="#bfeec5", shared="#d9cdfa", freq_bg="#05140a", freq_fg="#3ef07a",
                  accent="#16803d", ok="#1fa31f", bad="#d33333", idle="#999999",
                  hdr="#0b0f17", hdr_fg="#ffffff", hdr_val="#3ef07a", hdr_key="#d6dbe3",
                  go="#22c55e", go_fg="#04140a", go_act="#3ee07a",
                  stop="#c62828", stop_fg="#ffffff", stop_act="#e03a3a",
                  warn="#f2b01e", warn_fg="#1d1400", warn_act="#ffc845",
                  info="#2563eb", info_fg="#ffffff", info_act="#3b7bff"),
    "dark": dict(bg="#101318", fg="#f7f9fc", field="#0f1626", alt="#25395f", head="#222e44",
                 head_fg="#e6ebf2", head_border="#55647e", input="#2b3649", input_border="#5f6e88", button="#2a313d", active="#3b4453", border="#2c3646",
                 select="#2563eb", selfg="#ffffff", muted="#a6b0bd", fav="#f5c451", outrange="#8d9ab0",
                 onfreq="#1f6236", shared="#3a2d68", freq_bg="#05140a", freq_fg="#3ef07a",
                 accent="#3ef07a", ok="#3ef07a", bad="#ff5252", idle="#777777",
                 hdr="#07080b", hdr_fg="#ffffff", hdr_val="#3ef07a", hdr_key="#d6dbe3",
                 go="#22d160", go_fg="#03120a", go_act="#45f07f",
                 stop="#c62828", stop_fg="#ffffff", stop_act="#e03a3a",
                 warn="#f2b01e", warn_fg="#1d1400", warn_act="#ffc845",
                 info="#2563eb", info_fg="#ffffff", info_act="#3b7bff"),
}


UI_FONT = "Segoe UI"
UI_BOLD = "Segoe UI Semibold"
MONO = "Consolas"
BOLD_WEIGHT = False  # True when the bold face is the plain font made bold (Linux)


def pick_fonts(root):
    """Use Windows' fonts when they're there; on Linux pick the best installed ones."""
    global UI_FONT, UI_BOLD, MONO, BOLD_WEIGHT
    have = {f.lower() for f in tkfont.families(root)}

    def first(*names):
        return next((n for n in names if n.lower() in have), names[-1])
    if "segoe ui" in have:
        UI_FONT = "Segoe UI"
        if "segoe ui semibold" in have:
            UI_BOLD, BOLD_WEIGHT = "Segoe UI Semibold", False
        else:
            UI_BOLD, BOLD_WEIGHT = "Segoe UI", True
    else:
        UI_FONT = first("Ubuntu", "Noto Sans", "Cantarell", "Inter", "DejaVu Sans",
                        "Liberation Sans", "FreeSans", "TkDefaultFont")
        UI_BOLD, BOLD_WEIGHT = UI_FONT, True
    MONO = first("Consolas", "Ubuntu Mono", "DejaVu Sans Mono", "Noto Sans Mono",
                 "Liberation Mono", "FreeMono", "TkFixedFont")


TEXT_SIZES = [("Normal 100%", 100), ("Large 115%", 115), ("Larger 130%", 130),
              ("Extra large 150%", 150)]


def windows_prefers_dark():
    """Is the computer set to dark mode? (Windows setting, or GNOME/Ubuntu/Mint on Linux)"""
    if sys.platform.startswith("linux"):
        try:
            import subprocess
            for key in ("color-scheme", "gtk-theme"):
                r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", key],
                                   capture_output=True, text=True, timeout=2)
                if "dark" in r.stdout.lower():
                    return True
        except Exception:
            log.debug("Optional step skipped", exc_info=True)
        return False
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def monitor_work_area(win):
    """(left, top, right, bottom) of the usable area of the monitor that 'win' is on.
    Tk only knows the main monitor's size, so on Windows we ask Windows directly;
    that keeps dialogs on the same screen as the app on a multi-monitor setup."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
            win.update_idletasks()
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
            mon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if mon and user32.GetMonitorInfoW(mon, ctypes.byref(info)):
                r = info.rcWork
                return r.left, r.top, r.right, r.bottom
        except Exception:
            log.debug("Optional step skipped", exc_info=True)
    if sys.platform.startswith("linux"):
        mons = linux_monitors()
        if mons:
            win.update_idletasks()
            cx = win.winfo_rootx() + win.winfo_width() // 2
            cy = win.winfo_rooty() + win.winfo_height() // 2
            for l, t, r, b in mons:
                if l <= cx < r and t <= cy < b:
                    return l, t, r, b - 40  # leave room for a bottom panel
            l, t, r, b = mons[0]
            return l, t, r, b - 40
    # elsewhere: the whole (virtual) desktop, starting where the window's desktop starts
    x0, y0 = win.winfo_vrootx(), win.winfo_vrooty()
    return (-x0, -y0, -x0 + win.winfo_vrootwidth(), -y0 + win.winfo_vrootheight())


_MONS = {}


def linux_monitors():
    """Each monitor's (left, top, right, bottom), from 'xrandr --listmonitors'.
    Read once; an empty list means 'unknown' (then the whole desktop is used)."""
    if "list" not in _MONS:
        mons = []
        try:
            import subprocess
            out = subprocess.run(["xrandr", "--listmonitors"], capture_output=True,
                                 text=True, timeout=2).stdout
            for m in re.finditer(r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", out):
                w, h, x, y = (int(v) for v in m.groups())
                mons.append((x, y, x + w, y + h))
        except Exception:
            log.debug("Optional step skipped", exc_info=True)
        _MONS["list"] = mons
    return _MONS["list"]


def fit_on_monitor(owner, w, h, x, y, margin=10):
    """Shrink (w, h) and move (x, y) so the window fits on the owner's monitor."""
    left, top, right, bottom = monitor_work_area(owner)
    w = max(200, min(w, right - left - 2 * margin))
    h = max(200, min(h, bottom - top - 2 * margin - 30))  # 30 = title bar
    x = max(left + margin, min(x, right - w - margin))
    y = max(top + margin, min(y, bottom - h - margin - 30))
    return w, h, x, y


def set_titlebar_dark(win, dark):
    """Dark window title bar on Windows 10/11 (ignored elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old builds)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
        win.withdraw()
        win.deiconify()  # forces Windows to repaint the title bar
    except Exception:
        log.debug("Optional step skipped", exc_info=True)
