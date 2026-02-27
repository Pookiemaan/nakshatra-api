"""
dasha.py
========
Vimshottari Dasha calculation system.

Vimshottari ("120 years") is the most widely used dasha system in Vedic astrology.
The dasha ruler and starting point are determined by the Moon's nakshatra at birth.

Dasha sequence: Ketu (7) → Venus (20) → Sun (6) → Moon (10) → Mars (7)
                → Rahu (18) → Jupiter (16) → Saturn (19) → Mercury (17)
Total = 120 years

Source: Parashara, B.V. "Brihat Parashara Hora Shastra" (classical text)
Algorithm: Standard Vimshottari computation as implemented in reference software.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Dasha periods in years (Vimshottari = 120 year cycle)
DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars",
               "Rahu", "Jupiter", "Saturn", "Mercury"]

DASHA_YEARS = {
    "Ketu":    7,
    "Venus":   20,
    "Sun":     6,
    "Moon":    10,
    "Mars":    7,
    "Rahu":    18,
    "Jupiter": 16,
    "Saturn":  19,
    "Mercury": 17,
}

TOTAL_YEARS = 120.0  # sum of all dasha periods

# Nakshatra → dasha lord mapping (27 nakshatras, cycle of 9 lords × 3)
NAKSHATRA_LORDS = [
    "Ketu",    # 0  Ashwini
    "Venus",   # 1  Bharani
    "Sun",     # 2  Krittika
    "Moon",    # 3  Rohini
    "Mars",    # 4  Mrigashira
    "Rahu",    # 5  Ardra
    "Jupiter", # 6  Punarvasu
    "Saturn",  # 7  Pushya
    "Mercury", # 8  Ashlesha
    "Ketu",    # 9  Magha
    "Venus",   # 10 Purva Phalguni
    "Sun",     # 11 Uttara Phalguni
    "Moon",    # 12 Hasta
    "Mars",    # 13 Chitra
    "Rahu",    # 14 Swati
    "Jupiter", # 15 Vishakha
    "Saturn",  # 16 Anuradha
    "Mercury", # 17 Jyeshtha
    "Ketu",    # 18 Mula
    "Venus",   # 19 Purva Ashadha
    "Sun",     # 20 Uttara Ashadha
    "Moon",    # 21 Shravana
    "Mars",    # 22 Dhanishtha
    "Rahu",    # 23 Shatabhisha
    "Jupiter", # 24 Purva Bhadrapada
    "Saturn",  # 25 Uttara Bhadrapada
    "Mercury", # 26 Revati
]

DAYS_PER_YEAR = 365.25


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def years_to_days(years: float) -> float:
    return years * DAYS_PER_YEAR


def _dasha_sequence_from(lord: str) -> List[str]:
    """Return dasha sequence starting from given lord."""
    idx = DASHA_LORDS.index(lord)
    return DASHA_LORDS[idx:] + DASHA_LORDS[:idx]


# ---------------------------------------------------------------------------
# Core Vimshottari calculation
# ---------------------------------------------------------------------------

def compute_vimshottari_dasha(moon_sidereal_lon: float, birth_dt: datetime) -> List[dict]:
    """
    Compute Vimshottari Maha Dasha periods from birth.

    Args:
        moon_sidereal_lon: Moon's sidereal longitude in degrees (0–360)
        birth_dt: Birth datetime (timezone-aware or naive UTC assumed)

    Returns:
        List of dasha periods with start/end dates and antardasha breakdowns.
    """
    # Determine nakshatra
    nakshatra_span = 360.0 / 27.0       # 13.333... degrees per nakshatra
    nakshatra_idx = int(moon_sidereal_lon / nakshatra_span) % 27
    elapsed_in_nakshatra = (moon_sidereal_lon % nakshatra_span) / nakshatra_span

    # Starting dasha lord
    starting_lord = NAKSHATRA_LORDS[nakshatra_idx]
    dasha_years_for_lord = DASHA_YEARS[starting_lord]

    # Balance of first dasha remaining at birth
    balance_fraction = 1.0 - elapsed_in_nakshatra
    balance_years = dasha_years_for_lord * balance_fraction
    balance_days  = years_to_days(balance_years)

    # Build dasha list
    sequence = _dasha_sequence_from(starting_lord)
    periods = []

    current_start = birth_dt
    for i, lord in enumerate(sequence):
        if i == 0:
            duration_days = balance_days
        else:
            duration_days = years_to_days(DASHA_YEARS[lord])

        current_end = current_start + timedelta(days=duration_days)

        # Compute antardashas (sub-periods within each maha dasha)
        antardashas = _compute_antardasha(lord, current_start, duration_days)

        periods.append({
            "lord": lord,
            "start": current_start.strftime("%Y-%m-%d"),
            "end":   current_end.strftime("%Y-%m-%d"),
            "duration_years": round(duration_days / DAYS_PER_YEAR, 2),
            "antardashas": antardashas,
        })

        current_start = current_end

    return periods


def _compute_antardasha(maha_lord: str, start_dt: datetime,
                        total_days: float) -> List[dict]:
    """
    Compute Antardasha (Bhukti) periods within a Maha Dasha.
    Antardasha proportions: each sub-period proportional to the sub-lord's
    dasha years relative to 120 total years.
    Sequence starts from the maha dasha lord itself.
    """
    sequence = _dasha_sequence_from(maha_lord)
    antardashas = []
    current_start = start_dt

    for sub_lord in sequence:
        proportion = DASHA_YEARS[sub_lord] / TOTAL_YEARS
        sub_days = total_days * proportion
        current_end = current_start + timedelta(days=sub_days)

        antardashas.append({
            "lord": sub_lord,
            "start": current_start.strftime("%Y-%m-%d"),
            "end":   current_end.strftime("%Y-%m-%d"),
            "duration_days": round(sub_days, 1),
        })
        current_start = current_end

    return antardashas


def get_current_dasha(dasha_periods: List[dict], on_date: datetime) -> dict:
    """
    Return the active maha dasha and antardasha for a given date.
    """
    date_str = on_date.strftime("%Y-%m-%d")

    for period in dasha_periods:
        if period["start"] <= date_str <= period["end"]:
            # Find antardasha
            for antardasha in period.get("antardashas", []):
                if antardasha["start"] <= date_str <= antardasha["end"]:
                    return {
                        "maha_dasha": period["lord"],
                        "maha_dasha_start": period["start"],
                        "maha_dasha_end": period["end"],
                        "antardasha": antardasha["lord"],
                        "antardasha_start": antardasha["start"],
                        "antardasha_end": antardasha["end"],
                    }
            return {
                "maha_dasha": period["lord"],
                "maha_dasha_start": period["start"],
                "maha_dasha_end": period["end"],
                "antardasha": None,
            }

    return {"maha_dasha": None, "antardasha": None}
