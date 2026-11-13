"""Import tool logic: AI prompt builder and the CSV / AI-reply reader."""

import csv
import re

from .freq import band_of, fmt_khz, parse_bw, parse_freq_to_hz
from .geo import norm_scope, to_float


AI_PROMPT = """I keep a radio station list in an app. Please make a list of: {topic}.

Put the CSV right in your reply as plain text (a code block is fine). Do not make a file or a download link, and do not add any other text. It must start with exactly this header row:
name,frequency,mode,bw,schedule,comment,location,lat,lon,scope

Column rules:
- name: station name and/or call sign (for example: {ex_name})
- frequency: always include the unit, for example "{ex_freq}"
- mode: {mode_rule}
- bw: {bw_rule}
- schedule: days/times it is on in US Eastern time, or 24/7, or blank if unknown
- comment: genre or format, plus a short useful note
- location: city and state (or country) of the station or transmitter
- lat, lon: transmitter (or city) coordinates in decimal degrees; blank if unknown
- scope: who it serves - Local, State, Region, National or International
Put double quotes around any value that contains a comma. Only list real stations, and leave a value blank rather than guessing.

Important: list ONLY what was asked for: {topic}.{extra}"""


# Ready-made requests, one per kind of list. {dist} and {home} are filled in for you.
# People can edit the wording; "Reset to default" brings back the text below.
IMPORT_PRESETS = [
    {"name": "AM Broadcast", "tab": "AM Broadcast", "kind": "am",
     "text": "local AM radio stations within {dist} miles of {home}, with their genre"},
    {"name": "FM Broadcast", "tab": "FM Broadcast", "kind": "fm",
     "text": "local FM radio stations within {dist} miles of {home}, with their genre"},
    {"name": "Emergency", "tab": "Emergency", "kind": "hf",
     "text": "HF emergency and disaster nets and frequencies used within {dist} miles of "
             "{home} (ARES, RACES, SKYWARN, hurricane and state emergency nets), with their "
             "schedules"},
    {"name": "Nets-V", "tab": "Nets-V", "kind": "hf", "mode": "USB or LSB", "bw": "3000",
     "ex_name": "Hurricane Watch Net", "ex_freq": "14325 kHz",
     "text": "regular HF amateur radio voice (phone) nets that can be heard within {dist} "
             "miles of {home}, with the day and time of each net"},
    {"name": "Nets-D", "tab": "Nets-D", "kind": "hf", "mode": "USB-D or LSB-D", "bw": "3000",
     "ex_name": "AmRRON National HF Digital", "ex_freq": "14110 kHz",
     "text": "regular HF amateur radio digital-mode nets (JS8Call, Fldigi, Winlink, RTTY) "
             "that can be heard within {dist} miles of {home}, with the day and time and the "
             "digital mode of each net"},
    {"name": "Weather & Time", "tab": "Weather & Time", "kind": "hf",
     "text": "HF weather broadcasts, marine and aviation (VOLMET) weather, and time signal "
             "stations that can be heard from {home}, with their broadcast times"},
    {"name": "Shortwave", "tab": "Shortwave", "kind": "hf",
     "text": "shortwave broadcast stations that can be heard from {home}, with their "
             "schedules and language"},
    {"name": "Ham Digital", "tab": "Ham Digital", "kind": "hf", "mode": "USB-D", "bw": "3000",
     "ex_name": "FT8 20m", "ex_freq": "14074 kHz",
     "text": "standard HF amateur radio digital-mode dial frequencies for each band (FT8, FT4, "
             "JS8Call, PSK31, WSPR, Winlink/VARA)"},
    {"name": "CW", "tab": "CW", "kind": "hf", "mode": "CW", "bw": "500",
     "ex_name": "40m CW QRP calling", "ex_freq": "7030 kHz",
     "text": "common HF amateur radio CW calling frequencies and CW nets, with schedules"},
    {"name": "10m FM", "tab": "10m FM", "kind": "hf", "mode": "FM", "bw": "leave blank",
     "ex_name": "10m FM simplex calling", "ex_freq": "29.600 MHz",
     "text": "10 meter amateur FM simplex and repeater frequencies in the United States"},
    {"name": "Custom", "tab": "Imported", "kind": None, "text": ""},
]


