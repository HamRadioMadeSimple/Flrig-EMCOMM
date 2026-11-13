"""Starts the real window against a pretend flrig and clicks through the basics.
Needs a screen (on Linux servers run it with:  xvfb-run python -m unittest tests.test_gui)."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

try:
    import tkinter as tk
    tk.Tk().destroy()
    HAVE_SCREEN = True
except Exception:  # no display (e.g. a server without xvfb)
    HAVE_SCREEN = False


@unittest.skipUnless(HAVE_SCREEN, "needs a screen")
class MainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import fake_flrig
        cls.rig = fake_flrig
        cls.server = fake_flrig.start(port=12399)
        from tkinter import messagebox, simpledialog
        messagebox.showinfo = lambda *a, **k: None
        messagebox.askyesno = lambda *a, **k: True
        simpledialog.askstring = lambda *a, **k: None   # skip the first-start location question
        from flrig_emcomm import stations
        cls.stations = stations
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_file = stations.DATA_FILE
        stations.DATA_FILE = os.path.join(cls.tmp.name, "flrig_stations.json")
        data = stations.default_data()
        data["settings"]["port"] = 12399
        data["settings"]["shortcut_asked"] = True
        data["settings"]["home_asked"] = True
        stations.save_data(data)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.stations.DATA_FILE = cls.old_file
        cls.tmp.cleanup()

    def pump(self, app, ms):
        app.after(ms, app.quit)
        app.mainloop()

    def test_basics(self):
        from flrig_emcomm.app import App
        from flrig_emcomm.entry_dialog import EntryDialog
        app = App()
        try:
            self.pump(app, 2500)                                  # let it find the rig
            self.assertTrue(app.connected)
            self.assertIn("7,115.000 kHz", app.lbl_freq.cget("text"))

            # tune: pick WWV 10 MHz on the Weather & Time tab
            vi = next(i for i, v in enumerate(app.views) if v["label"] == "Weather & Time")
            app.go_to_view(vi)
            tree = app.cur_tree()
            row = next(i for i in tree.get_children() if app.by_id[i][1]["freq_hz"] == 10_000_000)
            tree.selection_set(row)
            tree.focus(row)
            app.tune_selected()
            self.pump(app, 1500)
            self.assertEqual(self.rig.state["vfo"], "10000000")
            self.assertEqual(self.rig.state["mode"], "AM")

            # favorite and reliable marks
            e = app.by_id[row][1]
            fav, rel = e["fav"], e["rel"]
            app.toggle_fav([row])
            app.toggle_rel([row])
            self.assertEqual((e["fav"], e["rel"]), (not fav, not rel))

            # clone with a new frequency
            def fill():
                d = [w for w in app.winfo_children() if isinstance(w, EntryDialog)][0]
                d.v_freq.set("15000")
                d._ok()
            app.after(500, fill)
            app.clone_selected(row)
            self.assertTrue(any(x["freq_hz"] == 15_000_000 and x["name"] == e["name"]
                                for _, x in app.by_id.values()))

            # frequency display formats
            app.cycle_freq_format()
            self.assertEqual(app.cur_tree().heading("freq")["text"].split()[1], "(MHz)")
            app.set_freq_format("khz")
        finally:
            app.on_close()
        # everything was saved
        loaded, _ = self.stations.load_data()
        self.assertTrue(any(x["freq_hz"] == 15_000_000 for t in loaded["tabs"] for x in t["entries"]))


if __name__ == "__main__":
    unittest.main()
