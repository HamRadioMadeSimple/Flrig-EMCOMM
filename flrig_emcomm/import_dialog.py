"""The Import window."""

import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from tkinter import ttk

from .freq import band_of, fmt_disp
from .geo import miles_between
from .importer import (DIST_RE, IMPORT_DISTANCES, IMPORT_PRESETS, PRESET_BY_NAME, ROW_TAB,
                       build_ai_prompt, classify_rows, import_message, parse_station_table)
from .look import THEMES, fit_on_monitor, set_titlebar_dark
from .stations import is_voice_net, new_id, normalize_entry, tidy_tabs


class ImportDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.rows = []
        p = app.pal
        st = app.data["settings"]
        self.title("Import stations")
        self.transient(app)
        self.configure(bg=p["bg"])
        # size to fit the screen (Windows display scaling can make 700 px too tall)
        k = app.data["settings"].get("ui_scale", 100) / 100
        w, h, x, y = fit_on_monitor(app, round(1080 * k), round(720 * k),
                                    app.winfo_rootx() + 50, app.winfo_rooty() + 30)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(820, w), min(420, h))
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="1   Ask any AI for a list", style="Big.TLabel").pack(anchor="w")
        r0 = ttk.Frame(frm)
        r0.pack(fill="x", pady=(4, 2))
        ttk.Label(r0, text="List type:").pack(side="left")
        self.v_preset = tk.StringVar(value=st.get("import_preset") if st.get("import_preset")
                                     in PRESET_BY_NAME else "AM Broadcast")
        pcb = ttk.Combobox(r0, textvariable=self.v_preset, state="readonly", width=16,
                           values=[pr["name"] for pr in IMPORT_PRESETS])
        pcb.pack(side="left", padx=(4, 14))
        pcb.bind("<<ComboboxSelected>>", lambda ev: self.load_preset())
        ttk.Label(r0, text="Distance:").pack(side="left")
        self.v_dist = tk.StringVar(value=f"{st.get('import_dist', 50)} miles")
        self.dist_cb = ttk.Combobox(r0, textvariable=self.v_dist, state="readonly", width=10,
                                    values=[f"{n} miles" for n in IMPORT_DISTANCES])
        self.dist_cb.pack(side="left", padx=(4, 14))
        self.dist_cb.bind("<<ComboboxSelected>>", lambda ev: self.change_distance())
        ttk.Button(r0, text="Reset to default", command=self.reset_preset).pack(side="left")
        self.edited_lbl = ttk.Label(r0, text="", style="Muted.TLabel")
        self.edited_lbl.pack(side="left", padx=10)
        r1 = ttk.Frame(frm)
        r1.pack(fill="x", pady=(4, 2))
        ttk.Label(r1, text="I want:").pack(side="left")
        self.v_topic = tk.StringVar()
        ttk.Entry(r1, textvariable=self.v_topic).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r1, text="Copy AI prompt", command=self.copy_prompt).pack(side="left")
        self.v_topic.trace_add("write", lambda *a: self._show_edited())
        ttk.Label(frm, style="Muted.TLabel",
                  text="Paste the prompt into ChatGPT, Claude, Copilot or any AI. Copy its whole reply "
                       "(or the code box's Copy button) and click 'Paste from clipboard' below. "
                       "If the AI gives you a file instead, use 'Open CSV file…'.",
                  wraplength=1000, justify="left").pack(anchor="w")

        ttk.Label(frm, text="2   Paste the AI's reply here (plain text is all you need, no file required)",
                  style="Big.TLabel").pack(anchor="w", pady=(10, 2))
        tf = ttk.Frame(frm)
        tf.pack(fill="x")
        self.txt = tk.Text(tf, height=7, wrap="none", font=("Consolas", 9), relief="flat",
                           bg=p["input"], fg=p["fg"], insertbackground=p["fg"],
                           highlightthickness=1, highlightbackground=p["input_border"],
                           highlightcolor=p["select"])
        self.txt.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.txt.yview)
        sb.pack(side="left", fill="y")
        self.txt.configure(yscrollcommand=sb.set)
        b2 = ttk.Frame(frm)
        b2.pack(fill="x", pady=4)
        ttk.Button(b2, text="Paste from clipboard", command=self.paste).pack(side="left")
        ttk.Button(b2, text="Open CSV file…", command=self.open_file).pack(side="left", padx=6)
        ttk.Button(b2, text="Clear", command=lambda: self.txt.delete("1.0", "end")
                   ).pack(side="left")
        ttk.Button(b2, text="Check list ▶", command=self.check).pack(side="right")

        ttk.Label(frm, text="3   Review, then import", style="Big.TLabel").pack(anchor="w",
                                                                              pady=(8, 2))
        pf = ttk.Frame(frm)
        pf.pack(fill="both", expand=True)
        cols = ("use", "freq", "mode", "band", "name", "comment", "location", "miles", "scope",
                "dest", "status")
        heads = {"use": ("✓", 30), "freq": ("Frequency", 86), "mode": ("Mode", 54),
                 "band": ("Band", 58), "name": ("Name", 140), "comment": ("Comments", 200),
                 "location": ("Location", 110), "miles": ("Miles", 46), "scope": ("Reach", 76),
                 "dest": ("Into tab", 110), "status": ("Status", 150)}
        self.tree = ttk.Treeview(pf, columns=cols, show="headings", selectmode="extended",
                                 height=5)
        for c in cols:
            self.tree.heading(c, text=heads[c][0])
            self.tree.column(c, width=heads[c][1], minwidth=30,
                             anchor="w" if c in ("name", "comment", "location", "status", "dest")
                             else "center", stretch=c in ("comment", "name"))
        vsb = ttk.Scrollbar(pf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        self.tree.tag_configure("skip", foreground=p["muted"])
        self.tree.tag_configure("bad", foreground=p["bad"])
        self.tree.bind("<ButtonRelease-1>", self._toggle_click)
        self.tree.bind("<space>", lambda ev: self._toggle_selected())
        self.tree.bind("<Button-3>", self._row_menu)
        self.row_menu = tk.Menu(self, tearoff=False)
        self.row_menu_tabs = tk.Menu(self.row_menu, tearoff=False)
        for mnu in (self.row_menu, self.row_menu_tabs):
            mnu.configure(bg=p["field"], fg=p["fg"], activebackground=p["select"],
                          activeforeground=p["selfg"])

        mv = ttk.Frame(frm)
        ttk.Label(mv, text="Highlighted rows →").pack(side="left")
        self.v_send = tk.StringVar()
        self.send_cb = ttk.Combobox(mv, textvariable=self.v_send, width=22,
                                    values=[t["name"] for t in app.data["tabs"]])
        self.send_cb.pack(side="left", padx=4)
        ttk.Button(mv, text="Send to tab", command=lambda: self.send_selected(self.v_send.get())
                   ).pack(side="left")
        ttk.Button(mv, text="Use default tab", command=lambda: self.send_selected(None)
                   ).pack(side="left", padx=(4, 12))
        ttk.Label(mv, style="Muted.TLabel",
                  text="Ctrl+click / Shift+click to highlight several rows, or right-click them."
                  ).pack(side="left")

        bot = ttk.Frame(frm)
        ttk.Button(bot, text="All", width=5, command=lambda: self._set_all(True)).pack(side="left")
        ttk.Button(bot, text="None", width=5, command=lambda: self._set_all(False)
                   ).pack(side="left", padx=(4, 16))
        ttk.Label(bot, text="Put into tab:").pack(side="left")
        self.v_tab = tk.StringVar(value=st.get("import_tab") or "FM Broadcast")
        self.tab_cb = ttk.Combobox(bot, textvariable=self.v_tab, width=24,
                                   values=[t["name"] for t in app.data["tabs"]])
        self.tab_cb.pack(side="left", padx=(4, 4))
        self.v_tab.trace_add("write", lambda *a: self._refresh_dest())
        ttk.Label(bot, text="(default; pick or type a new name)",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(bot, text="Close", command=self.close).pack(side="right")
        self.import_btn = ttk.Button(bot, text="Import", command=self.do_import, state="disabled")
        self.import_btn.pack(side="right", padx=6)
        self.summary = ttk.Label(frm, text="", style="Muted.TLabel")
        # packed bottom-up: buttons at the very bottom, then summary, then the send-to bar
        bot.pack(side="bottom", fill="x", pady=(6, 0), before=pf)
        self.summary.pack(side="bottom", anchor="w", pady=(4, 0), before=pf)
        mv.pack(side="bottom", fill="x", pady=(6, 0), before=pf)
        set_titlebar_dark(self, p is THEMES["dark"])
        self.bind("<Escape>", lambda ev: self.close())
        self.load_preset(set_tab=not st.get("import_tab"))
        self.protocol("WM_DELETE_WINDOW", self.close)

    # list types (presets)
    def _dist(self):
        try:
            return int(self.v_dist.get().split()[0])
        except (ValueError, IndexError):
            return 50

    def default_text(self, name=None):
        pr = PRESET_BY_NAME[name or self.v_preset.get()]
        return pr["text"].format(dist=self._dist(), home=self.app.data["settings"]["home_label"])

    def _overrides(self):
        return self.app.data["settings"].setdefault("import_requests", {})

    def _remember_text(self, name=None):
        """Keep the person's wording for this list type (or forget it if it's the default)."""
        name = name or getattr(self, "_loaded_preset", None) or self.v_preset.get()
        text = self.v_topic.get().strip()
        ov = self._overrides()
        if not text or text == self.default_text(name):
            ov.pop(name, None)
        else:
            ov[name] = text
        st = self.app.data["settings"]
        st["import_preset"] = self.v_preset.get()
        st["import_dist"] = self._dist()

    def load_preset(self, set_tab=True):
        if getattr(self, "_loaded_preset", None):
            self._remember_text(self._loaded_preset)  # keep edits to the type we're leaving
        name = self.v_preset.get()
        self._loaded_preset = name
        self.v_topic.set(self._overrides().get(name) or self.default_text(name))
        tab = PRESET_BY_NAME[name]["tab"]
        if set_tab:
            self.v_tab.set(tab)
        self._show_edited()

    def change_distance(self):
        text = self.v_topic.get()
        if DIST_RE.search(text):
            self.v_topic.set(DIST_RE.sub(f"within {self._dist()} miles", text, count=1))
        self._show_edited()

    def reset_preset(self):
        self._overrides().pop(self.v_preset.get(), None)
        self.v_topic.set(self.default_text())
        self.app._persist()
        self.summary.configure(text=f"'{self.v_preset.get()}' request reset to the original wording.")

    def _show_edited(self):
        if not hasattr(self, "dist_cb"):
            return
        text = self.v_topic.get().strip()
        edited = bool(text) and text != self.default_text()
        self.edited_lbl.configure(text="✎ edited (Reset to default brings back the original)"
                                  if edited else "")
        self.dist_cb.configure(state="readonly" if DIST_RE.search(text) else "disabled")

    def close(self):
        self._remember_text()
        self.app._persist()
        self.destroy()

    # step 1
    def copy_prompt(self):
        topic = self.v_topic.get().strip()
        if not topic:
            return
        self.clipboard_clear()
        self.clipboard_append(build_ai_prompt(topic, PRESET_BY_NAME[self.v_preset.get()]))
        self._remember_text()
        self.app._persist()
        self.summary.configure(text="Prompt copied. Paste it into your AI, then paste the reply "
                                    "in step 2.")

    # step 2
    def paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.check()

    def open_file(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[
            ("CSV / text", "*.csv *.txt *.tsv *.md"), ("All files", "*.*")])
        if not path:
            return
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.check()

    def check(self):
        rows, err = parse_station_table(self.txt.get("1.0", "end"))
        self.tree.delete(*self.tree.get_children())
        self.rows = rows
        if err:
            self.summary.configure(text="⚠ " + err)
            self.import_btn.configure(state="disabled")
            return
        st = self.app.data["settings"]
        classify_rows(rows, [e for _, e in self.app.by_id.values()],
                      st["rig_min_hz"], st["rig_max_hz"])
        for i in range(len(rows)):
            self._insert(i)
        if any(r["tab"] for r in rows):
            self.tab_cb.configure(values=[ROW_TAB] + [t["name"] for t in self.app.data["tabs"]])
            self.v_tab.set(ROW_TAB)
        self._update_summary()

    # step 3
    def _insert(self, i):
        r = self.rows[i]
        d = None
        if r["lat"] is not None:
            s = self.app.data["settings"]
            d = miles_between(s["home_lat"], s["home_lon"], r["lat"], r["lon"])
        vals = ("☑" if r["use"] else "☐", fmt_disp(r["freq_hz"]) if r["freq_hz"] else "",
                r["mode"], band_of(r["freq_hz"]) if r["freq_hz"] else "", r["name"], r["comment"],
                r["location"], "" if d is None else f"{d:.0f}", r["scope"],
                (f"↻ {self.app.data['tabs'][self.app.by_id[r['update']][0]]['name']}"
                 if r.get("update") in self.app.by_id
                 else ("→ " if r.get("dest") else "") + self._dest_of(r)), r["status"])
        tags = ("bad",) if r["error"] else (() if r["use"] else ("skip",))
        if self.tree.exists(str(i)):
            self.tree.item(str(i), values=vals, tags=tags)
        else:
            self.tree.insert("", "end", iid=str(i), values=vals, tags=tags)

    def _toggle(self, iid):
        if not iid:
            return
        r = self.rows[int(iid)]
        if r["error"]:
            return
        r["use"] = not r["use"]
        self._insert(int(iid))
        self._update_summary()

    def _dest_of(self, r):
        """Tab a row will go into: the one you sent it to, else the 'Put into tab' default."""
        if r.get("dest"):
            return r["dest"]
        target = self.v_tab.get().strip() or "Imported"
        dest = (r["tab"] or "Imported") if target == ROW_TAB else target
        names = {t["name"].lower() for t in self.app.data["tabs"]}
        if dest.lower() == "nets" and "nets" not in names and {"nets-v", "nets-d"} <= names:
            dest = "Nets-V" if is_voice_net(r) else "Nets-D"
        return dest

    def _refresh_dest(self):
        for i in range(len(getattr(self, "rows", []))):
            if self.tree.exists(str(i)):
                self._insert(i)

    def _tab_choices(self):
        names = [t["name"] for t in self.app.data["tabs"]]
        for r in self.rows:
            if r.get("dest") and r["dest"].lower() not in (n.lower() for n in names):
                names.append(r["dest"])
        return names

    def send_selected(self, name):
        ids = self.tree.selection()
        if not ids:
            self.summary.configure(text="Highlight one or more rows first (click, Ctrl+click, "
                                        "Shift+click).")
            return
        if name is not None:
            name = name.strip()
            if not name:
                return
            existing = {t["name"].lower(): t["name"] for t in self.app.data["tabs"]}
            name = existing.get(name.lower(), name)
        for iid in ids:
            r = self.rows[int(iid)]
            if r.get("update"):
                continue  # updates stay with the existing station
            r["dest"] = name
            if name and not r["error"] and not r["status"].startswith("Already"):
                r["use"] = True  # sending a row somewhere means you want it
            self._insert(int(iid))
        choices = self._tab_choices()
        self.send_cb.configure(values=choices)
        self.tab_cb.configure(values=([ROW_TAB] if any(r["tab"] for r in self.rows) else [])
                              + choices)
        self._update_summary()
        where = name or "the default tab"
        self.summary.configure(text=f"{len(ids)} row(s) will go into {where}. "
                                    + self.summary.cget("text"))

    def _toggle_selected(self):
        ids = [i for i in self.tree.selection() if not self.rows[int(i)]["error"]]
        if not ids:
            return
        new = not all(self.rows[int(i)]["use"] for i in ids)
        for i in ids:
            self.rows[int(i)]["use"] = new
            self._insert(int(i))
        self._update_summary()

    def _row_menu(self, ev):
        row = self.tree.identify_row(ev.y)
        if not row:
            return
        if row not in self.tree.selection():
            self.tree.selection_set(row)
        self.tree.focus(row)
        n = len(self.tree.selection())
        m, sub = self.row_menu, self.row_menu_tabs
        m.delete(0, "end")
        sub.delete(0, "end")
        for name in self._tab_choices():
            sub.add_command(label=name, command=lambda nm=name: self.send_selected(nm))
        sub.add_separator()
        sub.add_command(label="New tab…", command=self._send_new_tab)
        m.add_cascade(label=f"Send {n} row{'s' if n > 1 else ''} to tab", menu=sub)
        m.add_command(label="Use the default tab", command=lambda: self.send_selected(None))
        m.add_separator()
        m.add_command(label="Include (☑)", command=lambda: self._set_selected(True))
        m.add_command(label="Leave out (☐)", command=lambda: self._set_selected(False))
        m.tk_popup(ev.x_root, ev.y_root)

    def _send_new_tab(self):
        name = simpledialog.askstring("New tab", "Name for the new tab:", parent=self)
        if name and name.strip():
            self.send_selected(name.strip())

    def _set_selected(self, value):
        for i in self.tree.selection():
            if not self.rows[int(i)]["error"]:
                self.rows[int(i)]["use"] = value
                self._insert(int(i))
        self._update_summary()

    def _toggle_click(self, ev):
        if self.tree.identify_region(ev.x, ev.y) != "cell":
            return
        if self.tree.identify_column(ev.x) == "#1":
            self._toggle(self.tree.identify_row(ev.y))

    def _set_all(self, value):
        for i, r in enumerate(self.rows):
            if not r["error"]:
                r["use"] = value
                self._insert(i)
        self._update_summary()

    def _update_summary(self):
        n = sum(1 for r in self.rows if r["use"])
        skipped = sum(1 for r in self.rows if not r["use"])
        upd = sum(1 for r in self.rows if r["use"] and r.get("update"))
        pl = lambda k: f"{k} station{'' if k == 1 else 's'}"
        label = (f"Import {n - upd} · Update {upd}" if upd and n - upd
                 else f"Update {pl(upd)}" if upd else f"Import {pl(n)}")
        self.import_btn.configure(text=label, state="normal" if n else "disabled")
        self.summary.configure(text=f"{len(self.rows)} rows read · {n} selected · {skipped} "
                                    f"skipped. Click ☑ to include or leave out a row.")

    def do_import(self):
        app = self.app
        target = self.v_tab.get().strip() or "Imported"
        first_tab, count, per_tab, updated = self._apply_rows()
        if not count and not updated:
            return
        if target != ROW_TAB:
            app.data["settings"]["import_tab"] = target
        tidy_tabs(app.data)
        app._persist()
        self._remember_text()
        app._build_views(select=app.data["tabs"].index(first_tab) + 2 if first_tab
                         else app.cur_vi())
        msg = import_message(count, per_tab, updated)
        app.after(60, lambda: app._set_status(msg))
        app._persist()
        self.destroy()

    def _apply_rows(self):
        """Add the ticked new rows to their tabs and update the ticked existing stations.
        Returns (first tab added to, new count, {tab name: count}, updated count)."""
        app = self.app
        tabs = {t["name"].lower(): t for t in app.data["tabs"]}

        def tab_for(name):
            t = tabs.get(name.lower())
            if t is None:
                t = {"name": name, "entries": [], "id": new_id()}
                app.data["tabs"].append(t)
                tabs[name.lower()] = t
            return t
        first_tab, count, per_tab, updated = None, 0, {}, 0
        for r in self.rows:
            if not r["use"]:
                continue
            if r.get("update") in app.by_id:
                e = app.by_id[r["update"]][1]
                for k in r["changes"]:
                    e[k] = r[k]
                updated += 1
                continue
            tab = tab_for(self._dest_of(r))
            per_tab[tab["name"]] = per_tab.get(tab["name"], 0) + 1
            first_tab = first_tab or tab
            e = normalize_entry({k: r[k] for k in ("freq_hz", "mode", "bw", "name", "sched",
                                                   "comment", "location", "lat", "lon",
                                                   "scope", "fav", "rel")})
            e["also"] = [tabs[a.lower()]["id"] for a in r["also_names"] if a.lower() in tabs]
            tab["entries"].append(e)
            count += 1
        return first_tab, count, per_tab, updated
