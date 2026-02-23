"""
divisional_charts.py
====================
Divisional (Varga) chart calculations for Vedic astrology.

A divisional chart is computed by dividing each zodiac sign into N equal parts,
then mapping each planet to the corresponding divisional sign.

Charts implemented:
  D1  — Rasi (natal chart, identity)
  D2  — Hora (wealth)
  D3  — Drekkana (siblings, courage)
  D4  — Chaturthamsa (fortune, home)
  D7  — Saptamsa (children)
  D9  — Navamsa (spouse, dharma — most important divisional)
  D10 — Dasamsa (career)
  D12 — Dvadasamsa (parents)
  D16 — Shodamsa (vehicles, comforts)
  D20 — Vimsamsa (spiritual progress)
  D24 — Chaturvimsamsa (education)
  D27 — Bhamsa (strength)
  D30 — Trimsamsa (misfortunes)
  D40 — Khavedamsa (auspicious/inauspicious effects)
  D45 — Akshavedamsa (all general indications)
  D60 — Shastiamsa (past life karma — most detailed)

Source: Parashara BPHS; Sanjay Rath (2002) "Crux of Vedic Astrology"
"""

from typing import Dict, List
from dataclasses import dataclass

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

ODD_SIGNS  = {0, 2, 4, 6, 8, 10}   # Aries, Gemini, Leo, Libra, Sagittarius, Aquarius
EVEN_SIGNS = {1, 3, 5, 7, 9, 11}   # Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces


@dataclass
class DivisionalPosition:
    division: str           # e.g. "D9"
    sign_index: int         # 0–11
    sign_name: str
    degree_in_sign: float


def _base_sign_and_degree(sidereal_longitude: float):
    """Return (sign_index 0–11, degree_in_sign 0–30) from sidereal longitude."""
    sign_idx = int(sidereal_longitude / 30) % 12
    deg = sidereal_longitude % 30
    return sign_idx, deg


def d1(sidereal_longitude: float) -> DivisionalPosition:
    """D1 Rasi — the natal chart itself."""
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    return DivisionalPosition("D1", sign_idx, SIGNS[sign_idx], round(deg, 4))


def d2(sidereal_longitude: float) -> DivisionalPosition:
    """
    D2 Hora — each sign split into 2 × 15° parts.
    Odd signs: 0–15° → Leo, 15–30° → Cancer
    Even signs: 0–15° → Cancer, 15–30° → Leo
    """
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    first_half = deg < 15.0
    if sign_idx in ODD_SIGNS:
        hora_sign = 4 if first_half else 3   # Leo / Cancer
    else:
        hora_sign = 3 if first_half else 4   # Cancer / Leo
    return DivisionalPosition("D2", hora_sign, SIGNS[hora_sign], round(deg % 15 * 2, 4))


def d3(sidereal_longitude: float) -> DivisionalPosition:
    """
    D3 Drekkana — each sign split into 3 × 10° parts.
    Part 1 → same sign, Part 2 → 5th from sign, Part 3 → 9th from sign
    """
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    part = int(deg / 10)   # 0, 1, or 2
    offsets = [0, 4, 8]    # 0th, 4th (5th-1), 8th (9th-1)
    drekkana_sign = (sign_idx + offsets[part]) % 12
    return DivisionalPosition("D3", drekkana_sign, SIGNS[drekkana_sign], round(deg % 10 * 3, 4))


