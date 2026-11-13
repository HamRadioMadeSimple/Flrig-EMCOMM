"""Station table columns and sort orders."""

from .freq import band_of, band_rank
from .geo import SCOPES


# ==========================================================================
# Columns and sorting
# ==========================================================================
COLDEFS = {  # id: (heading, width, anchor, stretch)
    "fav": ("★", 34, "center", False),
    "rel": ("✔", 40, "center", False),
    "freq": ("Frequency", 120, "e", False),
    "mode": ("Mode", 62, "center", False),
    "bw": ("BW", 54, "center", False),
    "band": ("Band", 74, "center", False),
    "dist": ("Miles", 62, "center", False),
    "loc": ("Location", 130, "w", False),
    "name": ("Station / Name", 200, "w", True),
    "sched": ("Schedule (Eastern)", 160, "w", True),
    "comment": ("Comments", 250, "w", True),
    "cat": ("Category", 115, "w", False),
    "uses": ("Used", 60, "center", False),
}


ALL_COLS = tuple(COLDEFS)
TAB_COLS = tuple(c for c in ALL_COLS if c != "cat")


# key functions take (tab_index, position_in_tab, entry); ties broken by frequency
SORTS = {
    "Custom order": lambda ti, p, e: (ti, p),
    "Frequency": lambda ti, p, e: e["freq_hz"],
    "Name": lambda ti, p, e: e["name"].lower(),
    "Mode": lambda ti, p, e: e["mode"].lower(),
    "Bandwidth": lambda ti, p, e: e["bw"] or 0,
    "Band": lambda ti, p, e: band_rank(band_of(e["freq_hz"])),
    "Category": lambda ti, p, e: (ti, p),
    "Most used": lambda ti, p, e: -e["uses"],
    "Recently used": lambda ti, p, e: -e["last_used"],
    "Favorites first": lambda ti, p, e: 0 if e["fav"] else 1,
    "Reliable first": lambda ti, p, e: 0 if e["rel"] else 1,
    "Schedule": lambda ti, p, e: e["sched"].lower(),
    "Comments": lambda ti, p, e: e["comment"].lower(),
    "Location": lambda ti, p, e: (e["location"].lower() or "~"),
    "Distance": None,  # needs the home location; handled in refresh_view
    "Reach": lambda ti, p, e: SCOPES.index(e["scope"]) if e["scope"] in SCOPES else 9,
}


COL_SORT = {"fav": "Favorites first", "rel": "Reliable first", "freq": "Frequency", "mode": "Mode", "bw": "Bandwidth",
            "band": "Band", "name": "Name", "sched": "Schedule", "comment": "Comments",
            "cat": "Category", "uses": "Most used", "dist": "Distance",
            "loc": "Location"}


SORT_COL = {v: k for k, v in COL_SORT.items()}
DEFAULT_SORT = {"__fav__": ["Most used", False], "__all__": ["Frequency", False]}