PRESET_BY_NAME = {pr["name"]: pr for pr in IMPORT_PRESETS}
IMPORT_DISTANCES = [5, 10, 15, 25, 50, 100, 150, 250]
DIST_RE = re.compile(r"within \d+ miles", re.I)


def build_ai_prompt(topic, preset=None):
    """Fill the prompt with examples that match the request, so the AI isn't nudged
    toward the wrong kind of station. The words typed win; the list type is the fallback."""
    t = " " + topic + " "
    is_am = bool(re.search(r"\bAM\b|\bA\.M\.|medium ?wave|\bMW\b", t)) or "am radio" in t.lower()
    ham = re.search(r"\b10 ?m(eters?)?\b|amateur|\bham\b|repeater|simplex", t, re.I)
    is_fm = bool(re.search(r"\bFM\b", t)) and not ham
    kind = "am" if is_am and not is_fm else ("fm" if is_fm and not is_am else None)
    if kind is None and preset:
        kind = preset.get("kind")
    if kind == "am":
        ex_name, ex_freq, mode_rule, bw_rule = "WPTF 680", "680 kHz", "AM", "6000"
        extra = " These are AM broadcast (medium wave) stations, 530-1700 kHz only."
    elif kind == "fm":
        ex_name, ex_freq, mode_rule, bw_rule = "WQDR 94.7", "94.7 MHz", "FM", "leave blank"
        extra = " These are FM broadcast stations, 88-108 MHz only."
    else:
        ex_name, ex_freq = "WWV or Hurricane Watch Net", "10000 kHz\" or \"14325 kHz"
        mode_rule = "one of USB, LSB, USB-D, LSB-D, AM, FM, CW"
        bw_rule = ("filter width in Hz (6000 for AM, 3000 for SSB or data, 500 for CW); "
                   "leave blank for FM")
        extra = ""
        if preset and preset.get("mode"):
            mode_rule, bw_rule = preset["mode"], preset["bw"]
            ex_name, ex_freq = preset["ex_name"], preset["ex_freq"]
        if kind == "hf":
            extra = " Only include frequencies from 1.8 to 30 MHz (HF)."
    return AI_PROMPT.format(topic=topic.strip().rstrip("."), ex_name=ex_name, ex_freq=ex_freq,
                            mode_rule=mode_rule, bw_rule=bw_rule, extra=extra)


FIELD_ALIASES = {
    "name": ("name", "station", "station name", "call", "call sign", "callsign", "call_sign"),
    "freq": ("frequency", "freq", "frequency_khz", "frequency_mhz", "freq_mhz", "freq_khz",
             "frequency (mhz)", "frequency (khz)", "dial", "dial frequency"),
    "mode": ("mode",),
    "bw": ("bw", "bandwidth", "filter"),
    "sched": ("schedule", "hours", "time", "times", "day/time", "days"),
    "comment": ("comment", "comments", "notes", "note", "description"),
    "genre": ("genre", "format", "type"),
    "location": ("location", "city", "city of license", "qth", "transmitter"),
    "lat": ("lat", "latitude"),
    "lon": ("lon", "lng", "long", "longitude"),
    "scope": ("scope", "reach", "coverage"),
    "tab": ("tab", "category"),
    "fav": ("favorite", "fav", "favourite"),
    "rel": ("reliable", "go-to", "goto"),
    "also": ("also_on",),
}


def same_station(a, b):
    """'WWV' and 'WWV Colorado', or 'AmRRON' and 'AmRRON Rolling Regional', are the same
    station when they're on the same frequency."""
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return False
    return a == b or a in b or b in a or a.split()[0] == b.split()[0]


UPDATE_FIELDS = ("location", "lat", "lon", "scope", "sched", "comment", "mode", "bw")


FIELD_LABEL = {"location": "location", "lat": "coordinates", "lon": "coordinates",
               "scope": "reach", "sched": "schedule", "comment": "comments", "mode": "mode",
               "bw": "bandwidth"}


