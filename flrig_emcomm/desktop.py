"""Desktop integration: icons/shortcuts and hiding the Windows console."""

import logging
import os
import re
import sys
from tkinter import messagebox

from . import APP_NAME
from .icons import ensure_icon_file, ensure_png_file
from .paths import APP_DIR, APP_FILE, FROZEN

log = logging.getLogger(__name__)


def hide_console_window():
    """Windows: double-clicking the .py opens a black command window that stays open
    while the app runs. Hide it - but only when the app opened that window itself, never
    when it was started from a Command Prompt or PowerShell window you're using."""
    if sys.platform != "win32" or "--console" in sys.argv:
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32, user32 = ctypes.windll.kernel32, ctypes.windll.user32
        hwnd = k32.GetConsoleWindow()
        if not hwnd:
            return  # started with pythonw / pyw: there is no window to hide
        pids = (wintypes.DWORD * 16)()
        count = k32.GetConsoleProcessList(pids, 16)
        shells = ("cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
                  "openconsole.exe", "conhost.exe")
        for pid in pids[:min(count, 16)]:
            h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                continue
            buf = ctypes.create_unicode_buffer(520)
            size = wintypes.DWORD(520)
            ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
            k32.CloseHandle(h)
            if ok and os.path.basename(buf.value).lower() in shells[:4]:
                return  # someone's own command window: leave it alone
        user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        log.debug("Optional step skipped", exc_info=True)


