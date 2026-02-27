"""
Kundali Engine
==============
A production-ready Vedic astrology calculation engine.

Quick start:
    from kundali_engine import generate_kundali

    chart = generate_kundali(
        year=1990, month=6, day=15,
        hour=10, minute=30, second=0,
        timezone_offset=5.5,
        latitude=28.6139,
        longitude=77.2090,
    )
"""

from .tools.kundali import generate_kundali, generate_kundali_unknown_time

__version__ = "1.0.0"
__all__ = ["generate_kundali", "generate_kundali_unknown_time"]
