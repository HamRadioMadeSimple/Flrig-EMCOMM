"""Tabs: new, rename, delete, reorder and drag."""

from tkinter import messagebox
from tkinter import simpledialog

from . import APP_NAME
from .stations import new_id, tidy_tabs


class TabsMixin:
    # ------------------------------------------------------------ tabs
    def _cur_tab_index(self):
        v = self.cur_view()
        if v["kind"] != "tab":
            messagebox.showinfo(APP_NAME, "Select one of your category tabs first "
                                          "(Favorites and All Stations are automatic).")
            return None
        return v["tab"]

    def new_tab(self):
        name = simpledialog.askstring("New tab", "Tab name:", parent=self)
        if not name or not name.strip():
            return
        if name.strip().lower() in (n.lower() for n in self._tab_names()):
            messagebox.showinfo(APP_NAME, "There's already a tab with that name.")
            return
        self.data["tabs"].append({"name": name.strip(), "entries": [], "id": new_id()})
        self._persist()
        self._build_views(select=len(self.data["tabs"]) + 1)

    def rename_tab(self):
        ti = self._cur_tab_index()
        if ti is None:
            return
        old = self.data["tabs"][ti]["name"]
        name = simpledialog.askstring("Rename tab", "New name:", parent=self, initialvalue=old)
        if not name or not name.strip() or name.strip() == old:
            return
        sorts = self.data["settings"]["sorts"]
        if old in sorts:
            sorts[name.strip()] = sorts.pop(old)
        self.data["tabs"][ti]["name"] = name.strip()
        self._persist()
        self._build_views(select=ti + 2)

    def delete_tab(self):
        ti = self._cur_tab_index()
        if ti is None:
            return
        if len(self.data["tabs"]) <= 1:
            messagebox.showinfo(APP_NAME, "You need at least one category tab.")
            return
        tab = self.data["tabs"][ti]
        keep = [e for e in tab["entries"] if self.also_indices(e)]
        gone = len(tab["entries"]) - len(keep)
        msg = f"Delete tab '{tab['name']}'?\n\n{gone} stations whose home is this tab will be deleted."
        if keep:
            msg += f"\n{len(keep)} shared stations will move to their other tab instead."
        if not messagebox.askyesno(APP_NAME, msg):
            return
        for e in keep:
            new_ti = self.also_indices(e)[0]
            e["also"].remove(self.data["tabs"][new_ti]["id"])
            self.data["tabs"][new_ti]["entries"].append(e)
        del self.data["tabs"][ti]
        tidy_tabs(self.data)
        self.data["settings"]["sorts"].pop(tab["name"], None)
        self._persist()
        self._build_views(select=max(2, ti + 1))

    def move_tab(self, delta):
        v = self.cur_view()
        if v["kind"] != "tab":
            self._set_status("Favorites and All Stations stay at the front; pick one of your tabs.")
            return
        pos = self.nb.index(v["frame"]) + delta
        if 2 <= pos < len(self.views):
            self.nb.insert(pos, v["frame"])
            self._apply_tab_order()

    # ---- tab buttons: click to open, drag left/right to move (Favorites/All stay first)
    def _mark_tab_buttons(self):
        cur = self.nb.select()
        for v in self.views:
            if "btn" in v:
                v["btn"].configure(style="TabSel.TButton" if v["frame"] == cur else "Tab.TButton")

    def _layout_tabbar(self):
        """Lay the tab buttons out in the notebook's order, wrapping onto a second row
        if the window is too narrow."""
        if not self.views or "btn" not in self.views[0]:
            return
        by_frame = {v["frame"]: v for v in self.views}
        width = max(self.tabbar.winfo_width() - 24, 300)
        row = col = used = 0
        for f in self.nb.tabs():
            b = by_frame[f]["btn"]
            w = b.winfo_reqwidth() + 5
            if used and used + w > width:
                row, col, used = row + 1, 0, 0
            b.grid(row=row, column=col, padx=(0, 5), pady=(0, 5), sticky="w")
            col += 1
            used += w
        self._mark_tab_buttons()

    def _tab_press(self, ev, frame):
        self._drag = {"frame": frame, "x": ev.x_root, "moved": False}
        return "break"

    def _tab_motion(self, ev):
        d = self._drag
        if not d:
            return "break"
        if self.nb.index(d["frame"]) < 2:
            return "break"  # Favorites / All Stations don't move
        if not d["moved"]:
            if abs(ev.x_root - d["x"]) < 12:
                return "break"
            d["moved"] = True
            self.tabbar.configure(cursor="sb_h_double_arrow")
        over = self.winfo_containing(ev.x_root, ev.y_root)
        target = next((v for v in self.views if v.get("btn") is over), None)
        if target is not None:
            ti = self.nb.index(target["frame"])
            if ti >= 2 and ti != self.nb.index(d["frame"]):
                self.nb.insert(ti, d["frame"])
                self._layout_tabbar()
        return "break"

    def _tab_release(self, ev):
        d, self._drag = self._drag, None
        if not d:
            return "break"
        if d["moved"]:
            self.tabbar.configure(cursor="")
            self._apply_tab_order()
        else:
            self.nb.select(d["frame"])
        return "break"

    def _apply_tab_order(self):
        """Save the order the tabs are shown in. No rebuild, no popups."""
        by_frame = {v["frame"]: v for v in self.views}
        order = [by_frame[f] for f in self.nb.tabs()]
        tab_views = [v for v in order if v["kind"] == "tab"]
        new_tabs = [self.data["tabs"][v["tab"]] for v in tab_views]
        if new_tabs == self.data["tabs"]:
            return
        self.data["tabs"] = new_tabs
        for i, v in enumerate(tab_views):
            v["tab"] = i
        self.views = order
        self._persist()
        self.refresh_all()
        self._layout_tabbar()
        self._set_status("Tab order saved.")
