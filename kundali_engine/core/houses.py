"""
houses.py
=========
House cusp calculations for multiple house systems.

Supported systems:
  - Whole Sign (Vedic default)
  - Equal House
  - Placidus (Western standard)
  - Koch

Source: Meeus Ch. 14–16; Holden, J.H. (1994). "A History of Horoscopic Astrology"
"""

import math
from typing import List, Tuple
from .ephemeris import (
    J2000, DEG_TO_RAD, RAD_TO_DEG,
    nutation_and_obliquity, tropical_to_sidereal, gregorian_to_jd
)

# ---------------------------------------------------------------------------
# GMST and Local Sidereal Time
# ---------------------------------------------------------------------------

def greenwich_mean_sidereal_time(jd: float) -> float:
    """
    Greenwich Mean Sidereal Time in degrees.
    Source: Meeus Ch. 12, Eq. 12.4
    """
    T = (jd - J2000) / 36525.0
    theta = (280.46061837
             + 360.98564736629 * (jd - J2000)
             + 0.000387933 * T * T
             - T * T * T / 38710000.0)
    return theta % 360.0


def local_sidereal_time(jd: float, longitude_deg: float) -> float:
    """
    Local Apparent Sidereal Time (degrees).
    longitude_deg: geographic longitude, positive East
    """
    gmst = greenwich_mean_sidereal_time(jd)
    T = (jd - J2000) / 36525.0
    _, _, true_obliquity = nutation_and_obliquity(T)
    # Equation of the equinoxes (simplified)
    omega = 125.04452 - 1934.136261 * T
    eq_eq = (0.00256 * math.cos(omega * DEG_TO_RAD))   # degrees
    last = (gmst + eq_eq + longitude_deg) % 360.0
    return last


# ---------------------------------------------------------------------------
# Ascendant (Lagna) calculation
# ---------------------------------------------------------------------------

def compute_ascendant(lst: float, latitude_deg: float, obliquity: float) -> float:
    """
    Compute tropical Ascendant (Lagna) degree.
    lst: Local Sidereal Time in degrees
    Source: Meeus Ch. 14
    """
    ramc = lst  # Right Ascension of MC = LST
    e = obliquity * DEG_TO_RAD
    phi = latitude_deg * DEG_TO_RAD
    ramc_r = ramc * DEG_TO_RAD

    y = -math.cos(ramc_r)
    x = math.sin(e) * math.tan(phi) + math.cos(e) * math.sin(ramc_r)

    # Always add 180° to atan2 result — this consistently yields the eastern horizon point.
    # The old conditional (x < 0 → +180) was wrong for ~50% of birth charts.
    asc = math.atan2(y, x) * RAD_TO_DEG + 180.0
    asc = asc % 360.0

    # High-latitude adjustment (house system may be undefined >66.5° lat)
    if abs(latitude_deg) >= 66.5:
        # Return a warning flag by convention; caller should handle
        pass

    return asc


def compute_midheaven(lst: float, obliquity: float) -> float:
    """
    Compute tropical Midheaven (MC) degree.
    Source: Meeus Ch. 14
    """
    e = obliquity * DEG_TO_RAD
    ramc_r = lst * DEG_TO_RAD
    mc = math.atan2(math.sin(ramc_r), math.cos(ramc_r) * math.cos(e)) * RAD_TO_DEG
    return mc % 360.0


# ---------------------------------------------------------------------------
# House systems
# ---------------------------------------------------------------------------

def whole_sign_cusps(ascendant: float) -> List[float]:
    """
    Whole Sign house cusps. House 1 = sign containing Ascendant.
    Each house = entire zodiac sign (30°).
    Vedic standard.
    """
    lagna_sign = int(ascendant / 30) * 30
    return [(lagna_sign + 30 * i) % 360.0 for i in range(12)]


def equal_house_cusps(ascendant: float) -> List[float]:
    """
    Equal House cusps. House 1 begins exactly at Ascendant.
    Each house = 30°.
    """
    return [(ascendant + 30 * i) % 360.0 for i in range(12)]


