"""
varshphal_tool.py  --  Varshphal & Predictions API tools
=========================================================
Wraps the core varshphal and predictions modules for FastAPI endpoints.

Endpoints to add to main.py:
    POST /api/varshphal       -- Annual chart for a target year
    POST /api/predictions     -- Personalized predictions from natal chart + transits
    GET  /api/transits        -- Current planetary positions (live)
"""

from datetime import datetime
from typing import Optional
from ..core.varshphal import generate_varshphal
from ..core.predictions import generate_full_predictions, get_today_transits
from .kundali import generate_kundali


def get_varshphal(
    # Birth details (same as kundali)
    year: int, month: int, day: int,
    hour: int, minute: int, second: int,
    timezone_offset: float,
    latitude: float,
    longitude: float,
    ayanamsa: str = "lahiri",
    # Annual chart target
    target_year: Optional[int] = None,
) -> dict:
    """
    Generate a complete Varshphal (Solar Return Annual Chart).

    Steps:
    1. Compute natal chart (birth chart)
    2. Find exact Solar Return moment for target_year
    3. Cast annual chart at SR moment
    4. Compute Muntha, Varshesh, Tajika Yogas, Sahams, Mudda Dasha
    5. Generate life-domain predictions
    """
    if target_year is None:
        target_year = datetime.now().year

    # Step 1: Natal chart
    natal = generate_kundali(
        year=year, month=month, day=day,
        hour=hour, minute=minute, second=second,
        timezone_offset=timezone_offset,
        latitude=latitude, longitude=longitude,
        house_system="whole_sign",
        ayanamsa=ayanamsa,
    )

    # Step 2-5: Varshphal
    varshphal = generate_varshphal(
        natal_chart=natal,
        target_year=target_year,
        birth_lat=latitude,
        birth_lon=longitude,
        birth_year=year,
        ayanamsa=ayanamsa,
        today=datetime.now(),
    )

    return {
        "natal_summary": {
            "lagna": natal["lagna"]["sign"],
            "moon_sign": natal["moon_sign"],
            "moon_nakshatra": natal["moon_nakshatra"],
            "current_dasha": natal["dasha"]["current"],
        },
        "varshphal": varshphal,
    }


def get_predictions(
    year: int, month: int, day: int,
    hour: int, minute: int, second: int,
    timezone_offset: float,
    latitude: float,
    longitude: float,
    ayanamsa: str = "lahiri",
) -> dict:
    """
    Generate comprehensive personalized predictions.
    Combines:
    - Natal chart analysis (yogas, planetary strength)
    - Current Vimshottari Dasha
    - Live planetary transits
    - Vedic Gochara (transit effects from Moon and Lagna)
    - Remedies
    """
    # Natal chart
    natal = generate_kundali(
        year=year, month=month, day=day,
        hour=hour, minute=minute, second=second,
        timezone_offset=timezone_offset,
        latitude=latitude, longitude=longitude,
        house_system="whole_sign",
        ayanamsa=ayanamsa,
    )

    # Current transits
    current_transits = get_today_transits(ayanamsa)

    # Full predictions
    predictions = generate_full_predictions(
        natal_chart=natal,
        current_transits=current_transits,
        today=datetime.now(),
        include_yogas=True,
    )

    return {
        "natal_summary": {
            "lagna": natal["lagna"]["sign"],
            "lagna_degree": natal["lagna"]["degree_formatted"],
            "moon_sign": natal["moon_sign"],
            "moon_nakshatra": natal["moon_nakshatra"],
            "current_dasha": natal["dasha"]["current"],
        },
        "current_transits": current_transits,
        "predictions": predictions,
    }
