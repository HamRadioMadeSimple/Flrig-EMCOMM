"""The station table: filling it, filters, sorting, clicks, details bar, pop-ups."""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .columns import ALL_COLS, COLDEFS, COL_SORT, DEFAULT_SORT, SORTS, SORT_COL
from .freq import FREQ_FMT, band_of, band_rank, fmt_disp, fmt_rig
from .geo import SCOPES, miles_between
from .look import fit_on_monitor


class ListMixin:
    # ------------------------------------------------------------ data access
    def reindex(self):
        self.by_id = {}
        for ti, tab in enumerate(self.data["tabs"]):
            for e in tab["entries"]:
                self.by_id[e["id"]] = (ti, e)

    def rows_for(self, v):
        rows = []
        if v["kind"] == "tab":
            ti = v["tab"]
            tid = self.data["tabs"][ti]["id"]
            for p, e in enumerate(self.data["tabs"][ti]["entries"]):
                rows.append((ti, p, e))
            k = 0  # stations from other tabs that you chose to also show here
            for oti, tab in enumerate(self.data["tabs"]):
                if oti == ti:
                    continue
                for e in tab["entries"]:
                    if tid in e["also"]:
                        rows.append((ti, 100000 + k, e))
                        k += 1
            return rows
        for ti, tab in enumerate(self.data["tabs"]):
            for p, e in enumerate(tab["entries"]):
                if v["kind"] == "fav" and not e["fav"]:
                    continue
                if v["kind"] == "all" and not self.in_range(e):
                    continue  # All Stations = what this rig can actually tune
                rows.append((ti, p, e))
        return rows

    def dist(self, e):
        if e.get("lat") is None or e.get("lon") is None:
            return None
        s = self.data["settings"]
        return miles_between(s["home_lat"], s["home_lon"], e["lat"], e["lon"])

    def dist_text(self, e):
        d = self.dist(e)
        return "" if d is None else (f"{d:.1f}" if d < 10 else f"{d:.0f}")

    def tab_index(self, tid):
        for i, t in enumerate(self.data["tabs"]):
            if t["id"] == tid:
                return i
        return None

    def also_indices(self, e):
        return [i for i in (self.tab_index(t) for t in e["also"]) if i is not None]

    def is_shared(self, e):
        return bool(self.also_indices(e))

    def tabs_text(self, e, mark_home=False):
        home = self.data["tabs"][self.by_id[e["id"]][0]]["name"]
        others = [self.data["tabs"][i]["name"] for i in self.also_indices(e)]
        if mark_home and others:
            return ", ".join([f"{home} (home)"] + others)
        return " + ".join([home] + others)

    def cur_vi(self):
        try:
            return self.nb.index(self.nb.select())
        except tk.TclError:
            return 0

    def cur_view(self):
        return self.views[self.cur_vi()]

    def cur_tree(self):
        return self.cur_view()["tree"]

    def selected_ids(self):
        return [i for i in self.cur_tree().selection() if i in self.by_id]

    def focus_id(self):
        tree = self.cur_tree()
        iid = tree.focus()
        if iid in self.by_id and iid in tree.selection():
            return iid
        sel = self.selected_ids()
        return sel[0] if sel else None

    def default_tab_index(self):
        v = self.cur_view()
        if v["kind"] == "tab":
            return v["tab"]
        fid = self.focus_id()
        return self.by_id[fid][0] if fid else 0

    def in_range(self, e):
        s = self.data["settings"]
        return s["rig_min_hz"] <= e["freq_hz"] <= s["rig_max_hz"]

    # ------------------------------------------------------------ filter / sort
    def _hay(self, ti, e):
        khz = e["freq_hz"] / 1000
        parts = [f"{khz:.3f}", f"{khz:g}", f"{khz / 1000:.6f}".rstrip("0").rstrip("."),
                 fmt_rig(e["freq_hz"]),
                 e["mode"], e["name"], e["sched"], e["comment"], band_of(e["freq_hz"]),
                 self.tabs_text(e), "favorite fav" if e["fav"] else "",
                 "reliable" if e["rel"] else "",
                 e["location"], e["scope"],
                 "shared" if self.is_shared(e) else ""]
        return " ".join(parts).lower()

    def matches(self, ti, e):
        band = self.band_var.get()
        if band and band != "All bands" and band_of(e["freq_hz"]) != band:
            return False
        reach = self.reach_var.get()
        if reach.startswith("Within"):
            d = self.dist(e)
            if d is None or d > float(reach.split()[1]):
                return False
        elif reach in SCOPES and e["scope"] != reach:
            return False
        terms = self.search_var.get().lower().split()
        if not terms:
            return True
        hay = self._hay(ti, e)
        return all(t in hay for t in terms)

    def is_filtering(self):
        return (bool(self.search_var.get().strip())
                or self.band_var.get() not in ("", "All bands")
                or self.reach_var.get() not in ("", "Any reach"))

    def get_sort(self, key):
        srt = self.data["settings"]["sorts"].get(key) or DEFAULT_SORT.get(key) \
            or ["Custom order", False]
        if srt[0] not in SORTS:
            srt = ["Custom order", False]
        return srt[0], bool(srt[1])

    def set_sort(self, name, reverse=None, keep_dir=False):
        key = self.cur_view()["key"]
        _, old_rev = self.get_sort(key)
        if reverse is None:
            reverse = old_rev if keep_dir else False
        self.data["settings"]["sorts"][key] = [name, reverse]
        self._persist()
        self.refresh_view(self.cur_vi())
        self._sync_sort_widgets()

    def sort_by_column(self, col):
        name = COL_SORT[col]
        cur, rev = self.get_sort(self.cur_view()["key"])
        self.set_sort(name, reverse=(not rev) if cur == name else False)

    def flip_sort(self):
        name, rev = self.get_sort(self.cur_view()["key"])
        self.set_sort(name, reverse=not rev)

    def _sync_sort_widgets(self):
        if not self.views:
            return
        v = self.cur_view()
        name, rev = self.get_sort(v["key"])
        self.sort_var.set(name)
        self.dir_btn.config(text="↓" if rev else "↑")

    # ------------------------------------------------------------ rendering
    def _values(self, ti, e):
        return ("★" if e["fav"] else "☆", "✔" if e["rel"] else "·", fmt_disp(e["freq_hz"]), e["mode"], e["bw"] or "",
                band_of(e["freq_hz"]), self.dist_text(e), e["location"], e["name"], e["sched"],
                e["comment"],
                self.tabs_text(e), e["uses"] or "")

    def _tags(self, pos, e):
        tags = []
        if self.connected and e["id"] == self._rig_id:
            tags.append("onfreq")
        if self.is_shared(e):
            tags.append("shared")
        if not self.in_range(e):
            tags.append("outrange")
        if e["fav"]:
            tags.append("fav")
        if pos % 2:
            tags.append("odd")
        return tags

    def refresh_view(self, vi, keep=None):
        v = self.views[vi]
        tree = v["tree"]
        if keep is None:
            keep = tree.selection()
        focus = tree.focus()
        tree.delete(*tree.get_children())
        rows = [r for r in self.rows_for(v) if self.matches(r[0], r[2])]
        total = len(self.rows_for(v))
        name, rev = self.get_sort(v["key"])
        keyf = SORTS[name] or (lambda ti, p, e: self.dist(e) if self.dist(e) is not None else 1e9)
        if name == "Custom order" and v["kind"] in ("fav", "all"):
            order = {eid: n for n, eid in
                     enumerate(self.data["settings"].get("view_orders", {}).get(v["key"], []))}
            keyf = lambda ti, p, e: (order.get(e["id"], 10 ** 6), ti, p)
        rows.sort(key=lambda r: (keyf(*r), r[2]["freq_hz"]), reverse=rev)
        for pos, (ti, p, e) in enumerate(rows):
            tree.insert("", "end", iid=e["id"], values=self._values(ti, e),
                        tags=self._tags(pos, e))
        keep = [k for k in keep if tree.exists(k)]
        if keep:
            tree.selection_set(keep)
            tree.focus(focus if focus in keep else keep[0])
            tree.see(keep[0])
        primary = SORT_COL.get(name)
        for col in ALL_COLS:
            head = self._heading(col)
            if col == primary:
                head += " ▼" if rev else " ▲"
            tree.heading(col, text=head)
        text = f"{v['label']} ({len(rows)})" if self.is_filtering() else v["label"]
        self.nb.tab(vi, text=text)
        if "btn" in v:
            v["btn"].configure(text=text)
        v["shown"], v["total"] = len(rows), total

    def refresh_all(self, keep=None):
        self.reindex()
        bands = sorted({band_of(e["freq_hz"]) for _, e in self.by_id.values()}, key=band_rank)
        self.band_cb.config(values=["All bands"] + bands)
        if self.band_var.get() not in ["All bands"] + bands:
            self.band_var.set("All bands")
        for vi in range(len(self.views)):
            self.refresh_view(vi, keep=keep if vi == self.cur_vi() else None)
        self._update_status_count()

    def _mark_current(self):
        rs = self.rig_station() if self.views else None
        self._rig_id = rs["id"] if rs else None
        for v in self.views:
            tree = v["tree"]
            for pos, iid in enumerate(tree.get_children()):
                if iid in self.by_id:
                    tree.item(iid, tags=self._tags(pos, self.by_id[iid][1]))
        e = self.rig_station()
        self.lbl_station.config(text=("▶ " + (e["name"] or "Saved station")) if e else "")

    def rig_station(self):
        """The saved station matching what the rig is on now (prefers the last one you picked)."""
        hz = self.rig_state.get("freq")
        if not self.connected or hz is None:
            return None
        if self.last_tuned and self.last_tuned[0] in self.by_id:
            e = self.by_id[self.last_tuned[0]][1]
            if abs(e["freq_hz"] - hz) < 10:
                return e
        cur_ids = {e["id"] for _, _, e in self.rows_for(self.cur_view())} if self.views else set()
        matches = [e for _, e in self.by_id.values() if abs(e["freq_hz"] - hz) < 10]
        matches.sort(key=lambda e: (e["id"] not in cur_ids, -e["last_used"]))
        return matches[0] if matches else None

    def goto_rig_station(self, ev=None):
        """Jump the list back to the station that's on the rig right now."""
        if not self.connected:
            self._set_status("⚠ flrig isn't connected.")
            return
        e = self.rig_station()
        if e is None:
            self._set_status(f"No saved station at {self.rig_state['freq'] / 1000:,.3f} kHz. "
                             f"Use 'Add current' to save it.")
            return
        eid = e["id"]
        # Same page you picked it from, else the page you're on, else its own category tab
        keys = []
        if self.last_tuned and self.last_tuned[0] == eid:
            keys.append(self.last_tuned[1])
        keys.append(self.cur_view()["key"])
        keys.append(self.data["tabs"][self.by_id[eid][0]]["name"])
        vi = next(i for k in keys for i, v in enumerate(self.views)
                  if v["key"] == k and any(r[2]["id"] == eid for r in self.rows_for(v)))
        tree = self.views[vi]["tree"]
        if not tree.exists(eid):  # hidden by search / band / reach filter
            self.band_var.set("All bands")
            self.reach_var.set("Any reach")
            self.search_var.set("")
            self.refresh_all()
        self.nb.select(vi)
        tree.selection_set(eid)
        tree.focus(eid)
        tree.see(eid)
        tree.focus_set()
        self._show_details()
        msg = f"Showing {e['name'] or 'station'} on the {self.views[vi]['label']} tab."
        self.after(50, lambda: self._set_status(msg))

    def _update_status_count(self):
        if not self.views:
            return
        v = self.cur_view()
        extra = f" — showing {v.get('shown', 0)} matches" if self.is_filtering() else ""
        if self.reach_var.get().startswith("Within"):
            extra += f" {self.reach_var.get().lower()} of {self.data['settings']['home_label']}"
        if v["kind"] == "tab":
            n = sum(1 for _, p, _e in self.rows_for(v) if p >= 100000)
            if n:
                extra += f" ({n} shared from other tabs)"
        if v["kind"] == "all":
            hidden = sum(1 for _, e in self.by_id.values() if not self.in_range(e))
            if hidden:
                extra += (f" · {hidden} outside this rig's range not shown here "
                          f"(they stay on their own tabs)")
        self._set_status(f"{v['label']}: {v.get('total', 0)} stations{extra}")

    # ------------------------------------------------------------ events
    def _col_at(self, tree, x):
        col = tree.identify_column(x)
        try:
            return tree["displaycolumns"][int(col[1:]) - 1]
        except (ValueError, IndexError):
            return None

    # ------------------------------------------------------------ comment pop-up
    def _tip_motion(self, ev):
        """Hovering over a Comments cell that is cut off shows the whole comment."""
        tree = ev.widget
        row = tree.identify_row(ev.y)
        cell = (row, "comment") if row and self._col_at(tree, ev.x) == "comment" else None
        if cell == getattr(self, "_tip_cell", None):
            return
        self._tip_hide()
        self._tip_cell = cell
        if cell and row in self.by_id:
            text = self.by_id[row][1].get("comment", "")
            font = tkfont.nametofont("TkDefaultFont")
            try:
                font = tkfont.Font(font=self.style.lookup("Treeview", "font") or font)
            except tk.TclError:
                pass
            if text and font.measure(text) > tree.column("comment", "width") - 12:
                self._tip_job = self.after(400, lambda: self._tip_show(text, ev.x_root, ev.y_root))

    def _tip_show(self, text, x, y):
        self._tip_job = None
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(bg=self.pal["accent"])
        ttk.Label(tip, text=text, style="Details.TLabel", wraplength=480, justify="left",
                  padding=(10, 6)).pack(padx=1, pady=1)
        tip.update_idletasks()
        w, h = tip.winfo_reqwidth(), tip.winfo_reqheight()
        _, _, nx, ny = fit_on_monitor(self, w, h, x + 14, y + 18)
        tip.geometry(f"+{nx}+{ny}")
        self._tip = tip

    def _tip_hide(self):
        if getattr(self, "_tip_job", None):
            self.after_cancel(self._tip_job)
            self._tip_job = None
        if getattr(self, "_tip", None):
            self._tip.destroy()
            self._tip = None
        self._tip_cell = None

    def _on_click(self, ev):
        tree = ev.widget
        if tree.identify_region(ev.x, ev.y) != "cell":
            return
        row = tree.identify_row(ev.y)
        if not row:
            return
        if self._col_at(tree, ev.x) == "fav":
            self.toggle_fav([row])
            return
        if self._col_at(tree, ev.x) == "rel":
            self.toggle_rel([row])
            return

    def _on_double(self, ev):
        tree = ev.widget
        if tree.identify_region(ev.x, ev.y) != "cell" or self._col_at(tree, ev.x) in ("fav", "rel"):
            return
        row = tree.identify_row(ev.y)
        if row:
            tree.selection_set(row)
            tree.focus(row)
            self.tune_selected()

    def _on_right_click(self, ev):
        tree = ev.widget
        row = tree.identify_row(ev.y)
        if not row:
            return
        if row not in tree.selection():
            tree.selection_set(row)
        tree.focus(row)
        if self._fill_ctx_menu():
            self.ctx.tk_popup(ev.x_root, ev.y_root)

    def _show_details(self):
        fid = self.focus_id() if self.views else None
        if not fid:
            self.details.configure(text="Select a station to see its full schedule and comments.")
            return
        ti, e = self.by_id[fid]
        parts = [f"{e['name'] or 'Station'} — {fmt_disp(e['freq_hz'], unit=True)} {e['mode']}"]
        if e["sched"]:
            parts.append(f"🕘 {e['sched']}")
        if e["comment"]:
            parts.append(e["comment"])
        place = " · ".join(x for x in (e["location"], self.dist_text(e) and
                                         f"{self.dist_text(e)} mi from {self.data['settings']['home_label']}",
                                         e["scope"]) if x)
        if place:
            parts.append(f"📍 {place}")
        if self.is_shared(e):
            parts.append(f"🔗 On tabs: {self.tabs_text(e, mark_home=True)}")
        self.details.configure(text="     ".join(parts))

    def _on_view_changed(self, ev):
        self._mark_tab_buttons()
        self._show_details()
        self._sync_sort_widgets()
        self._update_status_count()

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def _focus_first_row(self, tune):
        tree = self.cur_tree()
        kids = tree.get_children()
        if not kids:
            return
        tree.focus_set()
        tree.selection_set(kids[0])
        tree.focus(kids[0])
        tree.see(kids[0])
        if tune:
            self.tune_selected()

    def _search_enter(self, ev):
        if not self.cur_tree().get_children() and self.search_var.get().strip():
            # nothing here; jump to All Stations
            self.nb.select(1)
        self._focus_first_row(tune=False)

    def _heading(self, col):
        head = COLDEFS[col][0].upper()
        if col == "freq":
            return "FREQ " + ("(kHz)" if FREQ_FMT["value"] == "khz" else "(MHz)")
        return head