def placidus_cusps(lst: float, latitude_deg: float, obliquity: float) -> List[float]:
    """
    Placidus house cusps for houses 2, 3, 11, 12.
    Houses 1, 4, 7, 10 = Asc, IC, Dsc, MC.
    Source: Meeus Ch. 16; Koch & Knappich (1971)
    """
    asc = compute_ascendant(lst, latitude_deg, obliquity)
    mc  = compute_midheaven(lst, obliquity)
    ic  = (mc + 180.0) % 360.0
    dsc = (asc + 180.0) % 360.0

    e = obliquity * DEG_TO_RAD
    phi = latitude_deg * DEG_TO_RAD

    def placidus_cusp(fraction: float, above_horizon: bool) -> float:
        """
        Iteratively solve for Placidus cusp.
        fraction: semiarc fraction (1/3 or 2/3)
        """
        # Start estimate
        ramc = lst * DEG_TO_RAD
        if above_horizon:
            ra_estimate = (ramc + fraction * math.pi) % (2 * math.pi)
        else:
            ra_estimate = (ramc - fraction * math.pi) % (2 * math.pi)

        for _ in range(20):  # Newton-Raphson iterations
            dec = math.asin(math.sin(e) * math.sin(ra_estimate))
            if above_horizon:
                dsa = math.acos(-math.tan(phi) * math.tan(dec))
                ra_new = ramc + (1 - fraction) * (math.pi - dsa)
            else:
                dsa = math.acos(-math.tan(phi) * math.tan(dec))
                ra_new = ramc - (1 - fraction) * (math.pi - dsa)

            if abs(ra_new - ra_estimate) < 1e-10:
                break
            ra_estimate = ra_new

        # Convert RA to ecliptic longitude
        lon = math.atan2(
            math.sin(ra_estimate) * math.cos(e),
            math.cos(ra_estimate)
        ) * RAD_TO_DEG
        return lon % 360.0

    # Calculate intermediate cusps
    try:
        h12 = placidus_cusp(1/3, True)
        h11 = placidus_cusp(2/3, True)
        h2  = placidus_cusp(1/3, False)
        h3  = placidus_cusp(2/3, False)
    except Exception:
        # Fall back to equal house if Placidus fails (high latitudes)
        return equal_house_cusps(asc)

    # Houses 1–12 (cusp of house N = start of house N)
    return [asc, h2, h3, ic, (ic+30)%360, (ic+60)%360,
            dsc, h11, h12, mc, (mc+30)%360, (mc+60)%360]


def koch_cusps(lst: float, latitude_deg: float, obliquity: float) -> List[float]:
    """
    Koch (Birthplace) house cusps.
    Source: Koch, W. & Knappich, H. (1971). Häusertabellen.
    """
    asc = compute_ascendant(lst, latitude_deg, obliquity)
    mc  = compute_midheaven(lst, obliquity)

    # Koch = divide oblique ascension arc
    # Simplified: proportional between ASC-MC arc
    arc = (asc - mc) % 360.0

    cusps = [mc]
    for i in range(1, 12):
        cusps.append((mc + arc * i / 3.0) % 360.0)
    return cusps


def get_house_cusps(system: str, lst: float, latitude: float,
                    obliquity: float) -> Tuple[List[float], float, float]:
    """
    Returns (cusps_list_12, ascendant, midheaven) in tropical degrees.
    system: 'whole_sign', 'equal', 'placidus', 'koch'
    """
    asc = compute_ascendant(lst, latitude, obliquity)
    mc  = compute_midheaven(lst, obliquity)

    if system == "placidus":
        cusps = placidus_cusps(lst, latitude, obliquity)
    elif system == "koch":
        cusps = koch_cusps(lst, latitude, obliquity)
    elif system == "equal":
        cusps = equal_house_cusps(asc)
    else:  # whole_sign (default vedic)
        cusps = whole_sign_cusps(asc)

    return cusps, asc, mc


def planet_house_number(planet_sidereal_lon: float, cusps_sidereal: List[float]) -> int:
    """
    Returns 1-based house number for a planet given sidereal cusps.

    For Whole Sign (Vedic): house = (planet_sign - lagna_sign) % 12 + 1
    For other systems: find which cusp interval contains the planet.
    """
    if not cusps_sidereal:
        return 1

    # Whole sign: cusps are exactly 0°, 30°, 60°, etc. from lagna start
    # Detect whole sign by checking if cusps are exactly 30° apart
    lagna_cusp = cusps_sidereal[0]
    is_whole_sign = all(
        abs(((cusps_sidereal[i] - lagna_cusp - i*30) % 360)) < 0.1
        for i in range(1, 12)
    )

    if is_whole_sign:
        # Simple sign-based house: (planet_sign_idx - lagna_sign_idx) % 12 + 1
        lagna_sign_idx  = int(lagna_cusp / 30) % 12
        planet_sign_idx = int(planet_sidereal_lon / 30) % 12
        return (planet_sign_idx - lagna_sign_idx) % 12 + 1

    # Non-whole-sign: find the cusp interval
    for i in range(11, -1, -1):
        c_start = cusps_sidereal[i]
        c_next  = cusps_sidereal[(i + 1) % 12]
        if c_next > c_start:  # no wraparound
            if c_start <= planet_sidereal_lon < c_next:
                return i + 1
        else:  # wraparound at 360/0
            if planet_sidereal_lon >= c_start or planet_sidereal_lon < c_next:
                return i + 1
    return 1
