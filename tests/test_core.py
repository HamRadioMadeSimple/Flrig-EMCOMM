"""Tests for the parts that don't need a window: frequencies, locations, the import
reader, and loading / upgrading station lists.   Run:  python -m unittest -v"""

import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flrig_emcomm import freq, geo, importer, stations  # noqa: E402


class Frequencies(unittest.TestCase):
    def test_typing(self):
        p = freq.parse_freq_to_hz
        self.assertEqual(p("7268"), 7_268_000)        # whole number = kHz
        self.assertEqual(p("680"), 680_000)
        self.assertEqual(p("7.268"), 7_268_000)       # under 100 = MHz
        self.assertEqual(p("101.5"), 101_500_000)     # 100-999 with a decimal = MHz
        self.assertEqual(p("14.074 MHz"), 14_074_000)
        self.assertEqual(p("7268 kHz"), 7_268_000)
        with self.assertRaises(ValueError):
            p("abc")

    def test_bands(self):
        self.assertEqual(freq.band_of(7_268_000), "40m")
        self.assertEqual(freq.band_of(680_000), "MW BC")
        self.assertEqual(freq.band_of(146_520_000), "2m")

    def test_display_formats(self):
        try:
            freq.FREQ_FMT["value"] = "khz"
            self.assertEqual(freq.fmt_disp(7_115_000), "7115.000")
            self.assertEqual(freq.fmt_readout(7_115_000), "7,115.000 kHz")
            freq.FREQ_FMT["value"] = "mhz"
            self.assertEqual(freq.fmt_disp(7_115_000), "7.115000")
            freq.FREQ_FMT["value"] = "rig"
            self.assertEqual(freq.fmt_disp(7_115_000), "7.115.000")
            self.assertEqual(freq.fmt_readout(0), "--.---.--- MHz")
        finally:
            freq.FREQ_FMT["value"] = "khz"

    def test_bandwidth(self):
        self.assertIsNone(freq.parse_bw(""))
        self.assertEqual(freq.parse_bw("3000 Hz"), 3000)


class Locations(unittest.TestCase):
    def test_grid_square(self):
        lat, lon = geo.parse_location("FM05")
        self.assertAlmostEqual(lat, 35.5, places=1)
        self.assertAlmostEqual(lon, -79.0, places=1)

    def test_lat_lon_and_distance(self):
        a = geo.parse_location("35.78, -78.64")
        b = (40.68, -105.04)                          # WWV
        miles = geo.miles_between(a[0], a[1], b[0], b[1])
        self.assertTrue(1400 < miles < 1550, miles)


class ImportReader(unittest.TestCase):
    def test_ai_reply_with_chatter_and_code_block(self):
        reply = ("Here you go:\n```csv\n"
                 "name,frequency,mode,bw,schedule,comment,location,lat,lon,scope\n"
                 'WPTF 680,680 kHz,AM,6000,24/7,News/talk,"Raleigh, NC",35.78,-78.64,Local\n'
                 "WWV,10 MHz,AM,6000,24/7,Time,Fort Collins CO,40.68,-105.04,National\n```\nEnjoy!")
        rows, err = importer.parse_station_table(reply)
        self.assertFalse(err)
        self.assertEqual([(r["name"], r["freq_hz"]) for r in rows],
                         [("WPTF 680", 680_000), ("WWV", 10_000_000)])
        self.assertEqual(rows[0]["location"], "Raleigh, NC")

    def test_export_format_round_trip(self):
        text = ("tab,frequency_khz,mode,bw,name,schedule,comment,favorite,uses,also_on,"
                "location,lat,lon,scope,reliable\n"
                "Nets-D,7115.000,USB-D,3000,MAGNET MR04,Thu 9:00 PM,Contestia,yes,,,,,,National,yes\n")
        rows, err = importer.parse_station_table(text)
        self.assertFalse(err)
        r = rows[0]
        self.assertEqual((r["tab"], r["freq_hz"], r["fav"], r["rel"]), ("Nets-D", 7_115_000, True, True))

    def test_same_station(self):
        self.assertTrue(importer.same_station("WWV", "WWV Colorado"))
        self.assertFalse(importer.same_station("WWV", "CHU"))

    def test_prompt_matches_request(self):
        am = importer.build_ai_prompt("local AM radio stations within 50 miles of Raleigh, NC")
        self.assertIn("530-1700 kHz", am)
        self.assertNotIn("88-108 MHz", am)


