"""Themes, text size and frequency display format."""

import tkinter as tk

from . import look
from .columns import ALL_COLS, COLDEFS
from .freq import FREQ_FMT, FREQ_FORMATS, fmt_readout
from .look import THEMES, fit_on_monitor, set_titlebar_dark, windows_prefers_dark


class LookMixin:
    # ------------------------------------------------------------ theme
    def resolve_theme(self):
        t = self.data["settings"].get("theme", "system")
        if t not in THEMES:
            t = "dark" if windows_prefers_dark() else "light"
        return t

    def set_theme(self, value):
        self.data["settings"]["theme"] = value
        self.theme_var.set(value)
        self._persist()
        self.apply_theme()

    def set_text_size(self, value):
        self.data["settings"]["ui_scale"] = value
        self._persist()
        self.apply_theme()
        # bigger text needs a wider window; grow it (up to the screen) so nothing is cut off
        k = value / 100
        w, h = self.winfo_width(), self.winfo_height()
        if w < round(1250 * k) or h < round(760 * k):
            nw, nh, x, y = fit_on_monitor(self, max(w, round(1250 * k)), max(h, round(760 * k)),
                                          self.winfo_x(), self.winfo_y())
            self.geometry(f"{nw}x{nh}+{x}+{y}")

    def set_freq_format(self, value):
        """Change how frequencies show: the readout, every tab and the details bar."""
        FREQ_FMT["value"] = value
        self.data["settings"]["freq_format"] = value
        self.freq_fmt_var.set(value)
        self._persist()
        for v in self.views:
            v["tree"].heading("freq", text=self._heading("freq"))
        self.refresh_all()
        self.lbl_freq.config(text=fmt_readout(self.rig_state.get("freq") if self.connected else 0))
        self._show_details()
        name = next(lbl for lbl, val in FREQ_FORMATS if val == value)
        self._set_status(f"Frequency display: {name.split('(')[0].strip()}")

    def cycle_freq_format(self):
        """Click the big readout: kHz -> MHz -> Rig style -> kHz."""
        order = [val for _, val in FREQ_FORMATS]
        self.set_freq_format(order[(order.index(FREQ_FMT["value"]) + 1) % len(order)])

    def toggle_theme(self):
        self.set_theme("light" if self.resolve_theme() == "dark" else "dark")

    def _style_tree(self, tree):
        p = self.pal
        # Tk gives priority to the tag created first, so the highlight goes first
        tree.tag_configure("onfreq", background=p["onfreq"])
        tree.tag_configure("shared", background=p["shared"])
        tree.tag_configure("outrange", foreground=p["outrange"])
        tree.tag_configure("fav", foreground=p["fg"])
        tree.tag_configure("odd", background=p["alt"])

    def apply_theme(self):
        name = self.resolve_theme()
        p = self.pal = THEMES[name]
        st = self.style
        st.theme_use("clam")
        k = self.data["settings"].get("ui_scale", 100) / 100

        def f(size, *style, face=look.UI_FONT):
            if face == look.UI_BOLD and look.BOLD_WEIGHT and "bold" not in style:
                style = (*style, "bold")  # no semibold font here: use bold instead
            return (face, max(7, round(size * k)), *style)
        ui, bold = f(10), f(10, face=look.UI_BOLD)
        st.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                     bordercolor=p["border"], lightcolor=p["bg"], darkcolor=p["bg"],
                     troughcolor=p["bg"], selectbackground=p["select"],
                     selectforeground=p["selfg"], insertcolor=p["fg"], arrowcolor=p["fg"],
                     focuscolor=p["select"], font=ui)
        st.map(".", foreground=[("disabled", p["muted"])])

        # buttons: bold, flat, roomy; coloured ones for the main actions
        st.configure("TButton", background=p["button"], foreground=p["fg"], font=bold,
                     padding=(12, 5), width=-4, relief="flat", borderwidth=1,
                     bordercolor=p["border"], lightcolor=p["button"], darkcolor=p["button"])
        st.map("TButton",
               background=[("disabled", p["bg"]), ("pressed", p["select"]), ("active", p["active"])],
               lightcolor=[("active", p["active"])], darkcolor=[("active", p["active"])],
               foreground=[("disabled", p["muted"]), ("pressed", p["selfg"])])
        for sty, bg_, fg_, act in (("Go", "go", "go_fg", "go_act"),
                                   ("Stop", "stop", "stop_fg", "stop_act"),
                                   ("Warn", "warn", "warn_fg", "warn_act"),
                                   ("Info", "info", "info_fg", "info_act")):
            st.configure(f"{sty}.TButton", background=p[bg_], foreground=p[fg_],
                         bordercolor=p[bg_], lightcolor=p[bg_], darkcolor=p[bg_], font=bold)
            st.map(f"{sty}.TButton",
                   background=[("disabled", p["button"]), ("pressed", p[act]), ("active", p[act])],
                   lightcolor=[("active", p[act])], darkcolor=[("active", p[act])],
                   foreground=[("disabled", p["muted"])])
        st.configure("Hdr.TButton", background="#1f2530", foreground="#ffffff",
                     bordercolor="#2c3442", lightcolor="#1f2530", darkcolor="#1f2530")
        st.map("Hdr.TButton", background=[("active", "#2e3644")],
               lightcolor=[("active", "#2e3644")], darkcolor=[("active", "#2e3644")])

        st.configure("TCheckbutton", background=p["bg"], indicatorbackground=p["field"],
                     indicatorforeground=p["fg"])
        st.map("TCheckbutton", background=[("active", p["bg"])],
               indicatorbackground=[("selected", p["select"]), ("active", p["field"])],
               indicatorforeground=[("selected", p["selfg"])])
        for w in ("TEntry", "TCombobox", "TSpinbox"):
            st.configure(w, fieldbackground=p["input"], foreground=p["fg"], padding=4,
                         background=p["button"], insertcolor=p["fg"], font=ui,
                         bordercolor=p["input_border"], lightcolor=p["input"],
                         darkcolor=p["input"], arrowcolor=p["fg"])
            st.map(w, fieldbackground=[("readonly", p["input"]), ("disabled", p["bg"])],
                   foreground=[("readonly", p["fg"]), ("disabled", p["muted"])],
                   lightcolor=[("focus", p["input"])], darkcolor=[("focus", p["input"])],
                   selectbackground=[("readonly", "!focus", p["input"])],
                   selectforeground=[("readonly", "!focus", p["fg"])],
                   background=[("active", p["active"])],
                   bordercolor=[("focus", p["select"])])
        st.configure("Search.TEntry", padding=5)
        self.option_add("*TCombobox*Listbox.font", ui)

        # station table
        st.configure("Treeview", background=p["field"], fieldbackground=p["field"],
                     foreground=p["fg"], rowheight=round(31 * k), font=f(10.5, face=look.UI_BOLD),
                     bordercolor=p["border"], borderwidth=0)
        st.map("Treeview", background=[("selected", p["select"])],
               foreground=[("selected", p["selfg"])])
        # each column heading is its own bordered cell, set apart from the rows below
        st.configure("Treeview.Heading", background=p["head"], foreground=p["head_fg"],
                     font=f(9, "bold"), relief="solid", padding=(4, 8), borderwidth=1,
                     bordercolor=p["head_border"], lightcolor=p["head"], darkcolor=p["head"])
        st.map("Treeview.Heading", background=[("active", p["active"])],
               lightcolor=[("active", p["active"])], darkcolor=[("active", p["active"])])

        # tabs are drawn as buttons; the notebook itself is just a borderless page holder
        st.layout("Bare.TNotebook.Tab", [])
        st.configure("Bare.TNotebook", background=p["bg"], borderwidth=0, tabmargins=0,
                     bordercolor=p["border"])
        st.configure("Tab.TButton", background=p["button"], foreground=p["fg"],
                     font=f(10.5, face=look.UI_BOLD), padding=(11, 6), width=-2,
                     bordercolor=p["border"], lightcolor=p["button"], darkcolor=p["button"])
        st.map("Tab.TButton", background=[("pressed", p["active"]), ("active", p["active"])],
               lightcolor=[("active", p["active"])], darkcolor=[("active", p["active"])])
        st.configure("TabSel.TButton", background=p["select"], foreground="#ffffff",
                     font=f(10.5, face=look.UI_BOLD), padding=(11, 6), width=-2,
                     bordercolor=p["select"], lightcolor=p["select"], darkcolor=p["select"])
        st.map("TabSel.TButton", background=[("active", "#3b7bff")],
               lightcolor=[("active", "#3b7bff")], darkcolor=[("active", "#3b7bff")])
        st.configure("TNotebook", background=p["bg"], bordercolor=p["border"],
                     tabmargins=(2, 4, 2, 0))
        st.configure("TNotebook.Tab", background=p["head"], foreground=p["muted"],
                     padding=(12, 6), font=f(10, face=look.UI_BOLD), bordercolor=p["border"])
        st.map("TNotebook.Tab", background=[("selected", p["select"]), ("active", p["active"])],
               foreground=[("selected", "#ffffff"), ("active", p["fg"])],
               lightcolor=[("selected", p["select"])])
        st.configure("Vertical.TScrollbar", background=p["button"], troughcolor=p["bg"],
                     arrowcolor=p["fg"], bordercolor=p["border"])
        st.map("Vertical.TScrollbar", background=[("active", p["active"])])

        # labels
        st.configure("Key.TLabel", font=f(10, face=look.UI_BOLD))
        st.configure("Muted.TLabel", foreground=p["muted"], font=f(9.5, face=look.UI_BOLD))
        st.configure("Accent.TLabel", foreground=p["accent"], font=f(11))
        st.configure("Big.TLabel", font=f(13, face=look.UI_BOLD))
        st.configure("Mode.TLabel", font=f(14, face=look.UI_BOLD))
        st.configure("Station.TLabel", foreground=p["accent"], font=f(14, face=look.UI_BOLD))
        st.configure("Shared.TLabel", background=p["shared"], foreground=p["fg"],
                     padding=(10, 3), font=f(9, face=look.UI_BOLD))
        st.configure("Details.TLabel", background=p["button"], foreground=p["fg"],
                     font=f(10.5, face=look.UI_BOLD))
        # Hotkeys box and the Keyboard shortcuts window
        # dark like the header bar in both themes: bright green keys, white text
        st.configure("Legend.TFrame", background=p["hdr"], relief="solid", borderwidth=1,
                     bordercolor=p["hdr_val"], lightcolor=p["hdr_val"], darkcolor=p["hdr_val"])
        st.configure("Legend.TLabel", background=p["hdr"], foreground=p["hdr_fg"],
                     font=f(10.5, face=look.UI_BOLD))
        st.configure("LegendKey.TLabel", background=p["hdr"], foreground=p["hdr_val"],
                     font=f(11, "bold", face=look.MONO))
        st.configure("LegendHead.TLabel", background=p["hdr"], foreground=p["hdr_fg"],
                     font=f(12.5, face=look.UI_BOLD))
        st.configure("Legend.TButton", padding=(8, 0), font=f(9, face=look.UI_BOLD))

        # dark header bar (same in both themes)
        st.configure("Hdr.TFrame", background=p["hdr"])
        if getattr(self, "logo_lbl", None):
            self.logo_lbl.configure(bg=p["hdr"])
        st.configure("HdrTitle.TLabel", background=p["hdr"], foreground=p["hdr_fg"],
                     font=f(20, "bold"))
        st.configure("HdrMono.TLabel", background=p["hdr"], foreground=p["hdr_key"],
                     font=f(12, "bold", face=look.MONO))
        st.configure("HdrVal.TLabel", background=p["hdr"], foreground=p["hdr_val"],
                     font=f(12, "bold", face=look.MONO))
        st.configure("HdrBad.TLabel", background=p["hdr"], foreground=p["bad"],
                     font=f(12, "bold", face=look.MONO))
        self.lbl_freq.configure(font=(look.MONO, round(26 * k), "bold"))

        # classic Tk pieces (option database covers dialogs and dropdown lists made later)
        for pat, val in (("*Background", p["bg"]), ("*Foreground", p["fg"]),
                         ("*Entry.Background", p["input"]), ("*insertBackground", p["fg"]),
                         ("*selectBackground", p["select"]), ("*selectForeground", p["selfg"]),
                         ("*TCombobox*Listbox.background", p["input"]),
                         ("*TCombobox*Listbox.foreground", p["fg"]),
                         ("*TCombobox*Listbox.selectBackground", p["select"]),
                         ("*TCombobox*Listbox.selectForeground", p["selfg"])):
            self.option_add(pat, val)
        self.configure(bg=p["bg"])
        self.dot.configure(bg=p["hdr"])
        if self.connected is None:
            self.dot.itemconfig(self.dot_id, fill=p["idle"])
        else:
            self.dot.itemconfig(self.dot_id, fill=p["ok"] if self.connected else p["bad"])
        self.lbl_freq.configure(bg=p["freq_bg"], fg=p["freq_fg"],
                                highlightbackground=p["border"], highlightcolor=p["border"])
        for m in self.menus:
            try:
                m.configure(bg=p["field"], fg=p["fg"], activebackground=p["select"],
                            activeforeground=p["selfg"], selectcolor=p["fg"])
            except tk.TclError:
                pass
        for cb in (self.band_cb, self.reach_cb, self.sort_cb):
            try:
                pd = self.tk.call("ttk::combobox::PopdownWindow", cb)
                self.tk.call(f"{pd}.f.l", "configure", "-background", p["input"],
                             "-foreground", p["fg"], "-selectbackground", p["select"],
                             "-selectforeground", p["selfg"])
            except tk.TclError:
                pass
        for v in self.views:
            self._style_tree(v["tree"])
            for col in ALL_COLS:
                v["tree"].column(col, width=round(COLDEFS[col][1] * k))
        for w in (self.band_cb, self.reach_cb, self.sort_cb, self.search_entry):
            w.configure(font=ui)
        self.theme_btn.configure(text="☀ Light" if name == "dark" else "☾ Dark")
        if hasattr(self, "size_var"):
            self.size_var.set(self.data["settings"].get("ui_scale", 100))
        set_titlebar_dark(self, name == "dark")
