"""The station list: built-in stations, loading, saving and upgrading old lists."""

import logging
import json
import os
import re
import uuid

from .freq import DEFAULT_RIG_MAX, DEFAULT_RIG_MIN
from .geo import DEFAULT_HOME
from . import paths
from .paths import DATA_FILE, OLD_FILE, PKG_DIR

log = logging.getLogger(__name__)


# ==========================================================================
# Starter station list (HF) - from Emergency_Radio_Guide.docx + digital modes
# ==========================================================================
def new_id():
    return uuid.uuid4().hex[:12]


def mk(khz, mode, bw, name, sched="", comment="", fav=False):
    return {"id": new_id(), "freq_hz": int(round(khz * 1000)), "mode": mode, "bw": bw,
            "name": name, "sched": sched, "comment": comment, "fav": fav,
            "uses": 0, "last_used": 0}


def nets_entries():
    """From 'Ham Radio Nets & Digital Activity Summary'. Schedule column is Eastern time."""
    C = "FLdigi Contestia 4/250"
    n = []
    for region, sched, when in [
            ("MR01–MR03", "Wed 9:00 PM", "Wednesday 9:00 PM Eastern"),
            ("MR04", "Thu 9:00 PM", "Thursday 9:00 PM Eastern"),
            ("MR05 & MR07", "Mon 9:00 PM", "Monday 8:00 PM Central (9:00 PM Eastern)"),
            ("MR06", "Tue 9:00 PM", "Tuesday 8:00 PM Central (9:00 PM Eastern)"),
            ("MR08 & MR09", "Thu 10:00 PM", "Thursday 8:00 PM Mountain (10:00 PM Eastern)"),
            ("MR10", "Fri 10:00 PM", "Friday 7:00 PM Pacific (10:00 PM Eastern)")]:
        n.append(mk(7115, "USB-D", 3000, f"MAGNET {region}", sched,
                    f"Weekly, {when} · {C} · signal centered near 900 Hz on waterfall"))
    n.append(mk(14110, "USB-D", 3000, "AmRRON National HF Digital", "1st & 3rd Tue 4:00 PM",
                "1st & 3rd Tuesdays (cycle starts 1st Tue of month) · 20:00Z = 4:00 PM EDT / "
                "3:00 PM EST · SOI quick-ref says 20:30Z, confirm with Net Control · " + C))
    n.append(mk(7110, "USB-D", 3000, "AmRRON Rolling Regional (summer)", "1st & 3rd Tue 8:00 PM",
                "1st & 3rd Tuesdays 8:00 PM local, rolls east to west · 40 m during daylight "
                "time · " + C))
    n.append(mk(3588, "USB-D", 3000, "AmRRON Rolling Regional (winter)", "1st & 3rd Tue 8:00 PM",
                "1st & 3rd Tuesdays 8:00 PM local, rolls east to west · 80 m in winter; NCS may "
                "move bands · " + C))
    for khz, mode, what, sched, note in [
            (7107, "USB-D", "JS8Call", "Thu 9:00–9:30 PM",
             "0100–0130Z Fri · JS8Call 40 m NVIS · check-ins, POSREPs · groups @GHOSTNET, "
             "@GSTFLASH (emergency)"),
            (7107, "USB-D", "Winlink VARA HF", "Thu 9:30–10:00 PM",
             "0130–0200Z Fri · Winlink peer-to-peer + VARA HF (USB) · handshakes start ~0135Z"),
            (7077, "USB-D", "RTTY", "Thu 10:00–10:30 PM",
             "0200–0230Z Fri · RTTY via FLDIGI · short blind bursts / fallback traffic"),
            (7190, "LSB", "Voice (emergency only)", "Thu 10:30–11:00 PM",
             "0230–0300Z Fri · HF voice simplex · emergency fallback only, not a normal net")]:
        n.append(mk(khz, mode, 3000, f"GhostNet {what}", sched,
                    f"Every Thursday night, EDT (1 hr earlier in EST) · {note}"))
    return n


VOICE_MODES = ("USB", "LSB", "AM", "FM", "SSB")
DIGITAL_WORDS = re.compile(r"digital|js8|winlink|vara|rtty|mfsk|psk|fldigi|contestia|olivia|"
                           r"\bft[48]\b|packet|\bdata\b", re.I)


def is_voice_net(e):
    """A voice (phone) net: a voice mode and no digital mode named in it."""
    if str(e.get("mode") or "").strip().upper() not in VOICE_MODES:
        return False
    return not DIGITAL_WORDS.search(f"{e.get('name', '')} {e.get('comment', '')}")


def split_nets(entries):
    """Voice nets and digital (and CW) nets, keeping their order."""
    return ([e for e in entries if is_voice_net(e)], [e for e in entries if not is_voice_net(e)])


