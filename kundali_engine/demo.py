"""
demo.py
=======
Demonstration of the Kundali Engine.
Run: python demo.py

Generates a full birth chart for a sample birth and prints a formatted report.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from kundali_engine import generate_kundali, generate_kundali_unknown_time


def print_section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def format_planet_table(planets: dict) -> str:
    lines = [f"{'Planet':<12} {'Sign':<14} {'Degree':<12} {'Nakshatra':<22} {'Pada':<5} {'House':<6}"]
    lines.append("─" * 75)
    for name, p in planets.items():
        retro = " ℞" if p.get("is_retrograde") else "  "
        lines.append(
            f"{name:<12} {p['sign']:<14} {p['degree_formatted']:<12} "
            f"{p['nakshatra']:<22} {p['nakshatra_pada']:<5} H{p['house']}"
            f"{retro}"
        )
    return "\n".join(lines)


def run_demo():
    print("=" * 60)
    print("   KUNDALI ENGINE — SAMPLE BIRTH CHART")
    print("=" * 60)

    # ── Sample birth data ──
    params = {
        "year": 1990, "month": 6, "day": 15,
        "hour": 10, "minute": 30, "second": 0,
        "timezone_offset": 5.5,        # IST
        "latitude": 28.6139,           # Delhi
        "longitude": 77.2090,
        "house_system": "whole_sign",
        "ayanamsa": "lahiri",
    }

    print(f"\n  Birth Date  : {params['year']}-{params['month']:02d}-{params['day']:02d}")
    print(f"  Birth Time  : {params['hour']:02d}:{params['minute']:02d} IST (UTC+5:30)")
    print(f"  Location    : Delhi, India ({params['latitude']}°N, {params['longitude']}°E)")
    print(f"  House System: {params['house_system'].replace('_', ' ').title()}")
    print(f"  Ayanamsa    : {params['ayanamsa'].title()} ({params['ayanamsa'].upper()})")

    chart = generate_kundali(**params)
    meta  = chart["meta"]

    print_section("LAGNA (ASCENDANT)")
    lagna = chart["lagna"]
    print(f"  Sign        : {lagna['sign']}")
    print(f"  Degree      : {lagna['degree_formatted']}")
    print(f"  Nakshatra   : {lagna['nakshatra']} (Pada {lagna['nakshatra_pada']})")
    mc = chart["midheaven"]
    print(f"  Midheaven   : {mc['sign']} {mc['degree_formatted']}")

    print_section("RASI CHART — PLANET POSITIONS")
    print(format_planet_table(chart["planets"]))

    print_section("MOON SIGN & NAKSHATRA")
    print(f"  Rasi (Sign)   : {chart['moon_sign']}")
    print(f"  Nakshatra     : {chart['moon_nakshatra']} (Pada {chart['moon_nakshatra_pada']})")

    print_section("PANCHANG")
    p = chart["panchang"]
    print(f"  Vara (Day)    : {p['vara']}")
    print(f"  Tithi         : {p['tithi']['name']} ({p['tithi']['paksha']} Paksha)"
          f"  — {p['tithi']['elapsed_pct']}% elapsed")
    print(f"  Nakshatra     : {p['nakshatra']['name']} (Pada {p['nakshatra']['pada']})"
          f"  — {p['nakshatra']['elapsed_pct']}% elapsed")
    print(f"  Yoga          : {p['yoga']['name']}")
    print(f"  Karana        : {p['karana']['name']}")
    print(f"  Sunrise (UTC) : {p.get('sunrise', 'N/A')}")
    print(f"  Sunset (UTC)  : {p.get('sunset', 'N/A')}")
    rk = p.get("rahu_kala", {})
    print(f"  Rahu Kala     : {rk.get('start', '?')} — {rk.get('end', '?')}")

    print_section("VIMSHOTTARI DASHA")
    dasha = chart["dasha"]
    cur = dasha.get("current", {})
    if cur and cur.get("maha_dasha"):
        print(f"  Current Maha Dasha : {cur['maha_dasha']}  ({cur['maha_dasha_start']} → {cur['maha_dasha_end']})")
        if cur.get("antardasha"):
            print(f"  Antardasha (Bhukti): {cur['antardasha']}  ({cur['antardasha_start']} → {cur['antardasha_end']})")
    else:
        print("  (Dasha date outside calculation range for demo)")

    print("\n  Full Vimshottari Sequence:")
    print(f"  {'Lord':<10} {'Start':<14} {'End':<14} {'Years':<8}")
    print(f"  {'─'*10} {'─'*14} {'─'*14} {'─'*8}")
    for period in dasha["all_periods"]:
        print(f"  {period['lord']:<10} {period['start']:<14} {period['end']:<14} {period['duration_years']:<8.2f}")

    print_section("DIVISIONAL CHARTS")
    for div_name, div_data in chart["divisional_charts"].items():
        print(f"\n  {div_name} Chart:")
        print(f"  {'Planet':<12} {'Sign':<16} {'Degree':<8}")
        print(f"  {'─'*12} {'─'*16} {'─'*8}")
        for planet, pos in div_data.items():
            print(f"  {planet:<12} {pos['sign']:<16} {pos['degree']:.2f}°")

    print_section("HOUSE CUSPS")
    print(f"  {'House':<8} {'Sign':<16} {'Degree':<14}")
    print(f"  {'─'*8} {'─'*16} {'─'*14}")
    for h in chart["houses"]:
        print(f"  H{h['house']:<7} {h['sign']:<16} {h['degree_formatted']}")

    print_section("TECHNICAL METADATA")
    print(f"  Julian Day    : {meta['julian_day']}")
    print(f"  T (centuries) : {meta['julian_centuries_j2000']}")
    print(f"  Obliquity     : {meta['obliquity']:.6f}°")
    print(f"  LST (degrees) : {meta['lst_degrees']:.6f}°")

    print("\n" + "=" * 60)
    print("  UNKNOWN BIRTH TIME DEMO (3-variant chart)")
    print("=" * 60)

    unknown_chart = generate_kundali_unknown_time(
        year=1975, month=4, day=1,
        latitude=13.0827, longitude=80.2707,
        timezone_offset=5.5,
        ayanamsa="lahiri"
    )
    print(f"\n  {unknown_chart['note']}")
    for variant_name, vc in unknown_chart["variants"].items():
        lagna = vc["lagna"]["sign"]
        moon  = vc["moon_sign"]
        print(f"\n  [{variant_name.upper():^8}]  Lagna: {lagna:<14}  Moon: {moon}")

    print("\n")


if __name__ == "__main__":
    run_demo()