class StationLists(unittest.TestCase):
    def test_starter_list(self):
        d = stations.default_data()
        self.assertEqual(d["version"], 9)
        names = [t["name"] for t in d["tabs"]]
        self.assertIn("Nets-V", names)
        self.assertIn("Nets-D", names)
        ids = [e["id"] for t in d["tabs"] for e in t["entries"]]
        self.assertEqual(len(ids), len(set(ids)))           # every station has its own id
        self.assertTrue(all(e["scope"] for t in d["tabs"] for e in t["entries"]
                            if e["name"] != "My flrig memory"))

    def test_upgrade_old_list(self):
        """A version-7 list with one 'Nets' tab is split into voice and digital nets."""
        old = {"version": 7, "settings": {"sorts": {"Nets": ["Frequency", False]}},
               "tabs": [{"name": "Nets", "id": "n1", "entries": [
                   {"id": "a", "freq_hz": 7_115_000, "mode": "USB-D", "name": "MAGNET MR04"},
                   {"id": "b", "freq_hz": 3_923_000, "mode": "LSB", "name": "Tar Heel Net"},
                   {"id": "c", "freq_hz": 144_500_000, "mode": "FM", "name": "AmRRON Local",
                    "comment": "MFSK32 (FLDIGI)"}]}]}
        data = copy.deepcopy(old)
        notes = stations.upgrade_data(data)
        self.assertEqual(data["version"], 9)
        tabs = {t["name"]: [e["name"] for e in t["entries"]] for t in data["tabs"]}
        self.assertEqual(tabs["Nets-V"], ["Tar Heel Net"])
        self.assertEqual(tabs["Nets-D"], ["MAGNET MR04", "AmRRON Local"])
        self.assertIn("Nets-V", data["settings"]["sorts"])
        self.assertTrue(notes)

    def test_save_and_load(self):
        import tempfile
        d = stations.default_data()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flrig_stations.json")
            old_path, stations.DATA_FILE = stations.DATA_FILE, path
            try:
                stations.save_data(d)
                loaded, warn = stations.load_data()
            finally:
                stations.DATA_FILE = old_path
        self.assertIsNone(warn)
        def entries(data):
            return json.dumps([t["entries"] for t in data["tabs"]], sort_keys=True)
        self.assertEqual(entries(loaded), entries(d))


if __name__ == "__main__":
    unittest.main()


class LinuxListMove(unittest.TestCase):
    """1.19: on Linux the list lives in ~/.local/share/flrig-emcomm. On first start it is
    copied (not moved) from where an older version kept it, and never overwritten."""

    def test_copied_once(self):
        import tempfile
        from flrig_emcomm import paths
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = os.path.join(tmp, "Applications", "Flrig EMCOMM")
            new_dir = os.path.join(tmp, "share", "flrig-emcomm")
            os.makedirs(old_dir)
            with open(os.path.join(old_dir, "flrig_stations.json"), "w") as f:
                f.write("old")
            saved = (paths.LINUX, paths.DATA_DIR, paths.DATA_FILE, paths.OLD_LIST_DIRS)
            try:
                paths.LINUX, paths.DATA_DIR = True, new_dir
                paths.DATA_FILE = os.path.join(new_dir, "flrig_stations.json")
                paths.OLD_LIST_DIRS = [os.path.join(tmp, "nothing"), old_dir]
                self.assertEqual(paths.bring_over_old_list(), old_dir)
                with open(paths.DATA_FILE) as f:
                    self.assertEqual(f.read(), "old")
                self.assertTrue(os.path.exists(os.path.join(old_dir, "flrig_stations.json")))
                with open(paths.DATA_FILE, "w") as f:
                    f.write("new")
                self.assertIsNone(paths.bring_over_old_list())   # never overwrites
                with open(paths.DATA_FILE) as f:
                    self.assertEqual(f.read(), "new")
            finally:
                paths.LINUX, paths.DATA_DIR, paths.DATA_FILE, paths.OLD_LIST_DIRS = saved
