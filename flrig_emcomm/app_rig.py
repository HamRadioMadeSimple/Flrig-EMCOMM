"""Tuning the radio: the worker thread, ATU and rig settings."""

import queue
import threading
import time
from tkinter import messagebox
from tkinter import simpledialog

from . import APP_NAME
from .freq import fmt_khz, fmt_readout
from .geo import parse_location


class RigMixin:
    # ------------------------------------------------------------ tuning
    def tune_selected(self, count=True):
        fid = self.focus_id()
        if fid:
            self.tune_entry(self.by_id[fid][1], count=count)

    def tune_entry(self, e, count=True):
        if not self.in_range(e):
            self._set_status(f"⚠ {fmt_khz(e['freq_hz'])} kHz ({e['name']}) is outside this rig's "
                             f"range. Saved for a VHF/UHF radio later.")
            return
        self.tune_q.put(dict(e))
        self.last_tuned = (e["id"], self.cur_view()["key"])
        self._mark_current()  # move the green highlight now, even if the frequency is the same
        self._set_status(f"Tuning {fmt_khz(e['freq_hz'])} kHz {e['mode']}  {e['name']}")
        if count:
            e["uses"] = int(e.get("uses", 0)) + 1
            e["last_used"] = time.time()
            for v in self.views:
                if v["tree"].exists(e["id"]):
                    v["tree"].set(e["id"], "uses", e["uses"])
            self._persist()

    def _worker(self):
        last_poll = 0.0
        while not self.stop_evt.is_set():
            job = None
            try:
                job = self.tune_q.get(timeout=0.15)
                while True:  # keep only the latest click
                    try:
                        job = self.tune_q.get_nowait()
                    except queue.Empty:
                        break
            except queue.Empty:
                pass
            if job is not None:
                try:
                    warnings = self.rig.tune(job["freq_hz"], job.get("mode"), job.get("bw"))
                    self.ui_q.put(("tuned", job, warnings))
                except Exception as ex:
                    self.ui_q.put(("error", f"Tune failed: {ex}"))
                last_poll = 0.0
            if time.time() - last_poll >= 1.0:
                last_poll = time.time()
                try:
                    self.ui_q.put(("status", self.rig.status()))
                except Exception as ex:
                    self.rig.xcvr = None
                    self.ui_q.put(("offline", str(ex)))

    def _process_ui_queue(self):
        try:
            while True:
                msg = self.ui_q.get_nowait()
                kind = msg[0]
                if kind == "status":
                    st = msg[1]
                    if st.get("modes"):
                        self.rig_modes = st["modes"]
                    old = self.rig_state.get("freq")
                    was = self.connected
                    self.rig_state.update(st)
                    self.connected = True
                    self.dot.itemconfig(self.dot_id, fill=self.pal["ok"])
                    self.lbl_xcvr.config(text=st.get('xcvr') or 'connected', style="HdrVal.TLabel")
                    self.lbl_freq.config(text=fmt_readout(st["freq"]))
                    bw = f"   BW {st['bw']}" if st.get("bw") else ""
                    self.lbl_mode.config(text=f"{st.get('mode', '')}{bw}")
                    if st["freq"] != old or not was:
                        self._mark_current()
                elif kind == "offline":
                    if self.connected is not False:
                        self.connected = False
                        self.dot.itemconfig(self.dot_id, fill=self.pal["bad"])
                        self.lbl_xcvr.config(text="not connected", style="HdrBad.TLabel")
                        self.lbl_freq.config(text=fmt_readout(0))
                        self.lbl_mode.config(text="")
                        self._mark_current()
                        self._set_status(f"Can't reach flrig at {self.rig.url} – is flrig "
                                         f"running? (Rig > flrig connection to change)")
                elif kind == "tuned":
                    job, warnings = msg[1], msg[2]
                    text = f"Tuned {fmt_khz(job['freq_hz'])} kHz {job.get('mode', '')}  {job.get('name', '')}"
                    if warnings:
                        text += "   ⚠ " + "; ".join(warnings)
                    self._set_status(text)
                elif kind == "error":
                    self._set_status("⚠ " + msg[1])
                elif kind == "atu":
                    self._set_status("⚠ ATU: " + msg[1] if msg[1] else
                                     "ATU tune command sent to the rig.")
        except queue.Empty:
            pass
        self.after(100, self._process_ui_queue)

    # ------------------------------------------------------------ antenna tuner
    def atu_tune(self):
        if not self.connected:
            self._set_status("⚠ flrig isn't connected, so the tuner can't be started.")
            return
        if str(self.atu_btn.cget("state")) == "disabled":
            return
        self.atu_btn.configure(state="disabled")
        self._set_status("ATU tuning… (the rig transmits a low-power carrier briefly)")

        def run():
            try:
                self.rig.atu_tune()
                self.ui_q.put(("atu", None))
            except Exception as ex:
                self.ui_q.put(("atu", str(ex)))
        threading.Thread(target=run, daemon=True).start()
        self.after(4000, lambda: self.atu_btn.configure(state="normal"))

    def set_home(self, first_start=False):
        st = self.data["settings"]
        intro = ("Welcome! Where is your station?\nIt's used to show how far away stations are.\n\n"
                 if first_start else "Your location, used for station distances.\n\n")
        text = simpledialog.askstring(
            "Home location",
            intro + "Enter your grid square (e.g. FM05)\nor latitude, longitude (e.g. 35.78, -78.64).",
            parent=self, initialvalue="" if first_start else f"{st['home_lat']:.4f}, {st['home_lon']:.4f}")
        if first_start:
            st["home_asked"] = True
            self._persist()
        if not text:
            if first_start:
                self._set_status("You can set your location any time under Rig > Home location.")
            return
        try:
            lat, lon = parse_location(text)
        except ValueError:
            messagebox.showerror(APP_NAME, "That isn't a lat, lon pair or a grid square.")
            return
        label = simpledialog.askstring("Home location", "Name for this place (shown in the app):",
                                       parent=self,
                                       initialvalue=text.strip() if first_start else st["home_label"])
        st["home_lat"], st["home_lon"] = lat, lon
        st["home_label"] = (label or "").strip() or f"{lat:.3f}, {lon:.3f}"
        self._persist()
        self.refresh_all()
        self._show_details()
        self._set_status(f"Home set to {st['home_label']}. Distances updated.")

    # ------------------------------------------------------------ settings
    def connection_settings(self):
        s = self.data["settings"]
        host = simpledialog.askstring("flrig connection", "flrig host / IP address:",
                                      parent=self, initialvalue=s["host"])
        if not host:
            return
        port = simpledialog.askinteger("flrig connection", "flrig XML-RPC port:", parent=self,
                                       initialvalue=s["port"], minvalue=1, maxvalue=65535)
        if not port:
            return
        s["host"], s["port"] = host.strip(), port
        self.lbl_host.configure(text=s["host"])
        self.lbl_port.configure(text=str(port))
        self.rig.set_address(s["host"], s["port"])
        self.connected = None
        self._persist()
        self._set_status(f"Connecting to {self.rig.url} …")

    def range_settings(self):
        s = self.data["settings"]
        lo = simpledialog.askfloat("Rig frequency range", "Lowest frequency the rig tunes (MHz):",
                                   parent=self, initialvalue=s["rig_min_hz"] / 1e6, minvalue=0)
        if lo is None:
            return
        hi = simpledialog.askfloat("Rig frequency range", "Highest frequency the rig tunes (MHz):",
                                   parent=self, initialvalue=s["rig_max_hz"] / 1e6, minvalue=lo)
        if hi is None:
            return
        s["rig_min_hz"], s["rig_max_hz"] = int(lo * 1e6), int(hi * 1e6)
        self._persist()
        self.refresh_all()