def upgrade_data(data):
    """Bring an older saved list up to the current version. Returns notes for the user."""
    notes = []
    if data.get("version", 2) < 3:
        removed = 0
        for t in data.get("tabs", []):
            keep = [e for e in t.get("entries", [])
                    if not str(e.get("name", "")).startswith("CB Channel")]
            removed += len(t.get("entries", [])) - len(keep)
            t["entries"] = keep
        if removed:
            notes.append(f"Removed {removed} CB channels (not used with an HF rig).")
        if not any(t.get("name", "").lower() == "nets" for t in data.get("tabs", [])):
            pos = next((i + 1 for i, t in enumerate(data["tabs"])
                        if t.get("name") == "Emergency"), 0)
            data["tabs"].insert(pos, {"name": "Nets", "entries": nets_entries()})
            notes.append("Added the Nets tab (MAGNET, AmRRON and GhostNet schedules).")
    if data.get("version", 2) < 4:
        if not any(t.get("name", "").lower() == "cw" for t in data.get("tabs", [])):
            pos = next((i + 1 for i, t in enumerate(data["tabs"])
                        if t.get("name") == "Ham Digital"), len(data["tabs"]))
            data["tabs"].insert(pos, {"name": "CW", "entries": []})
            notes.append("Added an empty CW tab.")
    if data.get("version", 2) < 6:
        for t in data.get("tabs", []):
            for e in t.get("entries", []):
                if not e.get("scope"):
                    e["scope"] = guess_scope(e, t.get("name", ""))
    if data.get("version", 2) < 7:
        tabs = data.get("tabs", [])
        names = {t.get("name", "").lower() for t in tabs}
        for t in tabs:
            if t.get("name") == "FM (10m)" and "10m fm" not in names:
                t["name"] = "10m FM"
                sorts = data.get("settings", {}).get("sorts", {})
                if "FM (10m)" in sorts:
                    sorts["10m FM"] = sorts.pop("FM (10m)")
                notes.append("Renamed the 'FM (10m)' tab to '10m FM'.")
        if "fm broadcast" not in names:
            pos = next((i + 1 for i, t in enumerate(tabs) if t.get("name") == "AM Broadcast"),
                       len(tabs))
            tabs.insert(pos, {"name": "FM Broadcast", "entries": []})
            notes.append("Added an empty 'FM Broadcast' tab for local FM stations.")
    if data.get("version", 2) < 8:
        tabs = data.get("tabs", [])
        names = {t.get("name", "").lower() for t in tabs}
        nets = next((t for t in tabs if t.get("name", "").lower() == "nets"), None)
        if nets is not None and not names & {"nets-v", "nets-d"}:
            nets.setdefault("id", new_id())
            voice, digital = split_nets(nets.get("entries", []))
            nets["name"], nets["entries"] = "Nets-V", voice
            dtab = {"name": "Nets-D", "entries": digital, "id": new_id()}
            tabs.insert(tabs.index(nets) + 1, dtab)
            moved_links = 0
            for t in tabs:  # stations shared onto Nets go to the matching new tab
                for e in t.get("entries", []):
                    also = e.get("also") or []
                    if nets["id"] in also and not is_voice_net(e):
                        e["also"] = [dtab["id"] if a == nets["id"] else a for a in also]
                        moved_links += 1
            st = data.setdefault("settings", {})
            sorts = st.get("sorts", {})
            if "Nets" in sorts:
                sorts["Nets-V"] = list(sorts["Nets"])
                sorts["Nets-D"] = list(sorts.pop("Nets"))
            orders = st.get("view_orders", {})
            if "Nets" in orders:
                old = orders.pop("Nets")
                orders["Nets-V"] = [i for i in old if any(e.get("id") == i for e in voice)]
                orders["Nets-D"] = [i for i in old if any(e.get("id") == i for e in digital)]
            for k in ("import_tab", "import_preset"):
                if st.get(k) == "Nets":
                    st[k] = "Nets-V"
            reqs = st.get("import_requests", {})
            if "Nets" in reqs:
                reqs["Nets-V"] = reqs.pop("Nets")
            notes.append(f"Split the Nets tab into Nets-V (voice, {len(voice)} stations) and "
                         f"Nets-D (digital, {len(digital)} stations).")
    if data.get("version", 2) < 9:
        for t in data.get("tabs", []):  # v9: the ✔ Reliable mark, off for every station
            for e in t.get("entries", []):
                e.setdefault("rel", False)
    data["version"] = 9
    return notes


def default_data():
    """A fresh list for a new user: the starter stations in data/stations_default.json."""
    with open(os.path.join(PKG_DIR, "data", "stations_default.json"), encoding="utf-8") as f:
        data = json.load(f)
    data["settings"] = default_settings()
    for t in data["tabs"]:
        t["entries"] = [normalize_entry(e) for e in t["entries"]]
    return data


def default_settings():
    return {"host": "127.0.0.1", "port": 12345,
            "geometry": "1200x700", "rig_min_hz": DEFAULT_RIG_MIN,
            "rig_max_hz": DEFAULT_RIG_MAX, "sorts": {}, "theme": "system",
            "home_lat": DEFAULT_HOME[0], "home_lon": DEFAULT_HOME[1],
            "home_label": DEFAULT_HOME[2], "freq_format": "khz"}


