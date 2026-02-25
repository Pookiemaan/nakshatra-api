"""
kundali.py
==========
Main Kundali (birth chart) generator.

Orchestrates ephemeris, house, panchang, dasha, and divisional chart modules
to produce a complete, structured Kundali output.

Usage:
    from kundali_engine.tools.kundali import generate_kundali

    chart = generate_kundali(
        year=1990, month=6, day=15,
        hour=10, minute=30, second=0,
        timezone_offset=5.5,        # IST = UTC+5:30
        latitude=28.6139,           # Delhi
        longitude=77.2090,
        house_system="whole_sign",  # or placidus, equal, koch
        ayanamsa="lahiri"           # or raman, kp, fagan
    )
"""

from datetime import datetime
from typing import Optional
import math

from ..core.ephemeris import (
    gregorian_to_jd, get_all_planets, J2000,
    SIGNS, NAKSHATRAS, nutation_and_obliquity, tropical_to_sidereal
)
from ..core.houses import (
    local_sidereal_time, get_house_cusps, planet_house_number
)
from ..core.panchang import compute_panchang
from ..core.dasha import compute_vimshottari_dasha, get_current_dasha
from ..core.divisional_charts import compute_divisional_chart


# ---------------------------------------------------------------------------
# Utility: degree formatting
# ---------------------------------------------------------------------------

def _dms(degrees: float) -> str:
    """Format decimal degrees as D°M'S\" string."""
    d = int(degrees)
    m_float = (degrees - d) * 60
    m = int(m_float)
    s = round((m_float - m) * 60, 1)
    return f"{d}°{m}'{s}\""


def _sign_from_longitude(lon: float) -> str:
    return SIGNS[int(lon / 30) % 12]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_kundali(
    year: int, month: int, day: int,
    hour: int = 0, minute: int = 0, second: int = 0,
    timezone_offset: float = 0.0,     # hours offset from UTC (e.g. 5.5 for IST)
    latitude: float = 0.0,
    longitude: float = 0.0,
    house_system: str = "whole_sign",
    ayanamsa: str = "lahiri",
    unknown_birth_time: bool = False,
) -> dict:
    """
    Generate a complete Kundali (birth chart).

    Args:
        year, month, day: Birth date (Gregorian)
        hour, minute, second: Birth time in LOCAL time
        timezone_offset: Hours ahead of UTC (e.g. 5.5 for India, -5 for EST)
        latitude: Geographic latitude in degrees (positive = North)
        longitude: Geographic longitude in degrees (positive = East)
        house_system: 'whole_sign', 'placidus', 'equal', 'koch'
        ayanamsa: 'lahiri', 'raman', 'kp', 'fagan'
        unknown_birth_time: If True, compute sunrise chart as uncertainty proxy

    Returns:
        Complete chart dict with planets, houses, panchang, dasha, divisionals
    """

    # ---- Time conversion: local → UTC ----
    local_decimal_hours = hour + minute / 60.0 + second / 3600.0
    utc_decimal_hours = local_decimal_hours - timezone_offset

    # Handle day rollover
    utc_day = day
    utc_month = month
    utc_year = year
    if utc_decimal_hours < 0:
        utc_decimal_hours += 24
        # Simple day rollback (full implementation would handle month/year boundaries)
        utc_day -= 1
        if utc_day == 0:
            utc_month -= 1
            if utc_month == 0:
                utc_month = 12
                utc_year -= 1
            days_in_month = [0,31,28,31,30,31,30,31,31,30,31,30,31]
            if utc_year % 4 == 0 and (utc_year % 100 != 0 or utc_year % 400 == 0):
                days_in_month[2] = 29
            utc_day = days_in_month[utc_month]
    elif utc_decimal_hours >= 24:
        utc_decimal_hours -= 24
        utc_day += 1

    jd = gregorian_to_jd(utc_year, utc_month, utc_day, utc_decimal_hours)
    T = (jd - J2000) / 36525.0

    # ---- Handle unknown birth time ----
    if unknown_birth_time:
        # Use solar noon as midpoint chart (convention when time is unknown)
        # Future: could generate three variants (sunrise/noon/sunset)
        jd_noon = gregorian_to_jd(year, month, day, 12.0 - timezone_offset)
        jd = jd_noon

    # ---- Obliquity and nutation ----
    dpsi, deps, obliquity = nutation_and_obliquity(T)

    # ---- Planet positions (geocentric engine) ----
    from ..core.ephemeris import compute_all_positions
    planets_raw, asc_tropical_ephem, _ = compute_all_positions(jd, latitude, longitude, ayanamsa)

    # ---- Local Sidereal Time and Houses ----
    lst = local_sidereal_time(jd, longitude)
    cusps_tropical, asc_tropical, mc_tropical = get_house_cusps(
        house_system, lst, latitude, obliquity
    )
    # Use accurate ascendant from geocentric ephemeris
    asc_tropical = asc_tropical_ephem

    # Convert cusps to sidereal
    cusps_sidereal = [tropical_to_sidereal(c, T, ayanamsa) for c in cusps_tropical]
    asc_sidereal = tropical_to_sidereal(asc_tropical, T, ayanamsa)
    mc_sidereal  = tropical_to_sidereal(mc_tropical,  T, ayanamsa)

    # ---- Planet house assignments ----
    planet_houses = {}
    for name, pos in planets_raw.items():
        house_num = planet_house_number(pos.sidereal_longitude, cusps_sidereal)
        planet_houses[name] = house_num

    # ---- Panchang ----
    panchang = compute_panchang(jd, latitude, longitude, ayanamsa)

    # ---- Moon sign and nakshatra (from ephemeris) ----
    moon_pos = planets_raw["Moon"]
    moon_sign = SIGNS[moon_pos.sign_index]
    moon_nakshatra = NAKSHATRAS[moon_pos.nakshatra_index]
    moon_nakshatra_pada = moon_pos.nakshatra_pada

    # ---- Ascendant sign ----
    lagna_sign = _sign_from_longitude(asc_sidereal)
    lagna_nak_idx = int(asc_sidereal / (360/27)) % 27
    lagna_nakshatra = NAKSHATRAS[lagna_nak_idx]

    # ---- Vimshottari Dasha ----
    birth_dt = datetime(year, month, day, hour, minute, second)
    dasha_periods = compute_vimshottari_dasha(moon_pos.sidereal_longitude, birth_dt)
    current_dasha = get_current_dasha(dasha_periods, datetime.now())

    # ---- Divisional charts ----
    divisional_charts = {}
    for division in ["D9", "D10", "D12"]:
        div_chart = compute_divisional_chart(planets_raw, division)
        divisional_charts[division] = {
            name: {
                "sign": pos.sign_name,
                "degree": round(pos.degree_in_sign, 2)
            }
            for name, pos in div_chart.items()
        }

    # ---- Format planet data for output ----
    formatted_planets = {}
    for name, pos in planets_raw.items():
        formatted_planets[name] = {
            "sidereal_longitude": round(pos.sidereal_longitude, 4),
            "tropical_longitude": round(pos.tropical_longitude, 4),
            "sign": SIGNS[pos.sign_index],
            "degree_in_sign": round(pos.degree_in_sign, 4),
            "degree_formatted": _dms(pos.degree_in_sign),
            "nakshatra": NAKSHATRAS[pos.nakshatra_index],
            "nakshatra_pada": pos.nakshatra_pada,
            "house": planet_houses[name],
            "is_retrograde": pos.is_retrograde,
        }

    # ---- Format house cusps ----
    formatted_cusps = []
    for i, cusp_sid in enumerate(cusps_sidereal):
        formatted_cusps.append({
            "house": i + 1,
            "sidereal_longitude": round(cusp_sid, 4),
            "sign": _sign_from_longitude(cusp_sid),
            "degree_formatted": _dms(cusp_sid % 30),
        })

    # ---- Assemble output ----
    return {
        "meta": {
            "input": {
                "date": f"{year}-{month:02d}-{day:02d}",
                "time": f"{hour:02d}:{minute:02d}:{second:02d}",
                "timezone_offset": timezone_offset,
                "latitude": latitude,
                "longitude": longitude,
                "house_system": house_system,
                "ayanamsa": ayanamsa,
                "unknown_birth_time": unknown_birth_time,
            },
            "julian_day": round(jd, 6),
            "julian_centuries_j2000": round(T, 8),
            "obliquity": round(obliquity, 6),
            "lst_degrees": round(lst, 6),
        },
        "lagna": {
            "sign": lagna_sign,
            "sidereal_longitude": round(asc_sidereal, 4),
            "degree_formatted": _dms(asc_sidereal % 30),
            "nakshatra": lagna_nakshatra,
            "nakshatra_pada": int(asc_sidereal / (360/27/4)) % 4 + 1,
        },
        "midheaven": {
            "sign": _sign_from_longitude(mc_sidereal),
            "sidereal_longitude": round(mc_sidereal, 4),
            "degree_formatted": _dms(mc_sidereal % 30),
        },
        "moon_sign": moon_sign,
        "moon_nakshatra": moon_nakshatra,
        "moon_nakshatra_pada": moon_nakshatra_pada,
        "planets": formatted_planets,
        "houses": formatted_cusps,
        "panchang": panchang,
        "dasha": {
            "system": "Vimshottari",
            "current": current_dasha,
            "all_periods": dasha_periods,
        },
        "divisional_charts": divisional_charts,
    }