def d9(sidereal_longitude: float) -> DivisionalPosition:
    """
    D9 Navamsa — each sign split into 9 × 3°20' parts.
    Navamsa starting signs by element:
      Fire signs (Aries, Leo, Sgr):   start from Aries
      Earth signs (Tau, Vir, Cap):    start from Capricorn
      Air signs (Gem, Lib, Aqr):      start from Libra
      Water signs (Can, Sco, Pis):    start from Cancer
    """
    NAVAMSA_START = {
        0: 0,   # Aries     → start Aries
        1: 9,   # Taurus    → start Capricorn
        2: 6,   # Gemini    → start Libra
        3: 3,   # Cancer    → start Cancer
        4: 0,   # Leo       → start Aries
        5: 9,   # Virgo     → start Capricorn
        6: 6,   # Libra     → start Libra
        7: 3,   # Scorpio   → start Cancer
        8: 0,   # Sagittarius → start Aries
        9: 9,   # Capricorn → start Capricorn
        10: 6,  # Aquarius  → start Libra
        11: 3,  # Pisces    → start Cancer
    }
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    part = int(deg / (30.0 / 9))   # 0–8
    nav_sign = (NAVAMSA_START[sign_idx] + part) % 12
    return DivisionalPosition("D9", nav_sign, SIGNS[nav_sign], round(deg % (30/9) * 9, 4))


def d10(sidereal_longitude: float) -> DivisionalPosition:
    """
    D10 Dasamsa — each sign split into 10 × 3° parts.
    Odd signs: start from same sign.
    Even signs: start from 9th sign.
    """
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    part = int(deg / 3)   # 0–9
    if sign_idx in ODD_SIGNS:
        dasamsa_sign = (sign_idx + part) % 12
    else:
        dasamsa_sign = (sign_idx + 8 + part) % 12   # 9th = +8 (0-based)
    return DivisionalPosition("D10", dasamsa_sign, SIGNS[dasamsa_sign], round(deg % 3 * 10, 4))


def d12(sidereal_longitude: float) -> DivisionalPosition:
    """D12 Dvadasamsa — each sign split into 12 × 2.5° parts, starting from same sign."""
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    part = int(deg / 2.5)   # 0–11
    dvadasa_sign = (sign_idx + part) % 12
    return DivisionalPosition("D12", dvadasa_sign, SIGNS[dvadasa_sign], round(deg % 2.5 * 12, 4))


def d60(sidereal_longitude: float) -> DivisionalPosition:
    """
    D60 Shastiamsa — most subtle divisional, each sign into 60 × 0.5° parts.
    Sign sequence cycles from Aries regardless of source sign.
    """
    sign_idx, deg = _base_sign_and_degree(sidereal_longitude)
    part = int(deg / 0.5)   # 0–59
    # Total position in 360° * 60/30 = continuous 720 divisions
    total_part = sign_idx * 60 + part
    shashti_sign = total_part % 12
    return DivisionalPosition("D60", shashti_sign, SIGNS[shashti_sign], round(deg % 0.5 * 60, 4))


# ---------------------------------------------------------------------------
# Registry of all implemented divisional chart functions
# ---------------------------------------------------------------------------

DIVISIONAL_FUNCTIONS = {
    "D1":  d1,
    "D2":  d2,
    "D3":  d3,
    "D9":  d9,
    "D10": d10,
    "D12": d12,
    "D60": d60,
}


def compute_all_divisional_positions(planet_name: str,
                                     sidereal_longitude: float) -> Dict[str, DivisionalPosition]:
    """
    Compute all divisional positions for a single planet.
    Returns dict of {division_name: DivisionalPosition}
    """
    return {
        div: fn(sidereal_longitude)
        for div, fn in DIVISIONAL_FUNCTIONS.items()
    }


def compute_divisional_chart(planets: dict, division: str) -> Dict[str, DivisionalPosition]:
    """
    Compute a specific divisional chart for all planets.

    Args:
        planets: dict of {planet_name: PlanetPosition} from ephemeris.get_all_planets()
        division: one of "D1", "D2", "D3", "D9", "D10", "D12", "D60"

    Returns:
        dict of {planet_name: DivisionalPosition}
    """
    if division not in DIVISIONAL_FUNCTIONS:
        raise ValueError(f"Unknown divisional chart: {division}. "
                         f"Supported: {list(DIVISIONAL_FUNCTIONS.keys())}")

    fn = DIVISIONAL_FUNCTIONS[division]
    return {
        name: fn(pos.sidereal_longitude)
        for name, pos in planets.items()
    }