def guess_scope(e, tab_name):
    """Reach for the built-in stations (only fills in blanks)."""
    n = e.get("name", "")
    if tab_name == "Weather & Time":
        return "National" if n.startswith("WWV") else ("Region" if "NMN" in n else "International")
    if tab_name == "AM Broadcast":
        return "Local" if n.startswith("WPTF") else ("State" if n.startswith("WBT") else "Region")
    if tab_name == "Emergency":
        return "State" if "Tar Heel" in n else "Region"
    if tab_name in ("Nets", "Nets-V", "Nets-D"):
        return "National"
    if n == "My flrig memory":
        return ""
    return "International"


def normalize_entry(e):
    e.setdefault("id", new_id())
    e["freq_hz"] = int(e.get("freq_hz", 0))
    for k, v in (("mode", ""), ("bw", None), ("name", ""), ("sched", ""), ("comment", ""),
                 ("fav", False), ("uses", 0), ("last_used", 0)):
        e.setdefault(k, v)
    e["rel"] = bool(e.get("rel", False))  # ✔ reliable: a go-to station that usually comes in
    for k, v in (("location", ""), ("lat", None), ("lon", None), ("scope", "")):
        e.setdefault(k, v)
    if not isinstance(e.get("also"), list):
        e["also"] = []  # ids of extra tabs this station is also shown on (set by hand)
    return e


def tidy_tabs(data):
    """Give every tab an id and drop 'also' links to tabs that no longer exist."""
    for t in data["tabs"]:
        t.setdefault("id", new_id())
    valid = {t["id"] for t in data["tabs"]}
    for t in data["tabs"]:
        for e in t["entries"]:
            seen = []
            for tid in e.get("also", []):
                if tid in valid and tid != t["id"] and tid not in seen:
                    seen.append(tid)
            e["also"] = seen


def migrate_old(data, old):
    """Bring v1 entries over if their frequency isn't already in the new list."""
    have = {e["freq_hz"] for t in data["tabs"] for e in t["entries"]}
    tabs = {t["name"].lower(): t for t in data["tabs"]}
    added = 0
    for ot in old.get("tabs", []):
        for oe in ot.get("entries", []):
            hz = int(oe.get("freq_hz", 0))
            if not hz or hz in have:
                continue
            target = tabs.get(ot.get("name", "").lower()) or tabs.get("other")
            if target is None:
                target = {"name": "Other", "entries": []}
                data["tabs"].append(target)
                tabs["other"] = target
            target["entries"].append(normalize_entry({
                "freq_hz": hz, "mode": oe.get("mode", ""), "bw": oe.get("bw"),
                "name": oe.get("name", ""), "comment": oe.get("comment", "")}))
            have.add(hz)
            added += 1
    s = old.get("settings", {})
    for k in ("host", "port"):
        if k in s:
            data["settings"][k] = s[k]
    return added


def load_data():
    warn = None
    data = None
    moved_from = None
    if DATA_FILE == paths.DATA_FILE:   # the real list (tests use their own file)
        moved_from = paths.bring_over_old_list()
        if moved_from:
            log.info("Copied the station list from %s to %s", moved_from, DATA_FILE)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            notes = upgrade_data(data)
            if notes:
                warn = "Updated your station list:\n\n" + "\n".join(notes)
        except Exception as ex:
            log.error("Could not read %s", DATA_FILE, exc_info=True)
            backup = DATA_FILE + ".bad"
            try:
                os.replace(DATA_FILE, backup)
            except OSError:
                pass
            warn = f"Could not read {DATA_FILE} ({ex}).\nIt was renamed to {backup}."
    if data is None:
        data = default_data()
        data["settings"]["home_asked"] = False  # new user: ask where they are
        if os.path.exists(OLD_FILE):
            try:
                with open(OLD_FILE, "r", encoding="utf-8") as f:
                    n = migrate_old(data, json.load(f))
                if n:
                    warn = (f"Brought over {n} frequencies from your previous list "
                            f"(flrig_freqs.json) that weren't already included.")
            except Exception:
                log.warning("Could not bring over the old flrig_freqs.json list", exc_info=True)
    if moved_from and data is not None and warn is None:
        warn = (f"Your station list was copied from {moved_from} to {paths.DATA_DIR}, "
                f"where this version keeps it. The old copy was left in place.")
    s = default_settings()
    s.update(data.get("settings", {}))
    data["settings"] = s
    if not data.get("tabs"):
        data["tabs"] = [{"name": "Stations", "entries": []}]
    for t in data["tabs"]:
        t["entries"] = [normalize_entry(e) for e in t.get("entries", [])]
    tidy_tabs(data)
    data["version"] = 9
    return data, warn


def save_data(data):
    if DATA_FILE == paths.DATA_FILE:
        paths.make_data_dir()
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, DATA_FILE)