def _loc_key(v):
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def station_changes(e, r):
    """What an imported row would change on an existing station.
    Returns (fills, replaces): fills only add missing info; replaces overwrite something."""
    fills, replaces = [], []
    for k in UPDATE_FIELDS:
        new, old = r.get(k), e.get(k)
        if new in (None, ""):
            continue
        if k in ("lat", "lon"):
            if old is not None and abs(float(old) - float(new)) < 1e-4:
                continue
        elif k == "bw":
            if old == new:
                continue
        else:
            if str(old or "").strip() == str(new).strip():
                continue
            if k == "location" and old and _loc_key(old) == _loc_key(new):
                fills.append(k)  # same place, just tidier spelling ("Raleigh NC" -> "Raleigh, NC")
                continue
        (fills if old in (None, "") else replaces).append(k)
    return fills, replaces


def _labels(keys):
    out = []
    for k in keys:
        if FIELD_LABEL[k] not in out:
            out.append(FIELD_LABEL[k])
    return ", ".join(out)


def parse_station_table(text):
    """Read CSV, tab-separated or a Markdown table (what AIs usually reply with).
    Returns (rows, error). Each row has the station fields plus 'tab' and 'error'."""
    lines = [l for l in text.replace("\r", "").split("\n") if not l.strip().startswith("```")]
    start = next((i for i, l in enumerate(lines)
                  if "freq" in l.lower() and any(k in l.lower() for k in ("name", "station", "call"))),
                 None)
    if start is None:
        return [], ("Couldn't find the header row. It needs at least a 'name' and a "
                    "'frequency' column.")
    lines = lines[start:]
    if lines[0].strip().startswith("|"):
        recs = []
        for l in lines:
            l = l.strip()
            if not l.startswith("|"):
                if recs:
                    break
                continue
            cells = [c.strip() for c in l.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            recs.append(cells)
    else:
        delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
        # a line with no separator at all is the AI talking ("Enjoy!"), not a station
        lines = [l for l in lines if delim in l]
        recs = [r for r in csv.reader(lines, delimiter=delim) if any(c.strip() for c in r)]
    header = [h.strip().lower() for h in recs[0]]
    col = {}
    for key, aliases in FIELD_ALIASES.items():
        for i, h in enumerate(header):
            if h in aliases and key not in col:
                col[key] = i
    if "freq" not in col:
        col["freq"] = next((i for i, h in enumerate(header) if "freq" in h), None)
        if col["freq"] is None:
            return [], "No frequency column found."
    fh = header[col["freq"]]
    unit = "mhz" if "mhz" in fh else ("khz" if "khz" in fh else None)
    rows = []
    for r in recs[1:]:
        def get(k):
            i = col.get(k)
            return r[i].strip() if i is not None and i < len(r) else ""
        row = {"name": get("name"), "mode": get("mode").upper(), "sched": get("sched"),
               "location": get("location"), "scope": norm_scope(get("scope")),
               "tab": get("tab"), "fav": get("fav").lower() in ("yes", "y", "true", "1", "★"),
               "rel": get("rel").lower() in ("yes", "y", "true", "1", "✔"),
               "also_names": [a.strip() for a in get("also").split("|") if a.strip()],
               "error": "", "bw": None, "freq_hz": 0, "lat": None, "lon": None}
        genre, note = get("genre"), get("comment")
        parts = [x for x in (genre, note) if x]
        if genre and note and genre.lower() in note.lower():
            parts = [note]
        row["comment"] = " · ".join(parts)
        try:
            row["freq_hz"] = parse_freq_to_hz(get("freq"), unit)
        except ValueError:
            row["error"] = f"Can't read frequency '{get('freq')}'"
        try:
            row["bw"] = parse_bw(get("bw"))
        except ValueError:
            row["bw"] = None
        if row["mode"] in ("WFM", "FM-W", "NFM"):
            row["mode"] = "FM"
        if not row["mode"] and row["freq_hz"]:
            b = band_of(row["freq_hz"])
            row["mode"] = "FM" if b == "FM BC" else ("AM" if b.endswith("BC") else "USB")
        lat, lon = to_float(get("lat")), to_float(get("lon"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            row["lat"], row["lon"] = lat, lon
        if not row["name"] and not row["error"]:
            row["name"] = fmt_khz(row["freq_hz"]) + " kHz"
        rows.append(row)
    return rows, None


# ==========================================================================
# Import dialog
# ==========================================================================
ROW_TAB = "(each row's 'tab' column)"
