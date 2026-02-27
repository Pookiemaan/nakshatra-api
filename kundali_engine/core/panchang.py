"""
panchang.py
===========
Daily Panchang (Hindu almanac) calculations.

Five limbs of Panchang:
  1. Vara      — Day of week
  2. Tithi     — Lunar day (1–30)
  3. Nakshatra — Lunar mansion (1–27)
  4. Yoga      — Luni-solar yoga (1–27)
  5. Karana    — Half lunar day (1–11 cycle)

Plus: Sunrise, Sunset, Moonrise, Rahu Kala

Source: Drik Panchang algorithm; Meeus Ch. 15 (sunrise/sunset)
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from .ephemeris import (
    J2000, DEG_TO_RAD, RAD_TO_DEG,
    moon_longitude, sun_longitude, nutation_and_obliquity,
    gregorian_to_jd
)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

TITHIS = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dvadashi", "Trayodashi", "Chaturdashi", "Purnima",   # Shukla Paksha (1–15)
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dvadashi", "Trayodashi", "Chaturdashi", "Amavasya",  # Krishna Paksha (16–30)
]

PAKSHA = ["Shukla"] * 15 + ["Krishna"] * 15

YOGAS = [
    "Vishkumbha", "Preeti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti"
]

KARANAS = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garija",
    "Vanija", "Vishti", "Shakuni", "Chatushpada", "Nagava", "Kimstughna"
]

VARA = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Rahu Kala by day (slot index out of 8 equal parts of day)
RAHU_KALA_SLOT = {
    0: 8,  # Sunday   — 8th slot (4:30–6:00pm)
    1: 2,  # Monday   — 2nd slot (7:30–9:00am)
    2: 7,  # Tuesday  — 7th slot (3:00–4:30pm)
    3: 5,  # Wednesday — 5th slot (12:00–1:30pm)
    4: 6,  # Thursday  — 6th slot (1:30–3:00pm)
    5: 4,  # Friday    — 4th slot (10:30am–12:00pm)
    6: 3,  # Saturday  — 3rd slot (9:00–10:30am)
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]


# ---------------------------------------------------------------------------
# Core Panchang computation
# ---------------------------------------------------------------------------

def compute_tithi(sun_sid: float, moon_sid: float) -> dict:
    """
    Tithi = difference between Moon and Sun longitudes / 12°
    Each tithi = 12° of separation. 30 tithis per lunar month.
    """
    diff = (moon_sid - sun_sid) % 360.0
    tithi_idx = int(diff / 12.0)  # 0-based, 0–29
    tithi_elapsed = (diff % 12.0) / 12.0  # fraction elapsed

    return {
        "index": tithi_idx + 1,                    # 1-based (1–30)
        "name": TITHIS[tithi_idx],
        "paksha": PAKSHA[tithi_idx],
        "elapsed_pct": round(tithi_elapsed * 100, 1),
    }


def compute_nakshatra(moon_sid: float) -> dict:
    """
    Nakshatra of Moon. Each nakshatra = 360/27 = 13°20' arc.
    """
    span = 360.0 / 27.0
    nak_idx = int(moon_sid / span) % 27
    elapsed = (moon_sid % span) / span
    pada = int(elapsed * 4) + 1  # 1–4

    return {
        "index": nak_idx + 1,
        "name": NAKSHATRAS[nak_idx],
        "pada": pada,
        "elapsed_pct": round(elapsed * 100, 1),
    }


def compute_yoga(sun_sid: float, moon_sid: float) -> dict:
    """
    Yoga = (Sun longitude + Moon longitude) / (360/27)
    27 yogas, each 13°20'
    """
    combined = (sun_sid + moon_sid) % 360.0
    span = 360.0 / 27.0
    yoga_idx = int(combined / span) % 27

    return {
        "index": yoga_idx + 1,
        "name": YOGAS[yoga_idx],
    }


def compute_karana(sun_sid: float, moon_sid: float) -> dict:
    """
    Karana = half-tithi. Two karanas per tithi.
    First 57 karanas are movable (7 types × 8 repeats + 1 partial),
    last 4 are fixed.
    """
    diff = (moon_sid - sun_sid) % 360.0
    karana_num = int(diff / 6.0)  # 0–59

    if karana_num == 0:
        name = "Kimstughna"
    elif karana_num >= 57:
        fixed = ["Shakuni", "Chatushpada", "Nagava", "Kimstughna"]
        name = fixed[min(karana_num - 57, 3)]
    else:
        movable = ["Bava", "Balava", "Kaulava", "Taitila", "Garija", "Vanija", "Vishti"]
        name = movable[(karana_num - 1) % 7]

    return {
        "number": karana_num + 1,
        "name": name,
    }


# ---------------------------------------------------------------------------
# Sunrise / Sunset (Meeus Ch. 15)
# ---------------------------------------------------------------------------

def _sun_hour_angle(latitude: float, declination: float,
                    altitude: float = -0.8333) -> Optional[float]:
    """
    Hour angle for standard sunrise/sunset (altitude = -0.8333° accounts for refraction).
    Returns None at polar regions where sun never rises/sets.
    """
    cos_H = ((math.sin(altitude * DEG_TO_RAD)
               - math.sin(latitude * DEG_TO_RAD) * math.sin(declination * DEG_TO_RAD))
             / (math.cos(latitude * DEG_TO_RAD) * math.cos(declination * DEG_TO_RAD)))
    if abs(cos_H) > 1.0:
        return None
    return math.acos(cos_H) * RAD_TO_DEG


def compute_sunrise_sunset(jd_noon: float, latitude: float,
                            longitude: float) -> dict:
    """
    Compute sunrise and sunset times (UTC) for a given geographic location.
    jd_noon: Julian Day of local noon (approximate)
    Source: Meeus Ch. 15
    """
    T = (jd_noon - J2000) / 36525.0
    dpsi, deps, obliquity = nutation_and_obliquity(T)

    # Solar coordinates at noon
    sun_lon_trop, _sun_R = sun_longitude(T, dpsi)
    sun_lon_r = sun_lon_trop * DEG_TO_RAD
    declination = math.asin(math.sin(obliquity * DEG_TO_RAD) * math.sin(sun_lon_r)) * RAD_TO_DEG

    # Right ascension
    ra = math.atan2(
        math.cos(obliquity * DEG_TO_RAD) * math.sin(sun_lon_r),
        math.cos(sun_lon_r)
    ) * RAD_TO_DEG
    ra = ra % 360.0

    H0 = _sun_hour_angle(latitude, declination)
    if H0 is None:
        return {"sunrise": None, "sunset": None, "polar": True}

    # Transit (solar noon) in fraction of day
    from .houses import greenwich_mean_sidereal_time
    theta0 = greenwich_mean_sidereal_time(jd_noon)  # GMST in degrees

    m0 = (ra - longitude - theta0) / 360.0
    m0 = m0 % 1.0

    m_rise = m0 - H0 / 360.0
    m_set  = m0 + H0 / 360.0

    def _to_hhmm(frac: float) -> str:
        frac = frac % 1.0
        total_min = round(frac * 24 * 60)
        h, m = divmod(total_min, 60)
        return f"{h:02d}:{m:02d} UTC"

    return {
        "sunrise_utc": _to_hhmm(m_rise),
        "sunset_utc":  _to_hhmm(m_set),
        "solar_noon_utc": _to_hhmm(m0),
        "polar": False,
    }


# ---------------------------------------------------------------------------
# Rahu Kala
# ---------------------------------------------------------------------------

def compute_rahu_kala(sunrise_utc: str, sunset_utc: str, weekday: int) -> dict:
    """
    Rahu Kala = 1/8 of daytime, slot varies by weekday.
    weekday: 0=Sunday … 6=Saturday
    """
    def parse_hhmm(s: str) -> float:
        h, m = map(int, s.split(" UTC")[0].split(":"))
        return h + m / 60.0

    if not sunrise_utc or not sunset_utc:
        return {"start": None, "end": None}

    sr = parse_hhmm(sunrise_utc)
    ss = parse_hhmm(sunset_utc)
    day_duration = ss - sr
    slot_duration = day_duration / 8.0
    slot = RAHU_KALA_SLOT[weekday] - 1   # 0-based slot index

    start = sr + slot * slot_duration
    end   = start + slot_duration

    def fmt(h: float) -> str:
        hh = int(h) % 24
        mm = round((h % 1) * 60)
        return f"{hh:02d}:{mm:02d} UTC"

    return {"start": fmt(start), "end": fmt(end)}


# ---------------------------------------------------------------------------
# Full Panchang
# ---------------------------------------------------------------------------

def compute_panchang(jd: float, latitude: float, longitude: float,
                     ayanamsa: str = "lahiri") -> dict:
    """
    Compute complete panchang for given Julian Day and location.
    """
    from .ephemeris import (
        get_ayanamsa, tropical_to_sidereal,
        moon_longitude, sun_longitude, nutation_and_obliquity
    )

    T = (jd - J2000) / 36525.0
    dpsi, deps, obliquity = nutation_and_obliquity(T)

    sun_trop, _sun_R = sun_longitude(T, dpsi)
    moon_trop, _ = moon_longitude(T)

    sun_sid  = tropical_to_sidereal(sun_trop, T, ayanamsa)
    moon_sid = tropical_to_sidereal(moon_trop, T, ayanamsa)

    # Day of week from JD
    weekday = int(jd + 1.5) % 7   # 0=Sunday

    tithi     = compute_tithi(sun_sid, moon_sid)
    nakshatra = compute_nakshatra(moon_sid)
    yoga      = compute_yoga(sun_sid, moon_sid)
    karana    = compute_karana(sun_sid, moon_sid)
    sun_times = compute_sunrise_sunset(jd, latitude, longitude)

    rahu_kala = compute_rahu_kala(
        sun_times.get("sunrise_utc", ""),
        sun_times.get("sunset_utc", ""),
        weekday
    )

    return {
        "vara": VARA[weekday],
        "tithi": tithi,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "sunrise": sun_times.get("sunrise_utc"),
        "sunset": sun_times.get("sunset_utc"),
        "solar_noon": sun_times.get("solar_noon_utc"),
        "rahu_kala": rahu_kala,
        "ayanamsa": ayanamsa,
    }
