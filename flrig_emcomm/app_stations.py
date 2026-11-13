"""Adding, editing, cloning, deleting, marking and moving stations; export."""

import csv
from tkinter import filedialog
from tkinter import messagebox

from . import APP_NAME
from .entry_dialog import EntryDialog
from .freq import DEFAULT_MODES, fmt_disp, fmt_khz, parse_bw
from .import_dialog import ImportDialog
from .stations import new_id, normalize_entry


class StationsMixin:
    # ------------------------------------------------------------ station actions
    def _tab_names(self):
        return [t["name"] for t in self.data["tabs"]]

    def _modes(self):
        out = []
        for m in self.rig_modes + DEFAULT_MODES:
            if m not in out:
                out.append(m)
        return out

    def add_entry(self, preset=None):
        if preset is None:
            preset = {"freq_hz": 0, "mode": "USB", "bw": None, "name": "",
                      "sched": "", "comment": "", "fav": self.cur_view()["kind"] == "fav"}
            if self.connected and self.rig_state.get("freq"):
                # start from what the rig is on now: frequency, mode and filter
                preset["freq_hz"] = self.rig_state["freq"]
                preset["mode"] = self.rig_state.get("mode") or "USB"
                try:
                    preset["bw"] = parse_bw(self.rig_state.get("bw"))
                except ValueError:
                    pass
        self._add_loop("Add station", preset, self.default_tab_index(), ())

    def _add_loop(self, title, preset, tab_idx, also):
        """Add dialog. "Save + another freq" saves, then opens again with the same name,
        schedule, comments, location and tabs, ready for the next frequency."""
        count = 0
        while True:
            dlg = EntryDialog(self, title, preset, self._tab_names(), tab_idx, self._modes(),
                              also=also, another=True)
            if not dlg.result:
                break
            fields, ti, also = dlg.result
            same = [x for _, x in self.by_id.values()
                    if x["freq_hz"] == fields["freq_hz"] and x["mode"] == fields["mode"]]
            if same and not messagebox.askyesno(
                    APP_NAME, f"{same[0]['name'] or 'A station'} is already in the list on "
                    f"{fmt_disp(fields['freq_hz'], unit=True)} {fields['mode']}.\n\nAdd anyway?",
                    parent=self):
                if not dlg.again:
                    break
                preset, tab_idx, title = dict(fields, freq_hz=0), ti, "Add another frequency"
                continue
            e = normalize_entry(dict(fields))
            e["also"] = [self.data["tabs"][i]["id"] for i in also]
            self.data["tabs"][ti]["entries"].append(e)
            self._persist()
            self.refresh_all(keep=[e["id"]])
            self._reveal(e["id"])
            count += 1
            if not dlg.again:
                break
            preset, tab_idx, title = dict(fields, freq_hz=0), ti, "Add another frequency"
            self._set_status(f"Saved {fmt_disp(e['freq_hz'], unit=True)}. "
                             f"Enter the next frequency for {e['name'] or 'this station'}.")
        if count > 1:
            self._set_status(f"Added {count} frequencies for {e['name'] or 'the station'}.")

    def select_all(self):
        """Highlight every station showing on this tab (after Search and filters)."""
        tree = self.cur_tree()
        rows = tree.get_children()
        tree.selection_set(rows)
        tree.focus_set()
        self._set_status(f"{len(rows)} stations highlighted on {self.cur_view()['label']}. "
                         f"Press Delete to remove them, or click a station to undo.")

    def clone_selected(self, fid=None):
        """Same station details, new frequency: opens Add with everything filled in
        except the frequency."""
        fid = fid or self.focus_id()
        if not fid:
            self._set_status("Highlight a station to clone first.")
            return
        ti, e = self.by_id[fid]
        self._add_loop("Clone station (new frequency)", dict(e, freq_hz=0), ti,
                       self.also_indices(e))

    def add_current(self):
        if not self.connected:
            messagebox.showinfo(APP_NAME, "flrig isn't connected, so there's no current "
                                          "frequency to grab.")
            return
        try:
            bw = parse_bw(self.rig_state.get("bw"))
        except ValueError:
            bw = None
        self.add_entry({"freq_hz": self.rig_state["freq"], "mode": self.rig_state.get("mode", ""),
                        "bw": bw, "name": "", "sched": "", "comment": "", "fav": False})

    def edit_selected(self):
        fid = self.focus_id()
        if not fid:
            return
        ti, e = self.by_id[fid]
        dlg = EntryDialog(self, "Edit station", e, self._tab_names(), ti, self._modes(),
                          also=self.also_indices(e), clone=True)
        if not dlg.result:
            return
        fields, new_ti, also = dlg.result
        e.update(fields)
        e["also"] = [self.data["tabs"][i]["id"] for i in also]
        if new_ti != ti:
            self.data["tabs"][ti]["entries"].remove(e)
            self.data["tabs"][new_ti]["entries"].append(e)
        self._persist()
        self.refresh_all(keep=[fid])
        self._mark_current()
        if dlg.clone_after:
            self.clone_selected(fid)

    def duplicate_selected(self):
        fid = self.focus_id()
        if not fid:
            return
        ti, e = self.by_id[fid]
        c = dict(e, id=new_id(), name=e["name"] + " (copy)", uses=0, last_used=0, also=[])
        lst = self.data["tabs"][ti]["entries"]
        lst.insert(lst.index(e) + 1, c)
        self._persist()
        self.refresh_all(keep=[c["id"]])

    def delete_selected(self):
        """On a tab where a station is only 'also shown', this just removes it from that tab.
        A station is deleted completely only from its home tab, Favorites or All Stations."""
        ids = self.selected_ids()
        if not ids:
            return
        v = self.cur_view()
        here = v["tab"] if v["kind"] == "tab" else None
        unlink = [i for i in ids if here is not None and self.by_id[i][0] != here]
        delete = [i for i in ids if i not in unlink]

        def names(lst):
            ns = [f"{self.by_id[i][1]['name'] or 'station'} ({fmt_khz(self.by_id[i][1]['freq_hz'])} kHz)"
                  for i in lst[:5]]
            return "\n".join("   " + n for n in ns) + ("\n   …" if len(lst) > 5 else "")
        parts = []
        if unlink:
            parts.append(f"Remove {len(unlink)} from the {v['label']} tab only "
                         f"(stays on its home tab):\n"
                         + names(unlink))
        if delete:
            shared = [i for i in delete if self.is_shared(self.by_id[i][1])]
            note = ("\n\nThis also removes it from every other tab it's shown on."
                    if shared else "")
            parts.append(f"Delete {len(delete)} station{'s' if len(delete) != 1 else ''} "
                         f"completely:\n" + names(delete) + note)
        if not messagebox.askyesno(APP_NAME, "\n\n".join(parts)):
            return
        if unlink:
            tid = self.data["tabs"][here]["id"]
            for i in unlink:
                e = self.by_id[i][1]
                if tid in e["also"]:
                    e["also"].remove(tid)
        for i in delete:
            ti, e = self.by_id[i]
            self.data["tabs"][ti]["entries"].remove(e)
        self._persist()
        self.refresh_all()

    def toggle_fav(self, ids):
        ents = [self.by_id[i][1] for i in ids if i in self.by_id]
        if not ents:
            return
        new = not all(e["fav"] for e in ents)
        for e in ents:
            e["fav"] = new
        self._persist()
        self.refresh_all(keep=ids)
        self._set_status(f"{'Added to' if new else 'Removed from'} favorites: "
                         + ", ".join(e["name"] or fmt_khz(e["freq_hz"]) for e in ents[:4])
                         + ("…" if len(ents) > 4 else ""))

    def toggle_rel(self, ids):
        """✔ Reliable: mark go-to stations that usually come in."""
        ents = [self.by_id[i][1] for i in ids if i in self.by_id]
        if not ents:
            return
        new = not all(e["rel"] for e in ents)
        for e in ents:
            e["rel"] = new
        self._persist()
        self.refresh_all(keep=ids)
        self._set_status(f"{'Marked' if new else 'Unmarked'} ✔ reliable: "
                         + ", ".join(e["name"] or fmt_khz(e["freq_hz"]) for e in ents[:4])
                         + ("…" if len(ents) > 4 else ""))

    def toggle_fav_selected(self):
        self.toggle_fav(self.selected_ids())

    def move_to_tab(self, new_ti):
        """Change the home tab of the selected stations."""
        ids = self.selected_ids()
        new_tid = self.data["tabs"][new_ti]["id"]
        for i in ids:
            ti, e = self.by_id[i]
            if ti != new_ti:
                self.data["tabs"][ti]["entries"].remove(e)
                self.data["tabs"][new_ti]["entries"].append(e)
                if new_tid in e["also"]:
                    e["also"].remove(new_tid)
        self._persist()
        self.refresh_all(keep=ids)

    def toggle_also(self, eid, ti):
        """Show / stop showing a station on an extra tab. Always one station, never a copy."""
        home_ti, e = self.by_id[eid]
        if ti == home_ti:
            return
        tid = self.data["tabs"][ti]["id"]
        name = self.data["tabs"][ti]["name"]
        if tid in e["also"]:
            e["also"].remove(tid)
            msg = f"{e['name'] or 'Station'} no longer shown on {name}."
        else:
            e["also"].append(tid)
            msg = f"{e['name'] or 'Station'} now also shown on {name} (same station, not a copy)."
        self._persist()
        self.refresh_all(keep=[eid])
        self._show_details()
        self._set_status(msg)

    def move_selected(self, delta):
        v = self.cur_view()
        fid = self.focus_id()
        if not fid:
            self._set_status("Highlight a station first, then use Move up / Move down.")
            return
        e = self.by_id[fid][1]
        if self.is_filtering():
            self._set_status("Clear the search, Band and Reach filters to reorder stations.")
            return
        if v["kind"] != "tab":
            self._move_in_view(v, fid, delta)
            return
        if self.is_filtering():
            self._set_status("Clear the search, Band and Reach filters to reorder stations.")
            return
        lst = self.data["tabs"][v["tab"]]["entries"]
        if e not in lst:
            self._set_status("This station is shared from another tab. Reorder it on its home tab.")
            return
        name, rev = self.get_sort(v["key"])
        if name != "Custom order":
            # keep exactly what's on screen as the new custom order, then move from there
            shown = [self.by_id[i][1] for i in self.cur_tree().get_children()]
            lst[:] = [x for x in shown if x in lst] + [x for x in lst if x not in shown]
            self.set_sort("Custom order", reverse=False)
            name, rev = "Custom order", False
            self.after(10, lambda: self._set_status(
                "Switched this tab to Custom order so your arrangement sticks. "
                "Click a column heading any time to sort it differently."))
        i = lst.index(e)
        j = i + (-delta if rev else delta)
        if 0 <= j < len(lst):
            lst[i], lst[j] = lst[j], lst[i]
            self._persist()
            self.refresh_view(self.cur_vi(), keep=[fid])
            self.reindex()

    def _move_in_view(self, v, fid, delta):
        """Favorites / All Stations keep their own arrangement (it doesn't change the tabs)."""
        tree = self.cur_tree()
        name, rev = self.get_sort(v["key"])
        ids = list(tree.get_children())
        if name != "Custom order" or rev:
            self.set_sort("Custom order", reverse=False)
            self.after(10, lambda: self._set_status(
                f"Switched {v['label']} to Custom order so your arrangement sticks. "
                f"It doesn't change the order on your other tabs."))
        i = ids.index(fid)
        j = i + delta
        if not 0 <= j < len(ids):
            return
        ids[i], ids[j] = ids[j], ids[i]
        self.data["settings"].setdefault("view_orders", {})[v["key"]] = ids
        self._persist()
        self.refresh_view(self.cur_vi(), keep=[fid])

    def _reveal(self, eid):
        """After adding, make sure the new station is visible on the current page."""
        tree = self.cur_tree()
        if not tree.exists(eid):
            ti = self.by_id[eid][0]
            self.nb.select(2 + ti)
            tree = self.cur_tree()
        if tree.exists(eid):
            tree.selection_set(eid)
            tree.focus(eid)
            tree.see(eid)

    def reset_usage(self):
        if messagebox.askyesno(APP_NAME, "Reset the 'Used' count on every station?"):
            for _, e in self.by_id.values():
                e["uses"] = 0
                e["last_used"] = 0
            self._persist()
            self.refresh_all()

    # ------------------------------------------------------------ CSV
    CSV_FIELDS = ["tab", "frequency_khz", "mode", "bw", "name", "schedule", "comment",
                  "favorite", "uses", "also_on", "location", "lat", "lon", "scope", "reliable"]

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")],
                                            initialfile="flrig_stations.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(self.CSV_FIELDS)
            for tab in self.data["tabs"]:
                for e in tab["entries"]:
                    w.writerow([tab["name"], fmt_khz(e["freq_hz"]), e["mode"], e["bw"] or "",
                                e["name"], e["sched"], e["comment"],
                                "yes" if e["fav"] else "", e["uses"] or "",
                                " | ".join(self.data["tabs"][i]["name"]
                                           for i in self.also_indices(e)),
                                e["location"], "" if e["lat"] is None else e["lat"],
                                "" if e["lon"] is None else e["lon"], e["scope"],
                                "yes" if e["rel"] else ""])
        self._set_status(f"Exported to {path}")

    def open_import(self):
        ImportDialog(self)
