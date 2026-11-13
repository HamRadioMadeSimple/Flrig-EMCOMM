"""The Add / Edit / Clone station window."""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from .freq import COMMON_BWS, band_of, fmt_khz, parse_bw, parse_freq_to_hz
from .geo import SCOPES, parse_location
from .look import THEMES, fit_on_monitor, set_titlebar_dark


# ==========================================================================
# Add / edit dialog
# ==========================================================================
class EntryDialog(tk.Toplevel):
    def __init__(self, master, title, entry, tab_names, tab_idx, modes, also=(), another=False,
                 clone=False):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        self.again = False  # "Save + another freq" was clicked
        self.clone_after = False  # "Save + clone" was clicked (Edit window)
        self.tab_names = tab_names

        frm = ttk.Frame(self, padding=14)
        frm.grid(sticky="nsew")
        self.v_freq = tk.StringVar(value=fmt_khz(entry["freq_hz"]) if entry.get("freq_hz") else "")
        self.v_mode = tk.StringVar(value=entry.get("mode") or "")
        self.v_bw = tk.StringVar(value=str(entry.get("bw") or ""))
        self.v_name = tk.StringVar(value=entry.get("name", ""))
        self.v_sched = tk.StringVar(value=entry.get("sched", ""))
        self.v_comment = tk.StringVar(value=entry.get("comment", ""))
        self.v_tab = tk.StringVar(value=tab_names[tab_idx])
        self.v_fav = tk.BooleanVar(value=bool(entry.get("fav")))
        self.v_rel = tk.BooleanVar(value=bool(entry.get("rel")))
        self.v_loc = tk.StringVar(value=entry.get("location", ""))
        lat, lon = entry.get("lat"), entry.get("lon")
        self.v_coords = tk.StringVar(value="" if lat is None or lon is None else f"{lat}, {lon}")
        self.v_scope = tk.StringVar(value=entry.get("scope", ""))

        freq_entry = ttk.Entry(frm, textvariable=self.v_freq, width=18)
        self.home_cb = ttk.Combobox(frm, textvariable=self.v_tab, values=tab_names,
                                    state="readonly", width=22)
        self.home_cb.bind("<<ComboboxSelected>>", lambda ev: self._sync_also())
        also_frame = ttk.Frame(frm)
        self.also_vars = []
        for i, name in enumerate(tab_names):
            var = tk.BooleanVar(value=i in also and i != tab_idx)
            cb = ttk.Checkbutton(also_frame, text=name, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14), pady=1)
            self.also_vars.append((var, cb))
        marks = ttk.Frame(frm)
        ttk.Checkbutton(marks, text="★ Favorite", variable=self.v_fav).pack(side="left")
        ttk.Checkbutton(marks, text="✔ Reliable (go-to station)", variable=self.v_rel).pack(
            side="left", padx=(18, 0))
        rows = [
            ("Frequency (kHz)", freq_entry),
            ("Mode", ttk.Combobox(frm, textvariable=self.v_mode, values=modes, width=16)),
            ("Bandwidth (Hz)", ttk.Combobox(frm, textvariable=self.v_bw, values=COMMON_BWS,
                                            width=16)),
            ("Station / Name", ttk.Entry(frm, textvariable=self.v_name, width=46)),
            ("Schedule (Eastern)", ttk.Entry(frm, textvariable=self.v_sched, width=46)),
            ("Comments", ttk.Entry(frm, textvariable=self.v_comment, width=60)),
            ("Location", ttk.Entry(frm, textvariable=self.v_loc, width=30)),
            ("Coordinates", ttk.Entry(frm, textvariable=self.v_coords, width=30)),
            ("Reach", ttk.Combobox(frm, textvariable=self.v_scope, values=[""] + SCOPES,
                                   state="readonly", width=16)),
            ("Home tab", self.home_cb),
            ("Also show on", also_frame),
            ("", marks),
        ]
        for r, (label, widget) in enumerate(rows):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="w", pady=3)
        self.band_lbl = ttk.Label(frm, style="Muted.TLabel")
        self.band_lbl.grid(row=0, column=1, sticky="e")
        self.v_freq.trace_add("write", lambda *a: self._show_band())
        self._show_band()
        self._sync_also()
        ttk.Label(frm, style="Muted.TLabel", justify="left",
                  text="Frequency: 7268 or 680 (kHz), or 7.268 / 101.5 (MHz). Leave BW blank to keep\n"
                       "the rig's filter. Coordinates: lat, lon (35.78, -78.64) or a grid square (FM05)."
                  ).grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Save", command=self._ok).pack(side="right")
        if another:
            ttk.Button(btns, text="Save + another freq", command=self._ok_again).pack(
                side="right", padx=(0, 6))
        if clone:
            ttk.Button(btns, text="Save + clone (new freq)", command=self._ok_clone).pack(
                side="right", padx=(0, 6))

        self.bind("<Return>", lambda ev: self._ok())
        self.bind("<Escape>", lambda ev: self.destroy())
        freq_entry.focus_set()
        freq_entry.select_range(0, "end")
        self.update_idletasks()  # keep the whole dialog (and its Save button) on screen
        _, _, x, y = fit_on_monitor(master, self.winfo_reqwidth(), self.winfo_reqheight(),
                                    master.winfo_rootx() + 90, master.winfo_rooty() + 90)
        self.geometry(f"+{x}+{y}")
        pal = getattr(master, "pal", THEMES["light"])
        self.configure(bg=pal["bg"])
        set_titlebar_dark(self, pal is THEMES["dark"])
        self.grab_set()
        self.wait_window(self)

    def _ok_clone(self):
        self.clone_after = True
        self._ok()
        if self.result is None:
            self.clone_after = False

    def _ok_again(self):
        self.again = True
        self._ok()
        if self.result is None:
            self.again = False

    def _sync_also(self):
        home = self.tab_names.index(self.v_tab.get())
        for i, (var, cb) in enumerate(self.also_vars):
            if i == home:
                var.set(False)
                cb.state(["disabled"])
            else:
                cb.state(["!disabled"])

    def _show_band(self):
        try:
            self.band_lbl.config(text=band_of(parse_freq_to_hz(self.v_freq.get())))
        except ValueError:
            self.band_lbl.config(text="")

    def _ok(self):
        try:
            hz = parse_freq_to_hz(self.v_freq.get())
        except ValueError:
            messagebox.showerror("Frequency", "Please enter a valid frequency.", parent=self)
            return
        try:
            bw = parse_bw(self.v_bw.get())
        except ValueError:
            messagebox.showerror("Bandwidth", "Bandwidth must be a number in Hz (or blank).",
                                 parent=self)
            return
        lat = lon = None
        if self.v_coords.get().strip():
            try:
                lat, lon = parse_location(self.v_coords.get())
            except ValueError:
                messagebox.showerror("Coordinates", "Use lat, lon (35.78, -78.64) or a grid "
                                     "square (FM05), or leave it blank.", parent=self)
                return
        fields = {"freq_hz": hz, "mode": self.v_mode.get().strip(), "bw": bw,
                  "location": self.v_loc.get().strip(), "lat": lat, "lon": lon,
                  "scope": self.v_scope.get(),
                  "name": self.v_name.get().strip(), "sched": self.v_sched.get().strip(),
                  "comment": self.v_comment.get().strip(), "fav": self.v_fav.get(),
                  "rel": self.v_rel.get()}
        home = self.tab_names.index(self.v_tab.get())
        also = [i for i, (var, cb) in enumerate(self.also_vars) if var.get() and i != home]
        self.result = (fields, home, also)
        self.destroy()