# ---------------------------------------------------------------------------
# Unknown birth time helper
# ---------------------------------------------------------------------------

def generate_kundali_unknown_time(
    year: int, month: int, day: int,
    latitude: float, longitude: float,
    timezone_offset: float,
    ayanamsa: str = "lahiri"
) -> dict:
    """
    Generate three chart variants for unknown birth time:
    sunrise, solar noon, and sunset. Returns all three for uncertainty display.
    """
    from ..core.panchang import compute_sunrise_sunset
    from ..core.ephemeris import gregorian_to_jd as gjd

    jd_noon = gjd(year, month, day, 12.0 - timezone_offset)
    sun_times = compute_sunrise_sunset(jd_noon, latitude, longitude)

    def parse_utc_hour(time_str):
        if not time_str:
            return 6.0
        h, m = map(int, time_str.split(" UTC")[0].split(":"))
        return h + m / 60.0

    sr_hour = parse_utc_hour(sun_times.get("sunrise_utc"))
    ss_hour = parse_utc_hour(sun_times.get("sunset_utc"))
    noon_hour = (sr_hour + ss_hour) / 2

    def _local(utc_h):
        return (utc_h + timezone_offset) % 24

    variants = {}
    for label, utc_h in [("sunrise", sr_hour), ("noon", noon_hour), ("sunset", ss_hour)]:
        lh = _local(utc_h)
        h, m = int(lh), int((lh % 1) * 60)
        variants[label] = generate_kundali(
            year, month, day, h, m, 0,
            timezone_offset, latitude, longitude,
            house_system="whole_sign", ayanamsa=ayanamsa,
            unknown_birth_time=False
        )

    return {
        "unknown_birth_time": True,
        "note": "Three chart variants generated for sunrise, noon, and sunset. Planetary positions vary minimally; Lagna (ascendant) changes significantly.",
        "variants": variants
    }