class DesktopMixin:
    def make_shortcut(self, quiet=False):
        self._remove_old_name_shortcuts()
        if sys.platform.startswith("linux"):
            return self._make_linux_shortcut(quiet)
        return self._make_windows_shortcut(quiet)

    def _make_linux_shortcut(self, quiet=False):
        """Linux: an app-menu entry and a desktop icon (.desktop files)."""
        def q(x):  # quote a path for the Exec line
            return '"' + re.sub(r'([\\"`$])', r"\\\1", x) + '"'
        exe = q(APP_FILE) if FROZEN else f"{q(sys.executable)} {q(APP_FILE)}"
        icon = ensure_png_file() or "utilities-terminal"
        text = ("[Desktop Entry]\nType=Application\nName=Flrig EMCOMM\n"
                "Comment=Station list that tunes your radio through flrig\n"
                f"Exec={exe}\nPath={APP_DIR}\nIcon={icon}\nTerminal=false\n"
                "Categories=HamRadio;Network;Utility;\nStartupWMClass=Flrigemcomm\n")
        made = []
        home = os.path.expanduser("~")
        desktop = os.path.join(home, "Desktop")
        try:
            import subprocess
            r = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True,
                               timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                desktop = r.stdout.strip()
        except Exception:
            log.debug("Optional step skipped", exc_info=True)
        for folder in (os.path.join(home, ".local", "share", "applications"), desktop):
            try:
                if folder == desktop and not os.path.isdir(folder):
                    continue
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, "flrig-emcomm.desktop")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                os.chmod(path, 0o755)
                made.append(path)
                if folder == desktop:
                    try:  # GNOME/Ubuntu: let it launch without "Allow Launching"
                        subprocess.run(["gio", "set", path, "metadata::trusted", "true"],
                                       capture_output=True, timeout=3)
                    except Exception:
                        log.debug("Optional step skipped", exc_info=True)
            except OSError:
                pass
        self.data["settings"]["shortcut_asked"] = True
        self._persist()
        if made:
            self._set_status("Added Flrig EMCOMM to the app menu"
                             + (" and the desktop" if len(made) > 1 else "") + ".")
        elif not quiet:
            messagebox.showinfo(APP_NAME, "Couldn't make the shortcut on this computer.")
        return bool(made)

    def _make_windows_shortcut(self, quiet=False):
        """Windows: a desktop shortcut with the app's icon that opens it with no black
        command window. Safe to run again (it just replaces the shortcut)."""
        ico = ensure_icon_file() or ""
        exe_dir = os.path.dirname(sys.executable)
        target = next((p for p in (os.path.join(exe_dir, "pythonw.exe"),
                                   os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "pyw.exe"))
                       if os.path.exists(p)), sys.executable)
        script = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
                  "[Environment]::GetFolderPath('Desktop')+'\\Flrig EMCOMM.lnk');"
                  "$s.TargetPath=$env:FSM_TARGET;"
                  "$s.Arguments='\"'+$env:FSM_SCRIPT+'\"';"
                  "$s.WorkingDirectory=$env:FSM_DIR;"
                  "if($env:FSM_ICON){$s.IconLocation=$env:FSM_ICON+',0'};"
                  "$s.Description='Flrig EMCOMM';$s.Save()")
        script_arg = APP_FILE  # run.py
        if FROZEN:  # the .exe runs itself: no Python, no arguments
            target, script = sys.executable, script.replace(
                "$s.Arguments='\"'+$env:FSM_SCRIPT+'\"';", "")
            script_arg = ""
        env = dict(os.environ, FSM_TARGET=target, FSM_SCRIPT=script_arg,
                   FSM_DIR=APP_DIR, FSM_ICON=ico)
        try:
            import subprocess
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-Command", script], env=env, capture_output=True,
                               timeout=20, creationflags=0x08000000)  # no window
            ok = r.returncode == 0
        except Exception:
            log.warning("Could not make the Windows desktop shortcut", exc_info=True)
            ok = False
        self.data["settings"]["shortcut_asked"] = True
        self._persist()
        if ok:
            self._set_status("Desktop shortcut made: \"Flrig EMCOMM\". "
                             "Right-click it to pin to the taskbar.")
        elif not quiet:
            messagebox.showinfo(APP_NAME, "Couldn't make the desktop shortcut on this PC.")
        return ok

    def _desktop_dir(self):
        if sys.platform == "win32":
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(520)
                if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:
                    return buf.value  # the real Desktop, even when OneDrive moved it
            except Exception:
                log.debug("Optional step skipped", exc_info=True)
        else:
            try:
                import subprocess
                r = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                   text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                log.debug("Optional step skipped", exc_info=True)
        return os.path.join(os.path.expanduser("~"), "Desktop")

    def _remove_old_name_shortcuts(self):
        """The app used to be called "Flrig Station Manager". Remove its old desktop and
        menu icons so people aren't left with two."""
        old = [os.path.join(self._desktop_dir(), "Flrig Station Manager.lnk"),
               os.path.join(self._desktop_dir(), "flrig-station-manager.desktop"),
               os.path.join(os.path.expanduser("~"), ".local", "share", "applications",
                            "flrig-station-manager.desktop")]
        for path in old:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    log.info("Removed old shortcut %s", path)
                except OSError:
                    log.warning("Could not remove old shortcut %s", path, exc_info=True)

    def _shortcut_file(self):
        name = ("Flrig EMCOMM.lnk" if sys.platform == "win32"
                else "flrig-emcomm.desktop")
        return os.path.join(self._desktop_dir(), name)

    def _auto_shortcut(self):
        """The .exe puts its own icon on the desktop: on first start, and again if the
        .exe was moved or the icon points somewhere else. No questions asked.
        (Turn off with File > Keep a desktop icon.) The .py version asks once instead."""
        if not FROZEN:
            return self._offer_shortcut()
        if os.path.exists(os.path.join(APP_DIR, "unins000.exe")):
            return  # put there by the Windows installer, which handles the desktop icon
        if not (sys.platform == "win32" or sys.platform.startswith("linux")):
            return
        s = self.data["settings"]
        if not s.get("auto_shortcut", True):
            return
        if os.path.exists(self._shortcut_file()) and s.get("shortcut_for") == APP_FILE:
            return
        if self.make_shortcut(quiet=True):
            s["shortcut_for"] = APP_FILE
            self._persist()
            self._set_status("Put a Flrig EMCOMM icon on your desktop.")

    def toggle_auto_shortcut(self):
        s = self.data["settings"]
        s["auto_shortcut"] = bool(self.auto_sc_var.get())
        if s["auto_shortcut"]:
            s.pop("shortcut_for", None)
            self._auto_shortcut()
        else:
            self._persist()
            self._set_status("Desktop icon won't be added again. Delete it from the desktop "
                             "if you don't want it.")

    def _offer_shortcut(self):
        """First start on Windows: offer a desktop shortcut once."""
        s = self.data["settings"]
        if not (sys.platform == "win32" or sys.platform.startswith("linux")) \
                or s.get("shortcut_asked"):
            return
        s["shortcut_asked"] = True
        self._persist()
        if messagebox.askyesno(APP_NAME, "Put a Flrig EMCOMM icon on your desktop"
                               + (" and in the app menu" if sys.platform != "win32" else "")
                               + "?\n\n"
                               "(You can do this later from File > Create desktop shortcut.)"):
            self.make_shortcut()
