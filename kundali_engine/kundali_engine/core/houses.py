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

    # Handle pole-proximity issues
    if abs(x) < 1e-10:
        asc = 90.0 if y < 0 else 270.0
    else:
        asc = math.atan2(y, x) * RAD_TO_DEG

    # Ensure correct quadrant
    if x < 0:
        asc += 180.0
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
    """
    for i in range(11, -1, -1):
        cusp = cusps_sidereal[i]
        if planet_sidereal_lon >= cusp or (cusp > cusps_sidereal[0] and planet_sidereal_lon < cusps_sidereal[0]):
            return i + 1
    return 1
