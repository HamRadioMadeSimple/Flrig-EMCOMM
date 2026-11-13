"""Home location, grid squares, distances and reach."""

import math
import re


SCOPES = ["Local", "State", "Region", "National", "International"]
DIST_CHOICES = [5, 10, 15, 25, 50, 100]
DEFAULT_HOME = (35.7796, -78.6382, "Raleigh, NC")


def miles_between(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(a))


def grid_to_latlon(grid):
    """Maidenhead grid square (FM05 or FM05pt) -> centre lat, lon."""
    g = grid.strip().upper()
    if not re.fullmatch(r"[A-R]{2}\d{2}([A-X]{2})?", g):
        raise ValueError("not a grid square")
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3])
    if len(g) == 6:
        lon += (ord(g[4]) - 65) * (2 / 24) + 1 / 24
        lat += (ord(g[5]) - 65) * (1 / 24) + 1 / 48
    else:
        lon += 1
        lat += 0.5
    return lat, lon


def parse_location(text):
    """'35.78, -78.64' or a grid square like FM05 -> (lat, lon)."""
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)\s*", text or "")
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
        raise ValueError("out of range")
    return grid_to_latlon(text)


def to_float(v):
    try:
        return float(str(v).strip()) if str(v).strip() not in ("", "None") else None
    except ValueError:
        return None


def norm_scope(v):
    v = str(v or "").strip().lower()
    for sc in SCOPES:
        if v == sc.lower() or (v and sc.lower().startswith(v)):
            return sc
    return {"regional": "Region", "nation": "National", "intl": "International",
            "worldwide": "International", "global": "International"}.get(v, "")
