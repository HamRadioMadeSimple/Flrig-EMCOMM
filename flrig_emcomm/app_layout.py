"""Building the main window: header, toolbars, menus, tab buttons, Hotkeys box."""

import sys
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk

from . import look
from . import APP_TITLE, APP_VERSION
from .columns import ALL_COLS, COLDEFS, SORTS, TAB_COLS
from .freq import FREQ_FMT, FREQ_FORMATS, fmt_readout
from .geo import DIST_CHOICES, SCOPES
from .hotkeys import SHORTCUTS
from .look import TEXT_SIZES, THEMES, fit_on_monitor, set_titlebar_dark
from .paths import FROZEN


class LayoutMixin:
    # ------------------------------------------------------------ layout
    def _build_menu(self):
        mb = tk.Menu(self)
        self.menus.append(mb)
        m = tk.Menu(mb, tearoff=False)
        m.add_command(label="Import stations (AI list or CSV)…", command=self.open_import,
                      accelerator="Ctrl+I")
        m.add_command(label="Export CSV…", command=self.export_csv)
        if sys.platform == "win32" or sys.platform.startswith("linux"):
            m.add_separator()
            m.add_command(label="Create desktop shortcut", command=self.make_shortcut)
            if FROZEN:
                self.auto_sc_var = tk.BooleanVar(
                    value=self.data["settings"].get("auto_shortcut", True))
                m.add_checkbutton(label="Keep a desktop icon", variable=self.auto_sc_var,
                                  command=self.toggle_auto_shortcut)
        m.add_separator()
        m.add_command(label="Reset usage counts", command=self.reset_usage)
        m.add_separator()
        m.add_command(label="Exit", command=self.on_close)
        mb.add_cascade(label="File", menu=m)
        self.menus.append(m)

        m = tk.Menu(mb, tearoff=False)
        m.add_command(label="Add station…", command=self.add_entry, accelerator="Ctrl+N")
        m.add_command(label="Add current rig frequency…", command=self.add_current)
        m.add_command(label="Import stations…", command=self.open_import, accelerator="Ctrl+I")
        m.add_command(label="Edit…", command=self.edit_selected, accelerator="F2")
        m.add_command(label="Clone station (new frequency)…", command=self.clone_selected,
                      accelerator="Ctrl+D")
        m.add_command(label="Delete", command=self.delete_selected, accelerator="Del")
        m.add_command(label="Select all on this tab", command=self.select_all,
                      accelerator="Ctrl+A")
        m.add_separator()
        m.add_command(label="Toggle favorite", command=self.toggle_fav_selected, accelerator="F")
        m.add_command(label="Toggle ✔ reliable", accelerator="R",
                      command=lambda: self.toggle_rel(self.selected_ids()))
        m.add_command(label="Move up", command=lambda: self.move_selected(-1),
                      accelerator="Ctrl+Up")
        m.add_command(label="Move down", command=lambda: self.move_selected(1),
                      accelerator="Ctrl+Down")
        m.add_separator()
        m.add_command(label="Search", command=self._focus_search, accelerator="Ctrl+F")
        m.add_separator()
        fm = tk.Menu(m, tearoff=False)
        self.freq_fmt_var = tk.StringVar(value=FREQ_FMT["value"])
        for label, val in FREQ_FORMATS:
            fm.add_radiobutton(label=label, value=val, variable=self.freq_fmt_var,
                               command=lambda v=val: self.set_freq_format(v))
        m.add_cascade(label="Frequency display", menu=fm)
        self.menus.append(fm)
        mb.add_cascade(label="Station", menu=m)
        self.menus.append(m)

        m = tk.Menu(mb, tearoff=False)
        m.add_command(label="New tab…", command=self.new_tab)
        m.add_command(label="Rename tab…", command=self.rename_tab)
        m.add_command(label="Delete tab", command=self.delete_tab)
        m.add_separator()
        m.add_command(label="Next tab", command=lambda: self.step_tab(1), accelerator="Ctrl+Tab")
        m.add_command(label="Previous tab", command=lambda: self.step_tab(-1),
                      accelerator="Ctrl+Shift+Tab")
        m.add_command(label="Go to tab 1 … 9", state="disabled", accelerator="Ctrl+1 … 9")
        m.add_separator()
        m.add_command(label="Move tab left", command=lambda: self.move_tab(-1),
                      accelerator="Ctrl+Shift+Left")
        m.add_command(label="Move tab right", command=lambda: self.move_tab(1),
                      accelerator="Ctrl+Shift+Right")
        m.add_command(label="(Tip: you can also drag a tab to move it)", state="disabled")
        mb.add_cascade(label="Tabs", menu=m)
        self.menus.append(m)

        m = tk.Menu(mb, tearoff=False)
        m.add_command(label="flrig connection…", command=self.connection_settings)
        m.add_command(label="Rig frequency range…", command=self.range_settings)
        m.add_command(label="Home location (for distances)…", command=self.set_home)
        m.add_separator()
        m.add_command(label="ATU Tune (antenna tuner)", command=self.atu_tune,
                      accelerator="Ctrl+T")
        m.add_command(label="Show the station on the rig", command=self.goto_rig_station,
                      accelerator="Ctrl+G")
        mb.add_cascade(label="Rig", menu=m)
        self.menus.append(m)

        m = tk.Menu(mb, tearoff=False)
        for label, val in (("Light", "light"), ("Dark", "dark"), ("Follow system setting", "system")):
            m.add_radiobutton(label=label, value=val, variable=self.theme_var,
                              command=lambda v=val: self.set_theme(v))
        m.add_separator()
        self.size_var = tk.IntVar(value=self.data["settings"].get("ui_scale", 100))
        for label, val in TEXT_SIZES:
            m.add_radiobutton(label=f"Text size: {label}", value=val, variable=self.size_var,
                              command=lambda v=val: self.set_text_size(v))
        m.add_separator()
        m.add_command(label="Switch Light / Dark", command=self.toggle_theme, accelerator="Ctrl+L")
        mb.add_cascade(label="Theme", menu=m)
        self.menus.append(m)

        m = tk.Menu(mb, tearoff=False)
        m.add_command(label="Keyboard shortcuts", command=self.show_shortcuts, accelerator="F1")
        m.add_command(label="Show / hide the Hotkeys box", command=self.toggle_legend)
        mb.add_cascade(label="Help", menu=m)
        self.menus.append(m)
        self.config(menu=mb)

    def _build_rig_panel(self):
        st = self.data["settings"]
        hdr = ttk.Frame(self, style="Hdr.TFrame", padding=(14, 10))
        hdr.pack(fill="x")
        self.logo_lbl = tk.Label(hdr, image=self._logo, bd=0, highlightthickness=0)
        self.logo_lbl.pack(side="left", padx=(0, 10))
        ttk.Label(hdr, text=APP_TITLE, style="HdrTitle.TLabel").pack(side="left")
        ttk.Label(hdr, text=f"v{APP_VERSION}", style="HdrMono.TLabel").pack(side="left",
                                                                         padx=(10, 26))

        def pair(key, value, width=None):
            ttk.Label(hdr, text=key, style="HdrMono.TLabel").pack(side="left")
            v = ttk.Label(hdr, text=value, style="HdrVal.TLabel", width=width)
            v.pack(side="left", padx=(6, 22))
            return v
        ttk.Label(hdr, text="Rig:", style="HdrMono.TLabel").pack(side="left")
        self.dot = tk.Canvas(hdr, width=14, height=14, highlightthickness=0)
        self.dot_id = self.dot.create_oval(2, 2, 12, 12, fill=self.pal["idle"], outline="")
        self.dot.pack(side="left", padx=(6, 2))
        self.lbl_xcvr = ttk.Label(hdr, text="connecting…", style="HdrVal.TLabel", width=15)
        self.lbl_xcvr.pack(side="left", padx=(2, 22))
        self.lbl_host = pair("Host:", st["host"])
        self.lbl_port = pair("Port:", str(st["port"]))
        self.lbl_utc = pair("UTC:", "--:--:--", width=8)
        self.theme_btn = ttk.Button(hdr, text="", style="Hdr.TButton", command=self.toggle_theme)
        self.theme_btn.pack(side="right")
        self._tick_utc()

        panel = ttk.Frame(self, padding=(12, 10, 12, 8))
        panel.pack(fill="x")
        self.lbl_freq = tk.Label(panel, text=fmt_readout(0), font=(look.MONO, 26, "bold"),
                                 padx=16, pady=2, bd=0, highlightthickness=1)
        self.lbl_freq.pack(side="left")
        self.lbl_mode = ttk.Label(panel, text="", style="Mode.TLabel")
        self.lbl_mode.pack(side="left", padx=18)
        self.lbl_station = ttk.Label(panel, text="", style="Station.TLabel")
        self.lbl_station.pack(side="left")
        self.atu_btn = ttk.Button(panel, text="ATU Tune", style="Warn.TButton",
                                  command=self.atu_tune)
        self.atu_btn.pack(side="right", ipadx=8, ipady=4)
        self.lbl_freq.configure(cursor="hand2")
        self.lbl_freq.bind("<Button-1>", lambda ev: self.cycle_freq_format())
        self.lbl_station.configure(cursor="hand2")
        self.lbl_station.bind("<Button-1>", self.goto_rig_station)

    def _tick_utc(self):
        self.lbl_utc.configure(text=datetime.now(timezone.utc).strftime("%H:%M:%S"))
        self.after(1000 - datetime.now().microsecond // 1000, self._tick_utc)

    def _build_toolbars(self):
        bar = ttk.Frame(self, padding=(12, 0, 12, 6))
        bar.pack(fill="x")
        for text, cmd, style in (("Set Rig ▶", self.tune_selected, "Go.TButton"),
                                 ("＋ Add…", self.add_entry, "TButton"),
                                 ("Add current", self.add_current, "TButton"),
                                 ("Edit…", self.edit_selected, "TButton"),
                                 ("★ Favorite", self.toggle_fav_selected, "TButton"),
                                 ("Import…", self.open_import, "Info.TButton"),
                                 ("Delete", self.delete_selected, "Stop.TButton")):
            ttk.Button(bar, text=text, command=cmd, style=style).pack(side="left", padx=(0, 6))
        self.up_btn = ttk.Button(bar, text="▲ Move up", command=lambda: self.move_selected(-1))
        self.up_btn.pack(side="left", padx=(10, 4))
        self.dn_btn = ttk.Button(bar, text="▼ Move down", command=lambda: self.move_selected(1))
        self.dn_btn.pack(side="left")
        for b in (self.up_btn, self.dn_btn):
            b.bind("<Enter>", lambda ev: self._set_status(
                "Move the highlighted station up or down in this tab (Ctrl+↑ / Ctrl+↓). "
                "The tab switches to 'Custom order' so your arrangement sticks."))
            b.bind("<Leave>", lambda ev: self._update_status_count())
        ttk.Label(bar, text="Shared on 2+ tabs", style="Shared.TLabel"
                  ).pack(side="right", padx=(12, 0))
        ttk.Label(bar, text="Double-click = set rig",
                  style="Muted.TLabel").pack(side="right", padx=12)

        find = ttk.Frame(self, padding=(12, 0, 12, 8))
        find.pack(fill="x")
        ttk.Label(find, text="Search:", style="Key.TLabel").pack(side="left")
        self.search_entry = ttk.Entry(find, textvariable=self.search_var, width=22,
                                      style="Search.TEntry")
        self.search_entry.pack(side="left", padx=(4, 2))
        self.search_entry.bind("<Return>", self._search_enter)
        self.search_entry.bind("<Down>", lambda ev: self._focus_first_row(tune=False))
        self.search_entry.bind("<Escape>", lambda ev: self.search_var.set(""))
        ttk.Button(find, text="✕", width=3, command=lambda: self.search_var.set("")
                   ).pack(side="left")
        ttk.Label(find, text="e.g. 7.268 · Thu · country",
                  style="Muted.TLabel").pack(side="left", padx=(6, 10))
        ttk.Label(find, text="Band:", style="Key.TLabel").pack(side="left")
        self.band_cb = ttk.Combobox(find, textvariable=self.band_var, state="readonly", width=9)
        self.band_cb.pack(side="left", padx=(4, 10))
        self.band_cb.bind("<<ComboboxSelected>>", lambda ev: self.refresh_all())
        ttk.Label(find, text="Reach:", style="Key.TLabel").pack(side="left")
        self.reach_cb = ttk.Combobox(
            find, textvariable=self.reach_var, state="readonly", width=13,
            values=["Any reach"] + [f"Within {n} mi" for n in DIST_CHOICES] + SCOPES)
        self.reach_cb.pack(side="left", padx=(4, 10))
        self.reach_cb.bind("<<ComboboxSelected>>", lambda ev: self.refresh_all())
        ttk.Label(find, text="Sort:", style="Key.TLabel").pack(side="left")
        self.sort_cb = ttk.Combobox(find, textvariable=self.sort_var, state="readonly",
                                    values=list(SORTS), width=15)
        self.sort_cb.pack(side="left", padx=(4, 2))
        self.sort_cb.bind("<<ComboboxSelected>>",
                          lambda ev: self.set_sort(self.sort_var.get(), keep_dir=True))
        self.dir_btn = ttk.Button(find, text="↑", width=3, command=self.flip_sort)
        self.dir_btn.pack(side="left")

    def _build_ctx_menu(self):
        self.ctx = tk.Menu(self, tearoff=False)
        self.ctx_also = tk.Menu(self.ctx, tearoff=False)
        self.ctx_move = tk.Menu(self.ctx, tearoff=False)
        self.menus += [self.ctx, self.ctx_also, self.ctx_move]
        self._ctx_vars = []

    def _fill_ctx_menu(self):
        m = self.ctx
        m.delete(0, "end")
        self.ctx_also.delete(0, "end")
        self.ctx_move.delete(0, "end")
        self._ctx_vars = []
        ids = self.selected_ids()
        fid = self.focus_id()
        if not fid:
            return False
        home_ti, e = self.by_id[fid]
        v = self.cur_view()
        if len(ids) == 1:
            m.add_command(label=f"On tabs: {self.tabs_text(e, mark_home=True)}", state="disabled")
            m.add_separator()
        m.add_command(label="Set rig to this station", command=self.tune_selected)
        m.add_command(label="Toggle favorite", command=self.toggle_fav_selected)
        m.add_separator()
        m.add_command(label="Edit…", command=self.edit_selected)
        if len(ids) == 1:
            also = set(self.also_indices(e))
            for i, tab in enumerate(self.data["tabs"]):
                var = tk.BooleanVar(value=(i == home_ti or i in also))
                self._ctx_vars.append(var)
                if i == home_ti:
                    self.ctx_also.add_checkbutton(label=f"{tab['name']} (home)", variable=var,
                                                  state="disabled")
                else:
                    self.ctx_also.add_checkbutton(
                        label=tab["name"], variable=var,
                        command=lambda i=i, eid=fid: self.toggle_also(eid, i))
            m.add_cascade(label="Also show on tab", menu=self.ctx_also)
        for i, tab in enumerate(self.data["tabs"]):
            self.ctx_move.add_command(label=tab["name"], command=lambda i=i: self.move_to_tab(i))
        m.add_cascade(label="Change home tab", menu=self.ctx_move)
        m.add_command(label="Clone station (new frequency)…", command=self.clone_selected)
        m.add_separator()
        if v["kind"] == "tab" and all(self.by_id[i][0] != v["tab"] for i in ids):
            m.add_command(label=f"Remove from {v['label']} tab", command=self.delete_selected)
        else:
            m.add_command(label="Delete station…", command=self.delete_selected)
        return True

    def _build_views(self, select=None):
        for child in self.tabbar.winfo_children():
            child.destroy()
        for t in self.nb.tabs():
            self.nb.forget(t)
        self.views = [{"key": "__fav__", "kind": "fav", "label": "★ Favorites"},
                      {"key": "__all__", "kind": "all", "label": "All Stations"}]
        for i, tab in enumerate(self.data["tabs"]):
            self.views.append({"key": tab["name"], "kind": "tab", "tab": i, "label": tab["name"]})
        for v in self.views:
            frame = ttk.Frame(self.nb)
            cols = ALL_COLS if v["kind"] != "tab" else TAB_COLS
            tree = ttk.Treeview(frame, columns=ALL_COLS, displaycolumns=cols,
                                show="headings", selectmode="extended")
            for col in ALL_COLS:
                head, width, anchor, stretch = COLDEFS[col]
                tree.heading(col, text=self._heading(col), command=lambda c=col: self.sort_by_column(c))
                tree.column(col, width=width, minwidth=30, anchor=anchor, stretch=stretch)
            vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            self._style_tree(tree)
            tree.bind("<ButtonRelease-1>", self._on_click)
            tree.bind("<Double-1>", self._on_double)
            tree.bind("<Button-3>", self._on_right_click)
            tree.bind("<<TreeviewSelect>>", lambda ev: self._show_details())
            tree.bind("<Return>", lambda ev: self.tune_selected())
            tree.bind("<Delete>", lambda ev: self.delete_selected())
            tree.bind("<Key-f>", lambda ev: self.toggle_fav_selected())
            tree.bind("<Key-F>", lambda ev: self.toggle_fav_selected())
            tree.bind("<Key-r>", lambda ev: self.toggle_rel(self.selected_ids()))
            tree.bind("<Key-R>", lambda ev: self.toggle_rel(self.selected_ids()))
            tree.bind("<Motion>", self._tip_motion)
            tree.bind("<Leave>", lambda ev: self._tip_hide())
            v["tree"] = tree
            self.nb.add(frame, text=v["label"])
            v["frame"] = str(frame)
            btn = ttk.Button(self.tabbar, text=v["label"], style="Tab.TButton",
                             takefocus=False, cursor="hand2")
            btn.bind("<ButtonPress-1>", lambda ev, fr=v["frame"]: self._tab_press(ev, fr))
            btn.bind("<B1-Motion>", self._tab_motion)
            btn.bind("<ButtonRelease-1>", self._tab_release)
            v["btn"] = btn
        self.refresh_all()
        if select is not None:
            self.nb.select(min(select, len(self.views) - 1))
        self.after_idle(self._layout_tabbar)
        self._sync_sort_widgets()

    # ------------------------------------------------------------ hotkeys
    def _hotkey(self, fn, in_entry=True):
        """Run a shortcut only in the main window (not in dialogs). Shortcuts that are
        also editing keys (Ctrl+D) are left alone while typing in a box."""
        def handler(ev):
            try:
                w = self.focus_get()
            except (KeyError, tk.TclError):
                w = None
            if w is not None and w.winfo_toplevel() is not self:
                return None
            if not in_entry and isinstance(w, (tk.Entry, ttk.Entry)):
                return None
            fn()
            return "break"
        return handler

    def step_tab(self, delta):
        if self.views:
            self.go_to_view((self.cur_vi() + delta) % len(self.views))

    def go_to_view(self, i):
        if 0 <= i < len(self.views):
            self.nb.select(i)
            self.cur_tree().focus_set()

    def _build_legend(self):
        """Small Hotkeys box over the bottom right of the table; starts closed."""
        self.legend_open = False
        self.legend_btn = ttk.Button(self.status, style="Legend.TButton", takefocus=False,
                                     cursor="hand2", command=self.toggle_legend)
        self.legend_btn.place(relx=1, rely=0.5, anchor="e", x=-4)
        self.legend = ttk.Frame(self, style="Legend.TFrame", padding=(12, 8, 12, 10))
        ttk.Label(self.legend, text="Hotkeys", style="LegendHead.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row = 1
        for keys, what, show in SHORTCUTS:
            if show:
                ttk.Label(self.legend, text=keys, style="LegendKey.TLabel").grid(
                    row=row, column=0, sticky="w", padx=(0, 14))
                ttk.Label(self.legend, text=what, style="Legend.TLabel").grid(
                    row=row, column=1, sticky="w")
                row += 1
        self.legend.bind("<Button-1>", lambda ev: self.toggle_legend())
        self._show_legend()

    def _show_legend(self):
        self.legend_btn.configure(text="⌨ Hotkeys ▾" if self.legend_open else "⌨ Hotkeys ▴")
        if self.legend_open:
            self.legend.place(in_=self.nb, relx=1, rely=1, x=-24, y=-8, anchor="se")
            self.legend.lift()
        else:
            self.legend.place_forget()

    def toggle_legend(self):
        self.legend_open = not self.legend_open
        self._show_legend()

    def show_shortcuts(self):
        """Help > Keyboard shortcuts (F1): every shortcut in one window."""
        if getattr(self, "_keys_win", None) and self._keys_win.winfo_exists():
            self._keys_win.lift()
            return
        win = self._keys_win = tk.Toplevel(self)
        win.title("Keyboard shortcuts")
        win.transient(self)
        win.resizable(False, False)
        frm = ttk.Frame(win, style="Legend.TFrame", padding=(18, 14))
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Keyboard shortcuts", style="LegendHead.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for r, (keys, what, _) in enumerate(SHORTCUTS, start=1):
            ttk.Label(frm, text=keys, style="LegendKey.TLabel").grid(
                row=r, column=0, sticky="w", padx=(0, 18), pady=1)
            ttk.Label(frm, text=what, style="Legend.TLabel").grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text="Single click only highlights a station; it never tunes the rig.",
                  style="Legend.TLabel").grid(row=len(SHORTCUTS) + 1, column=0, columnspan=2,
                                             sticky="w", pady=(10, 0))
        ttk.Button(frm, text="Close", command=win.destroy).grid(
            row=len(SHORTCUTS) + 2, column=1, sticky="e", pady=(12, 0))
        win.bind("<Escape>", lambda ev: win.destroy())
        win.bind("<F1>", lambda ev: win.destroy())
        win.configure(bg=self.pal["bg"])
        set_titlebar_dark(win, self.pal is THEMES["dark"])
        win.update_idletasks()
        _, _, x, y = fit_on_monitor(self, win.winfo_reqwidth(), win.winfo_reqheight(),
                                    self.winfo_rootx() + 120, self.winfo_rooty() + 120)
        win.geometry(f"+{x}+{y}")
        win.focus_set()
