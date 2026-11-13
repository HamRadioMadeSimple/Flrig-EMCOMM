"""The main window. Most of its work lives in the mixins (app_*.py, desktop.py)."""

import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from . import APP_NAME
from .app_layout import LayoutMixin
from .app_list import ListMixin
from .app_look import LookMixin
from .app_rig import RigMixin
from .app_stations import StationsMixin
from .app_tabs import TabsMixin
from .desktop import DesktopMixin
from .freq import DEFAULT_MODES, FREQ_FMT
from .icons import ensure_icon_file, icon_path
from .look import THEMES, fit_on_monitor, monitor_work_area, pick_fonts
from .rig import Flrig
from .stations import load_data, save_data


class App(LayoutMixin, ListMixin, RigMixin, StationsMixin, TabsMixin, LookMixin,
          DesktopMixin, tk.Tk):
    def __init__(self):
        super().__init__(className="FlrigEMCOMM")  # Linux: groups the dock icon
        self.title(APP_NAME)
        pick_fonts(self)
        self.data, load_warning = load_data()
        s = self.data["settings"]
        FREQ_FMT["value"] = s.get("freq_format", "khz")
        self.geometry(s.get("geometry", "1200x700"))
        self.minsize(900, 450)
        self.after(50, lambda: (self._keep_on_screen(),
                                s.get("maximized") and self._maximize()))
        self._geo_job = None
        self.bind("<Configure>", self._on_resize, add="+")

        self.rig = Flrig(s["host"], s["port"])
        self.rig_state = {}
        self.rig_modes = list(DEFAULT_MODES)
        self.connected = None
        self.tune_q = queue.Queue()
        self.ui_q = queue.Queue()
        self.stop_evt = threading.Event()
        self.last_tuned = None  # (entry id, view key) of the last station sent to the rig
        self._rig_id = None     # the one station highlighted as "on the rig"
        self.views = []
        self.by_id = {}

        self.search_var = tk.StringVar()
        self.band_var = tk.StringVar(value="All bands")
        self.reach_var = tk.StringVar(value="Any reach")
        self.sort_var = tk.StringVar()

        self.style = ttk.Style(self)
        self.theme_var = tk.StringVar(value=s.get("theme", "system"))
        self.pal = THEMES[self.resolve_theme()]
        self.menus = []

        self._set_icons()
        self._build_menu()
        self._build_rig_panel()
        self._build_toolbars()
        self.style.layout("Bare.TNotebook.Tab", [])  # real tabs hidden; we draw buttons
        self.tabbar = ttk.Frame(self, padding=(12, 2, 12, 8))
        self.tabbar.pack(fill="x")
        self.tabbar.bind("<Configure>", lambda ev: self._layout_tabbar())
        self.nb = ttk.Notebook(self, style="Bare.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.nb.bind("<<NotebookTabChanged>>", self._on_view_changed)
        self._drag = None
        self.status = ttk.Label(self, text="Starting…", anchor="w", padding=(8, 3))
        self.status.pack(fill="x", side="bottom")
        self.details = ttk.Label(self, text="", anchor="w", padding=(10, 4),
                                 style="Details.TLabel", wraplength=1100, justify="left")
        self.details.pack(fill="x", side="bottom")
        self.details.bind("<Configure>",
                          lambda ev: self.details.configure(wraplength=max(300, ev.width - 20)))
        self._build_ctx_menu()
        self._build_views(select=0)
        self._build_legend()
        self.apply_theme()

        self.search_var.trace_add("write", lambda *a: self.refresh_all())
        threading.Thread(target=self._worker, daemon=True).start()
        self.after(100, self._process_ui_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        keys = [("<Control-f>", self._focus_search, True), ("<Control-n>", self.add_entry, True),
                ("<F2>", self.edit_selected, True), ("<Control-t>", self.atu_tune, True),
                ("<Control-g>", self.goto_rig_station, True),
                ("<Control-Up>", lambda: self.move_selected(-1), True),
                ("<Control-Down>", lambda: self.move_selected(1), True),
                ("<Control-Shift-Left>", lambda: self.move_tab(-1), True),
                ("<Control-Shift-Right>", lambda: self.move_tab(1), True),
                ("<Control-Tab>", lambda: self.step_tab(1), True),
                ("<Control-Shift-Tab>", lambda: self.step_tab(-1), True),
                ("<Control-ISO_Left_Tab>", lambda: self.step_tab(-1), True),  # Linux
                ("<F1>", self.show_shortcuts, True),
                ("<Control-i>", self.open_import, True),
                ("<Control-d>", self.clone_selected, False),
                ("<Control-a>", self.select_all, False),
                ("<Control-l>", self.toggle_theme, True)]
        keys += [(f"<Control-Key-{n}>", lambda n=n: self.go_to_view(n - 1), True)
                 for n in range(1, 10)]
        for seq, fn, in_entry in keys:
            try:
                self.bind(seq, self._hotkey(fn, in_entry))  # main window only
            except tk.TclError:
                pass  # key name not known on this system
        self._persist()
        if load_warning:
            self.after(300, lambda: messagebox.showinfo(APP_NAME, load_warning))
        self.after(1200, self._auto_shortcut)
        if not self.data["settings"].get("home_asked", True):
            self.after(1600, lambda: self.set_home(first_start=True))

    def _set_status(self, text):
        self.status.config(text=text)

    def _persist(self):
        try:
            save_data(self.data)
        except OSError as ex:
            messagebox.showerror(APP_NAME, f"Could not save list:\n{ex}")

    def _set_icons(self):
        """Window/taskbar icon and the logo in the header."""
        try:
            self._icons = [tk.PhotoImage(file=icon_path(n)) for n in (64, 48, 32)]
            self.iconphoto(True, *self._icons)  # True: dialogs get it too
            self._logo = self._icons[1]
        except tk.TclError:
            self._logo = ""
        ico = ensure_icon_file() if sys.platform == "win32" else None
        if ico:
            try:
                self.iconbitmap(default=ico)  # sharpest icon in the Windows title bar
            except tk.TclError:
                pass

    def _keep_on_screen(self):
        """If the saved spot is off every screen (a monitor was unplugged), bring the
        window back onto the nearest screen at the same size."""
        self.update_idletasks()
        left, top, right, bottom = monitor_work_area(self)
        x, y = self.winfo_x(), self.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        if x + 120 > right or x + w - 120 < left or y < top - 20 or y + 60 > bottom:
            nw, nh, nx, ny = fit_on_monitor(self, w, h, x, y)
            self.geometry(f"{nw}x{nh}+{nx}+{ny}")

    def _maximize(self):
        try:
            self.state("zoomed")              # Windows
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)  # Linux
            except tk.TclError:
                pass

    def _is_maximized(self):
        try:
            if self.state() == "zoomed":
                return True
            return bool(self.attributes("-zoomed"))
        except tk.TclError:
            return False

    def _on_resize(self, ev):
        """Window moved or resized: save it a moment later, so it reopens the same way."""
        if ev.widget is not self:
            return
        if self._geo_job:
            self.after_cancel(self._geo_job)
        self._geo_job = self.after(800, self._remember_geometry)

    def _remember_geometry(self):
        self._geo_job = None
        s = self.data["settings"]
        if self.state() not in ("normal", "zoomed"):
            return  # minimized: keep the last real size
        maxed = self._is_maximized()
        geo = s.get("geometry") if maxed else self.geometry()  # keep the normal size too
        if geo != s.get("geometry") or maxed != bool(s.get("maximized")):
            s["geometry"], s["maximized"] = geo, maxed
            self._persist()

    def _save_settings(self):
        s = self.data["settings"]
        s.pop("tune_on_click", None)
        s.pop("dwell", None)
        if self.state() in ("normal", "zoomed"):
            s["maximized"] = self._is_maximized()
            if not s["maximized"]:
                s["geometry"] = self.geometry()
        self._persist()

    def on_close(self):
        self._save_settings()
        self.stop_evt.set()
        self.destroy()
