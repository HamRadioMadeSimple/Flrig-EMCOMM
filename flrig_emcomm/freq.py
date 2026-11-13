"""Bands, frequency formatting and parsing."""


DEFAULT_MODES = ["USB", "LSB", "USB-D", "LSB-D", "AM", "AM-D", "FM", "FM-D",
                 "CW", "CW-R", "RTTY", "RTTY-R"]
COMMON_BWS = ["", "50", "100", "250", "500", "1200", "1800", "2400", "2700",
              "3000", "3600", "6000", "9000", "10000", "15000"]
# Rig coverage. IC-7300 receives 30 kHz - 74.8 MHz. Change under Rig > Frequency range.
DEFAULT_RIG_MIN = 30_000
DEFAULT_RIG_MAX = 74_800_000


# ==========================================================================
# Bands (already includes VHF/UHF so the same data works for a V/U rig later)
# ==========================================================================
HAM_BANDS = [(1800, 2000, "160m"), (3500, 4000, "80m"), (5330, 5410, "60m"),
             (7000, 7300, "40m"), (10100, 10150, "30m"), (14000, 14350, "20m"),
             (18068, 18168, "17m"), (21000, 21450, "15m"), (24890, 24990, "12m"),
             (28000, 29700, "10m"), (50000, 54000, "6m"), (144000, 148000, "2m"),
             (222000, 225000, "1.25m"), (420000, 450000, "70cm")]


OTHER_BANDS = [(530, 1710, "MW BC"), (2300, 2500, "120m BC"), (3200, 3400, "90m BC"),
               (4750, 5110, "60m BC"), (5800, 6300, "49m BC"), (7300, 7800, "41m BC"),
               (9250, 9995, "31m BC"), (11500, 12200, "25m BC"), (13500, 13900, "22m BC"),
               (15000, 15900, "19m BC"), (17400, 17950, "16m BC"), (21450, 21950, "13m BC"),
               (25600, 26100, "11m BC"), (88000, 108000, "FM BC"),
               (162400, 162550, "NOAA WX"), (462550, 467725, "FRS/GMRS")]


def band_of(hz):
    khz = hz / 1000
    for lo, hi, name in HAM_BANDS + OTHER_BANDS:
        if lo <= khz <= hi:
            return name
    if khz < 300:
        return "LF"
    if khz < 3000:
        return "MF"
    if khz < 30000:
        return "HF"
    if khz < 300000:
        return "VHF"
    return "UHF"


def band_rank(name):
    for lo, hi, n in HAM_BANDS + OTHER_BANDS:
        if n == name:
            return lo
    return {"LF": 0, "MF": 300, "HF": 3000, "VHF": 30000, "UHF": 300000}.get(name, 9e9)


# ==========================================================================
# Helpers
# ==========================================================================
def fmt_khz(hz):
    return f"{hz / 1000:.3f}"


# How frequencies are shown: Station > Frequency display
FREQ_FORMATS = [("kHz   (7115.000)", "khz"), ("MHz   (7.115000)", "mhz"),
                ("Rig style   (7.115.000)", "rig")]


FREQ_FMT = {"value": "khz"}  # set from the saved settings when the app starts


def fmt_rig(hz):
    """Like the IC-7300's display: MHz.kHz.Hz, e.g. 7.115.000"""
    hz = int(round(hz))
    return f"{hz // 1_000_000}.{hz // 1000 % 1000:03d}.{hz % 1000:03d}"


def fmt_disp(hz, unit=False):
    """A frequency in the chosen format. kHz: HF as 7268.000, VHF/UHF as 101.5 MHz.
    MHz: 7.268000. Rig style: 7.268.000. unit=True adds kHz/MHz."""
    style = FREQ_FMT["value"]
    if style == "mhz":
        return f"{hz / 1e6:.6f}" + (" MHz" if unit else "")
    if style == "rig":
        return fmt_rig(hz) + (" MHz" if unit else "")
    if hz >= 30_000_000:
        return f"{hz / 1e6:.4f}".rstrip("0").rstrip(".") + " MHz"
    return fmt_khz(hz) + (" kHz" if unit else "")


def fmt_readout(hz):
    """The big frequency readout at the top (dashes when the rig isn't connected)."""
    style = FREQ_FMT["value"]
    if not hz:
        return {"khz": "--------.--- kHz", "mhz": "--.------ MHz",
                "rig": "--.---.--- MHz"}[style]
    if style == "khz":
        return f"{hz / 1000:,.3f} kHz"
    return fmt_disp(hz, unit=True)


def parse_freq_to_hz(text, unit=None):
    """Accepts 7268, 7268.0 kHz, 7.268 MHz, 7.268M, 7268000 Hz, 101.5.
    Bare numbers: under 100 -> MHz; 100-999 with a fraction (101.5, 146.52) -> MHz;
    whole numbers (680, 7268) -> kHz. 'unit' ("mhz"/"khz") is used when the text has none."""
    t = str(text).strip().lower().replace(",", "").replace(" ", "")
    if not t:
        raise ValueError("Frequency is empty")
    mult = None
    for suffix, m in (("mhz", 1000.0), ("khz", 1.0), ("hz", 0.001), ("m", 1000.0), ("k", 1.0)):
        if t.endswith(suffix):
            t, mult = t[: -len(suffix)], m
            break
    if mult is None and unit:
        mult = {"mhz": 1000.0, "khz": 1.0}[unit]
    v = float(t)
    if mult is None:
        if v < 100 or (v < 1000 and v != int(v)):
            mult = 1000.0
        else:
            mult = 1.0
    khz = v * mult
    if khz <= 0:
        raise ValueError("Frequency must be positive")
    return int(round(khz * 1000))


def parse_bw(text):
    t = str(text or "").strip().lower().replace("hz", "")
    if not t:
        return None
    return int(float(t))
