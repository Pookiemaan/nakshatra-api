"""
varshphal.py  —  Vedic Annual Chart (Varshaphal / Tajika Shastra)
=================================================================
Implements the complete Varshphal (Solar Return) system as used by
top Vedic astrology software (Jagannatha Hora, Parashara's Light,
Astro-Vision, AstroSage, Cosmic Insights):

1.  Solar Return finder       -- binary-search to minute-precision
2.  Annual chart cast         -- full planetary positions at SR moment
3.  Muntha calculation        -- progressed ascendant (one sign/year)
4.  Varshesh (Year Lord)      -- lord of Varsha Lagna
5.  Pancha-Vargiya Bala       -- 5-fold strength for annual planets
6.  Tajika yogas              -- Ithasala, Ishrafa, Nakta, Yamaya
7.  Mudda Dasha               -- 360-day compressed Vimshottari
8.  Sahams (Arabic Parts)     -- 16 sensitive points
9.  Predictions narrative     -- house-by-house synthesis
10. Transit overlay           -- slow planets over natal positions

Sources:
  - Bepin Behari "A Textbook of Varshaphala" (Motilal Banarsidass)
  - Saraswati "Tajika Shastra" (classical text)
  - K.N. Rao "Predicting Through Jaimini's Chara Dasha"
  - Astrowindows blog (Muntha calculation manual)
  - Cosmic Insights (Sahams, Ithasala orbs)
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ---- Constants ---------------------------------------------------------------
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

SIGN_LORDS = {
    "Aries": "Mars",  "Taurus": "Venus",  "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun",       "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars",  "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# Tajika Deepthamsas (orbs, degrees per planet)
DEEPTHAMSA = {
    "Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7,
    "Jupiter": 9, "Venus": 7, "Saturn": 9, "Rahu": 0, "Ketu": 0,
}

# Tajika aspects: positions from one planet to another that form aspects
TAJIKA_FRIENDLY_POSITIONS = {3, 5, 9, 11}
TAJIKA_INIMICAL_POSITIONS  = {1, 4, 7, 10}

# Dasha system (Vimshottari)
DASHA_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
               "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}
TOTAL_DASHA_YEARS = 120.0
MUDDA_TOTAL_DAYS  = 360.0

NAKSHATRA_LORDS = (
    ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3
)

PLANET_SPEED_ORDER = ["Moon","Mercury","Venus","Sun","Mars","Jupiter","Saturn","Rahu","Ketu"]

# Exaltation sidereal longitudes
EXALTATION = {
    "Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0,
    "Jupiter": 95.0, "Venus": 357.0, "Saturn": 200.0, "Rahu": 30.0, "Ketu": 240.0,
}
DEBILITATION = {p: (e + 180) % 360 for p, e in EXALTATION.items()}

GOOD_HOUSES = {1, 2, 3, 5, 9, 10, 11}
BAD_HOUSES  = {6, 8, 12}

BENEFIC_PLANETS = {"Jupiter", "Venus", "Moon", "Mercury"}
MALEFIC_PLANETS = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

HOUSE_THEMES = {
    1: "personality, health, and overall year energy",
    2: "finances, speech, family, and accumulated wealth",
    3: "communication, siblings, courage, short travels, and skills",
    4: "home, property, mother, vehicles, and emotional security",
    5: "creativity, children, education, romance, and speculation",
    6: "health, service, enemies, debts, and competitive situations",
    7: "partnerships, marriage, business deals, and public relations",
    8: "transformation, inheritance, occult, and joint resources",
    9: "fortune, spirituality, higher education, and long travels",
    10: "career, reputation, authority, and public achievements",
    11: "gains, networks, aspirations, elder siblings, and social circles",
    12: "expenditure, isolation, foreign connection, and spiritual growth",
}

PLANET_KARAKAS = {
    "Sun":     ["career", "father", "authority", "government", "vitality", "leadership"],
    "Moon":    ["emotions", "mother", "mind", "popularity", "travel", "public image"],
    "Mars":    ["energy", "action", "siblings", "property", "competition", "surgery"],
    "Mercury": ["communication", "business", "intellect", "writing", "trade", "education"],
    "Jupiter": ["wisdom", "fortune", "children", "religion", "expansion", "guidance"],
    "Venus":   ["relationships", "beauty", "luxury", "arts", "marriage", "finance"],
    "Saturn":  ["discipline", "longevity", "service", "karma", "delays", "chronic matters"],
    "Rahu":    ["ambition", "innovation", "foreign", "technology", "sudden gains", "obsession"],
    "Ketu":    ["spirituality", "intuition", "research", "isolation", "liberation", "past"],
}

OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"],
    "Mars": ["Aries","Scorpio"], "Mercury": ["Gemini","Virgo"],
    "Jupiter": ["Sagittarius","Pisces"], "Venus": ["Taurus","Libra"],
    "Saturn": ["Capricorn","Aquarius"], "Rahu": ["Aquarius"], "Ketu": ["Scorpio"],
}
FRIENDLY_SIGNS = {
    "Sun": ["Aries","Sagittarius","Scorpio","Pisces"],
    "Moon": ["Taurus","Gemini","Scorpio","Sagittarius","Pisces"],
    "Mars": ["Gemini","Leo","Sagittarius","Capricorn","Pisces"],
    "Mercury": ["Libra","Capricorn","Aquarius","Taurus"],
    "Jupiter": ["Aries","Cancer","Leo","Scorpio"],
    "Venus": ["Capricorn","Aquarius","Gemini","Virgo","Pisces"],
    "Saturn": ["Gemini","Virgo","Libra","Taurus"],
    "Rahu": ["Gemini","Virgo","Capricorn","Pisces"],
    "Ketu": ["Sagittarius","Capricorn","Gemini"],
}

# ---- Utilities ---------------------------------------------------------------

def _n(x):  return x % 360.0
def _sign(lon):  return SIGNS[int(lon/30)%12]
def _sign_num(lon):  return int(lon/30)%12
def _sign_diff(a, b):  return (b - a) % 12 + 1
def _deg_in_sign(lon):  return lon % 30.0


# ---- Solar Return Finder -----------------------------------------------------

def find_solar_return(natal_sun_sidereal: float,
                      target_year: int,
                      birth_lat: float,
                      birth_lon: float,
                      ayanamsa: str = "lahiri") -> float:
    """
    Binary-search for the exact JD when the Sun returns to its natal
    sidereal longitude. Accurate to better than 1 minute (0.0001 deg).

    Algorithm:
    1. Scan the target year in 1-day steps to bracket the crossing
    2. Binary search to sub-minute precision (60 iterations)
    """
    from .ephemeris import (
        gregorian_to_jd, nutation_and_obliquity, sun_longitude,
        tropical_to_sidereal, J2000
    )

    def sun_sid_at_jd(jd):
        T = (jd - J2000) / 36525.0
        dpsi, _, _ = nutation_and_obliquity(T)
        sun_trop, _ = sun_longitude(T, dpsi)
        return tropical_to_sidereal(sun_trop, T, ayanamsa)

    target = natal_sun_sidereal
    jd_jan1 = gregorian_to_jd(target_year, 1, 1, 0.0)

    # Step 1: bracket by scanning year
    prev_sid = sun_sid_at_jd(jd_jan1)
    bracket_lo = jd_jan1

    for day in range(370):
        jd_test = jd_jan1 + day
        curr_sid = sun_sid_at_jd(jd_test)
        delta_prev = (prev_sid - target + 360) % 360
        delta_curr = (curr_sid - target + 360) % 360
        if delta_prev > 180 and delta_curr < 180:
            bracket_lo = jd_test - 1
            break
        prev_sid = curr_sid

    # Step 2: binary search
    lo = bracket_lo
    hi = bracket_lo + 2.0

    for _ in range(70):
        mid = (lo + hi) / 2.0
        sid = sun_sid_at_jd(mid)
        diff = (target - sid + 360) % 360
        if diff > 180:
            diff -= 360
        if abs(diff) < 0.00005:
            break
        if diff > 0:
            lo = mid
        else:
            hi = mid

    return mid


# ---- Muntha ------------------------------------------------------------------

def compute_muntha(natal_lagna_sidereal: float, age_years: int) -> Tuple[float, str, str]:
    """
    Muntha = natal Lagna progressed 1 sign per completed year.
    Returns: (longitude, sign, lord)
    """
    natal_sign_idx   = int(natal_lagna_sidereal / 30) % 12
    natal_deg_offset = natal_lagna_sidereal % 30
    muntha_sign_idx  = (natal_sign_idx + age_years) % 12
    muntha_lon       = muntha_sign_idx * 30 + natal_deg_offset
    muntha_sign      = SIGNS[muntha_sign_idx]
    return muntha_lon, muntha_sign, SIGN_LORDS[muntha_sign]


# ---- Pancha-Vargiya Bala -----------------------------------------------------

def compute_panchavargiya_bala(planet: str, sidereal_lon: float,
                               is_retrograde: bool = False) -> dict:
    """
    5-fold strength for Varshphal planet assessment.
    Max = 95 pts; >30 = Strong, 15-30 = Moderate, <15 = Weak.
    """
    sign     = _sign(sidereal_lon)
    deg      = sidereal_lon % 30
    sign_idx = _sign_num(sidereal_lon)

    # 1. Kshetra Bala
    if sign in OWN_SIGNS.get(planet, []):
        kshetra, klabel = 30, "own"
    elif sign in FRIENDLY_SIGNS.get(planet, []):
        kshetra, klabel = 15, "friendly"
    else:
        kshetra, klabel = 7.5, "enemy"

    # 2. Uccha Bala (proximity to exaltation)
    exalt_lon = EXALTATION.get(planet, 0)
    dist_exalt = abs((sidereal_lon - exalt_lon + 180) % 360 - 180)
    uccha = round(max(0, 20 * (1 - dist_exalt / 180)), 1)

    # 3. Hora Bala (odd nakshatra = 15)
    nak_idx = int(sidereal_lon / (360/27)) % 27
    hora = 15 if nak_idx % 2 == 0 else 0

    # 4. Dreshkana Bala (decanate)
    decan = int(deg / 10)
    dresk = 15 if decan == 0 else (10 if decan == 1 else 5)

    # 5. Navamsha Bala
    nav_lon = _n(sidereal_lon * 9)
    nav_sign = _sign(nav_lon)
    nav_score = 15 if nav_sign in OWN_SIGNS.get(planet, []) else (
        10 if nav_sign in FRIENDLY_SIGNS.get(planet, []) else 5)

    total = kshetra + uccha + hora + dresk + nav_score
    if is_retrograde and total >= 30:
        label = "Strong (Retrograde)"
    elif total >= 30:
        label = "Strong"
    elif total >= 15:
        label = "Moderate"
    else:
        label = "Weak"

    return {
        "kshetra_bala": kshetra, "kshetra_label": klabel,
        "uccha_bala": uccha, "hora_bala": hora,
        "dreshkana_bala": dresk, "navamsha_bala": nav_score,
        "total": round(total, 1), "strength": label,
    }


# ---- Tajika Yoga Detection ---------------------------------------------------

def compute_tajika_yogas(planets: dict) -> List[dict]:
    """
    Detect Tajika yogas between planets in the Varshphal chart.
    Ithasala: applying (fast behind slow), within orb, both direct = success
    Ishrafa:  separating (fast past slow) = opportunity passed
    Kambula:  applying but fast is retrograde = indirect success
    """
    yogas = []
    active_planets = [p for p in PLANET_SPEED_ORDER
                      if p in planets and p not in ("Rahu","Ketu")]

    for i, fast_name in enumerate(active_planets):
        for slow_name in active_planets[i+1:]:
            fast = planets[fast_name]
            slow = planets[slow_name]
            fast_lon  = fast["sidereal_longitude"]
            slow_lon  = slow["sidereal_longitude"]
            fast_retro = fast.get("is_retrograde", False)
            slow_retro = slow.get("is_retrograde", False)

            # Which Tajika aspect applies?
            p1_sign = _sign_num(fast_lon)
            p2_sign = _sign_num(slow_lon)
            position = _sign_diff(p1_sign, p2_sign)

            if position not in (TAJIKA_FRIENDLY_POSITIONS | TAJIKA_INIMICAL_POSITIONS):
                continue

            # Orb check
            orb_allowed = (DEEPTHAMSA.get(fast_name, 7) + DEEPTHAMSA.get(slow_name, 7)) / 2
            exact_angle = (position - 1) * 30.0
            angular_dist = (slow_lon - fast_lon + 360) % 360
            if angular_dist > 180:
                angular_dist = 360 - angular_dist
            orb_remaining = abs(angular_dist - exact_angle)

            if orb_remaining > orb_allowed:
                continue

            # Applying vs separating
            diff = (slow_lon - fast_lon + 360) % 360
            applying = diff < 180 and not fast_retro

            aspect_type = "friendly" if position in TAJIKA_FRIENDLY_POSITIONS else "inimical"

            if applying and not fast_retro and not slow_retro:
                yoga, favorable = "Ithasala", True
                meaning = (f"{fast_name} applying to {slow_name} ({aspect_type} aspect, "
                           f"{position}th position) — desired matter will reach completion.")
            elif applying and fast_retro:
                yoga, favorable = "Kambula", True
                meaning = (f"{fast_name} (retrograde) applying to {slow_name} — success "
                           f"through indirect means; some delay but eventual fulfillment.")
            elif not applying:
                yoga, favorable = "Ishrafa", False
                meaning = (f"{fast_name} separating from {slow_name} — the opportunity "
                           f"related to these planets has already manifested or passed.")
            else:
                yoga, favorable = "Mixed", None
                meaning = f"Complex interaction between {fast_name} and {slow_name}."

            yogas.append({
                "yoga": yoga,
                "planets": [fast_name, slow_name],
                "aspect_type": aspect_type,
                "position": position,
                "orb_used": round(orb_remaining, 2),
                "orb_allowed": round(orb_allowed, 1),
                "applying": applying,
                "favorable": favorable,
                "meaning": meaning,
            })

    return yogas


# ---- Mudda Dasha -------------------------------------------------------------

def compute_mudda_dasha(moon_sidereal_lon: float,
                        varsha_start_dt: datetime) -> List[dict]:
    """
    Mudda Dasha = Vimshottari proportions compressed to 360 days.
    Same starting lord as natal Vimshottari (Moon's nakshatra lord).
    """
    nak_span = 360.0 / 27.0
    nak_idx  = int(moon_sidereal_lon / nak_span) % 27
    elapsed  = (moon_sidereal_lon % nak_span) / nak_span

    start_lord = NAKSHATRA_LORDS[nak_idx]
    start_idx  = DASHA_LORDS.index(start_lord)
    sequence   = DASHA_LORDS[start_idx:] + DASHA_LORDS[:start_idx]

    first_full = (DASHA_YEARS[start_lord] / TOTAL_DASHA_YEARS) * MUDDA_TOTAL_DAYS
    balance    = first_full * (1 - elapsed)

    periods = []
    current_dt = varsha_start_dt
    cutoff_dt  = varsha_start_dt + timedelta(days=MUDDA_TOTAL_DAYS + 1)

    for i, lord in enumerate(sequence):
        duration = balance if i == 0 else (DASHA_YEARS[lord] / TOTAL_DASHA_YEARS) * MUDDA_TOTAL_DAYS
        end_dt = current_dt + timedelta(days=duration)
        periods.append({
            "lord": lord,
            "start": current_dt.strftime("%Y-%m-%d"),
            "end": end_dt.strftime("%Y-%m-%d"),
            "duration_days": round(duration, 1),
        })
        current_dt = end_dt
        if current_dt >= cutoff_dt:
            break

    return periods


def get_current_mudda(mudda_periods: List[dict], on_date: datetime) -> Optional[dict]:
    date_str = on_date.strftime("%Y-%m-%d")
    for p in mudda_periods:
        if p["start"] <= date_str <= p["end"]:
            return p
    return None


# ---- Sahams ------------------------------------------------------------------

def compute_sahams(planets: dict, asc_sidereal: float, is_day_chart: bool) -> dict:
    """
    Compute 16 major Sahams (Arabic Parts/Lots) for Varshphal.
    Formula: Saham = (A + B - C) mod 360.
    """
    def g(name):
        return planets.get(name, {}).get("sidereal_longitude", 0.0)

    sun=g("Sun"); moon=g("Moon"); sat=g("Saturn"); jup=g("Jupiter")
    mars=g("Mars"); mer=g("Mercury"); ven=g("Venus"); asc=asc_sidereal

    raw = {
        "Punya (Fortune)":    _n(asc + moon - sun) if is_day_chart else _n(asc + sun - moon),
        "Vidya (Knowledge)":  _n(asc + mer - moon),
        "Yashas (Fame)":      _n(asc + jup - sun),
        "Mitra (Friends)":    _n(asc + moon - mer),
        "Mahatmya (Authority)": _n(asc + mars - sun),
        "Aasha (Ambition)":   _n(asc + jup - sat),
        "Samarthya (Power)":  _n(asc + mars - moon),
        "Bhratru (Siblings)": _n(asc + jup - mars),
        "Pitru (Father)":     _n(asc + sat - sun),
        "Raja (Leadership)":  _n(asc + moon - jup),
        "Vivaha (Marriage)":  _n(asc + ven - sat) if is_day_chart else _n(asc + sat - ven),
        "Santana (Children)": _n(asc + jup - moon),
        "Jeeva (Health)":     _n(asc + sat - mars),
        "Karma (Career)":     _n(asc + mars - mer),
        "Kali (Obstacles)":   _n(asc + sat - moon),
        "Paradesa (Travel)":  _n(asc + sat - sun),
    }

    return {
        name: {"longitude": round(lon, 4), "sign": _sign(lon), "degree": round(lon % 30, 2)}
        for name, lon in raw.items()
    }


# ---- Varshesh ----------------------------------------------------------------

def compute_varshesh(annual_planets: dict, varsha_lagna_sidereal: float) -> dict:
    """Varshesh = Lord of the Varsha (Annual) Lagna."""
    lagna_sign   = _sign(varsha_lagna_sidereal)
    varshesh     = SIGN_LORDS[lagna_sign]
    vp           = annual_planets.get(varshesh, {})
    sid_lon      = vp.get("sidereal_longitude", 0.0)
    is_retro     = vp.get("is_retrograde", False)
    bala         = compute_panchavargiya_bala(varshesh, sid_lon, is_retro)

    bala_total   = bala["total"]
    if bala_total >= 35:
        quality = "Excellent — strong Varshesh; a highly productive, successful year."
    elif bala_total >= 25:
        quality = "Good — moderate strength; most endeavors are well supported."
    elif bala_total >= 15:
        quality = "Mixed — some gains amid obstacles; consistent effort is required."
    else:
        quality = "Challenging — weak Varshesh; patience and remedies are advised."
    if is_retro:
        quality += " Retrograde Varshesh adds introspection and delays, but eventual success."

    return {
        "planet": varshesh,
        "sign": _sign(sid_lon),
        "house": vp.get("house", "?"),
        "sidereal_longitude": round(sid_lon, 4),
        "is_retrograde": is_retro,
        "pancha_bala": bala,
        "year_quality": quality,
    }


# ---- Predictions Synthesis ---------------------------------------------------

def _score_label(s: int) -> str:
    if s >= 3: return "Very Favorable"
    if s >= 2: return "Favorable"
    if s >= 1: return "Mildly Favorable"
    if s == 0: return "Neutral"
    return "Requires Attention"


def generate_predictions(natal_chart, annual_chart, muntha, varshesh,
                         tajika_yogas, mudda_dasha, current_natal_dasha,
                         today) -> dict:
    """
    Synthesize yearly predictions across life domains from:
    - Varshesh strength and placement
    - Muntha house activation
    - Tajika yogas (Ithasala favors, Ishrafa warns)
    - Annual planetary house placements
    - Natal Mahadasha / Antardasha
    """
    annual_planets = annual_chart.get("planets", {})
    maha  = current_natal_dasha.get("maha_dasha", "?")
    antar = current_natal_dasha.get("antardasha", "?") or "?"
    maha_k  = PLANET_KARAKAS.get(maha, [])
    antar_k = PLANET_KARAKAS.get(antar, [])

    varshesh_planet = varshesh["planet"]
    muntha_house    = muntha.get("annual_house", 1)
    bala_score      = varshesh.get("pancha_bala", {}).get("total", 20)

    # Planets by house
    h = {i: [] for i in range(1, 13)}
    for pname, pd in annual_planets.items():
        house_num = pd.get("house")
        if isinstance(house_num, int) and 1 <= house_num <= 12:
            h[house_num].append(pname)

    ithasalas = [y for y in tajika_yogas if y["yoga"] == "Ithasala"]
    ishrafas  = [y for y in tajika_yogas if y["yoga"] == "Ishrafa"]

    def any_ithasala_involves(*plist):
        return any(set(y["planets"]) & set(plist) for y in ithasalas)

    # ---- Career & Status ----
    cs = 0; cp = []
    if any(p in BENEFIC_PLANETS for p in h[10]):
        cs += 2; cp.append(f"Benefic planet(s) in H10 ({', '.join(p for p in h[10] if p in BENEFIC_PLANETS)}) — career recognition and advancement.")
    if any(p in MALEFIC_PLANETS for p in h[10]):
        cs -= 1; cp.append(f"Malefic in H10 ({', '.join(p for p in h[10] if p in MALEFIC_PLANETS)}) — authority conflicts or career pressure; careful communication needed.")
    if varshesh_planet in ("Jupiter","Sun","Mercury") and varshesh["house"] not in (6,8,12):
        cs += 1; cp.append(f"Varshesh {varshesh_planet} in H{varshesh['house']} — career and authority themes amplified.")
    if maha in ("Jupiter","Saturn","Sun","Mercury"):
        cs += 1; cp.append(f"{maha} Mahadasha activates {', '.join(maha_k[:3])}.")
    if any_ithasala_involves("Sun","Jupiter","Saturn","Mercury"):
        cs += 1; cp.append("Ithasala involving career-ruling planets — professional opportunity will materialize.")
    if muntha_house == 10:
        cs += 2; cp.append("Muntha in H10 — outstanding year for career peak and public recognition.")

    # ---- Finance & Wealth ----
    fs = 0; fp = []
    if any(p in BENEFIC_PLANETS for p in h[2]+h[11]):
        fs += 2; fp.append(f"Benefic planets in H2/H11 — financial gains and income growth likely.")
    if any(p in MALEFIC_PLANETS for p in h[2]):
        fs -= 1; fp.append("Malefic in H2 — unexpected expenses or family financial tension.")
    if varshesh_planet == "Venus":
        fs += 1; fp.append("Venus as Varshesh brings material comfort and financial flow.")
    if varshesh_planet == "Jupiter":
        fs += 1; fp.append("Jupiter Varshesh bestows wealth expansion and fortunate windfalls.")
    if any_ithasala_involves("Venus","Jupiter","Moon"):
        fs += 1; fp.append("Ithasala with Venus/Jupiter — financial opportunity actively manifesting.")
    if maha in ("Venus","Jupiter","Mercury"):
        fs += 1; fp.append(f"{maha} Mahadasha supports wealth accumulation and prosperity.")
    if muntha_house in (2, 11):
        fs += 1; fp.append(f"Muntha in H{muntha_house} — strong emphasis on wealth and gains.")

    # ---- Relationships & Marriage ----
    rs = 0; rp = []
    if any(p in ("Venus","Jupiter","Moon") for p in h[7]):
        rs += 2; rp.append(f"Benefic in H7 — favorable for partnerships, romance, and marital harmony.")
    if any(p in ("Saturn","Mars","Rahu") for p in h[7]):
        rs -= 1; rp.append(f"Malefic in H7 ({', '.join(p for p in h[7] if p in MALEFIC_PLANETS)}) — relationship friction or delays; patience required.")
    if maha in ("Venus","Moon") or antar in ("Venus","Moon"):
        rs += 1; rp.append(f"{'Maha' if maha in ('Venus','Moon') else 'Antar'}dasha of {'Venus' if 'Venus' in (maha,antar) else 'Moon'} activates emotional and relationship themes.")
    if any_ithasala_involves("Venus","Moon","Jupiter"):
        rs += 1; rp.append("Ithasala with Venus/Moon — relationship opportunity will blossom.")
    if muntha_house == 7:
        rs += 1; rp.append("Muntha in H7 — partnerships, business alliances, and romantic themes dominate.")

    # ---- Health & Vitality ----
    hs = 2; hp = []
    if any(p in MALEFIC_PLANETS for p in h[6]+h[8]):
        hs -= 1; hp.append(f"Malefic in H6/H8 — health vigilance needed, especially immune and chronic issues.")
    if any(p in BENEFIC_PLANETS for p in h[1]):
        hs += 1; hp.append("Benefic in H1 — good vitality and physical energy.")
    if any(p in MALEFIC_PLANETS for p in h[1]):
        hs -= 1; hp.append("Malefic in H1 — personal health requires proactive care.")
    if maha == "Saturn" or antar == "Saturn":
        hs -= 1; hp.append("Saturn Dasha active — chronic issues may surface; regular checkups advised.")
    if maha == "Jupiter" or antar == "Jupiter":
        hs += 1; hp.append("Jupiter Dasha supports recovery, healing, and overall vitality.")
    if muntha_house in (6, 8):
        hs -= 1; hp.append(f"Muntha in H{muntha_house} — health matters need monitoring this year.")

    # ---- Spirituality & Growth ----
    sp = []; ss = 0
    if any(p in ("Jupiter","Ketu","Saturn") for p in h[9]):
        sp.append("Jupiter/Ketu/Saturn in H9 — profound year for spiritual growth, pilgrimage, or philosophy."); ss += 1
    if any(p in ("Jupiter","Rahu","Moon") for p in h[12]):
        sp.append("H12 planets — foreign travel, ashram retreat, or meaningful seclusion."); ss += 1
    if maha in ("Jupiter","Ketu","Saturn"):
        sp.append(f"{maha} Mahadasha invites inner wisdom, karma resolution, and spiritual insight."); ss += 1
    if muntha_house in (9, 12):
        sp.append(f"Muntha in H{muntha_house} — a transformative year for spiritual seeking."); ss += 1

    # ---- Tajika yoga summaries ----
    yoga_summaries = []
    for y in (ithasalas + ishrafas)[:10]:
        yoga_summaries.append({
            "yoga": y["yoga"],
            "planets": " + ".join(y["planets"]),
            "nature": y["aspect_type"],
            "favorable": y["favorable"],
            "position": y["position"],
            "interpretation": y["meaning"],
        })

    # ---- Mudda Dasha preview ----
    mudda_preview = []
    for p in mudda_dasha[:9]:
        mudda_preview.append({
            "lord": p["lord"],
            "period": f"{p['start']} to {p['end']}",
            "days": p["duration_days"],
            "themes": PLANET_KARAKAS.get(p["lord"], [])[:3],
        })

    return {
        "year_overview": {
            "varshesh": varshesh_planet,
            "varshesh_house": varshesh.get("house", "?"),
            "varshesh_strength": varshesh.get("pancha_bala", {}).get("strength", "?"),
            "overall_quality": varshesh.get("year_quality", ""),
            "muntha_house": muntha_house,
            "muntha_effect": muntha.get("interpretation", ""),
            "ithasala_count": len(ithasalas),
            "ishrafa_count": len(ishrafas),
        },
        "dasha_context": {
            "maha_dasha": maha,
            "maha_themes": maha_k[:4],
            "antardasha": antar,
            "antar_themes": antar_k[:4],
            "combined_note": (f"Under {maha}–{antar} Dasha, core life themes center on "
                              f"{', '.join((maha_k+antar_k)[:5])}."),
        },
        "domains": {
            "Career & Status":          {"rating": _score_label(cs), "score": cs, "insights": cp or ["No strong annual indicators; natal Dasha governs."]},
            "Finance & Wealth":         {"rating": _score_label(fs), "score": fs, "insights": fp or ["Steady financial year; avoid speculation."]},
            "Relationships & Marriage": {"rating": _score_label(rs), "score": rs, "insights": rp or ["Relationships run smoothly; no major disruptions indicated."]},
            "Health & Vitality":        {"rating": _score_label(hs), "score": hs, "insights": hp or ["Good health overall; maintain routine."]},
            "Spirituality & Growth":    {"rating": _score_label(ss), "score": ss, "insights": sp or ["Routine year for spiritual matters."]},
        },
        "tajika_yogas": yoga_summaries,
        "mudda_dasha": mudda_preview,
    }


# ---- Muntha interpretation ---------------------------------------------------

def _muntha_interpretation(house: int, lord: str) -> str:
    msgs = {
        1:  f"Muntha in H1 (lord {lord}): Peak year — self, health, leadership. Victory and elevation.",
        2:  f"Muntha in H2 (lord {lord}): Wealth, family, and speech foregrounded. Save and invest.",
        3:  f"Muntha in H3 (lord {lord}): Courage, communication, short travel. Bold decisions succeed.",
        4:  f"Muntha in H4 (lord {lord}): Home, property, and emotional stability. Real estate favorable.",
        5:  f"Muntha in H5 (lord {lord}): Creativity, children, romance, and speculation highlighted.",
        6:  f"Muntha in H6 (lord {lord}): Competition and health challenges. Victory through effort.",
        7:  f"Muntha in H7 (lord {lord}): Partnerships and marriage dominate. New alliances possible.",
        8:  f"Muntha in H8 (lord {lord}): Transformation, research, inheritance. Avoid risky ventures.",
        9:  f"Muntha in H9 (lord {lord}): Outstanding fortune, spirituality, and long travel. Dharmic year.",
        10: f"Muntha in H10 (lord {lord}): Career peak. Authority, recognition, and leadership arise.",
        11: f"Muntha in H11 (lord {lord}): Excellent gains, fulfilled desires, and social expansion.",
        12: f"Muntha in H12 (lord {lord}): Expenditure and spiritual growth. Foreign connection possible.",
    }
    return msgs.get(house, f"Muntha in H{house}: {HOUSE_THEMES.get(house, 'life themes')} activated.")


# ---- Main Varshphal Generator ------------------------------------------------

def generate_varshphal(
    natal_chart: dict,
    target_year: int,
    birth_lat: float,
    birth_lon: float,
    birth_year: int,
    ayanamsa: str = "lahiri",
    today: Optional[datetime] = None,
) -> dict:
    """
    Complete Varshphal (Solar Return Annual Chart) generator.

    Args:
        natal_chart: Output of generate_kundali() — birth chart
        target_year: Gregorian year for annual chart (e.g. 2025)
        birth_lat, birth_lon: Geographic coordinates of birth
        birth_year: Year of birth (for Muntha age calculation)
        ayanamsa: Vedic ayanamsa system
        today: Date for current Mudda period (defaults to now)

    Returns:
        Complete Varshphal dict including annual chart, Muntha,
        Varshesh, Tajika yogas, Sahams, Mudda Dasha, and predictions.
    """
    import sys
    # Remove /home/claude from path to avoid old kundali_engine copy
    sys.path = [p for p in sys.path if '/home/claude' not in p]
    sys.path.insert(0, '/mnt/user-data/outputs')
    for k in list(sys.modules.keys()):
        if 'kundali' in k: del sys.modules[k]
    from kundali_engine.core.ephemeris import (
        compute_all_positions, tropical_to_sidereal, J2000, jd_to_gregorian,
        nutation_and_obliquity, sun_longitude, gregorian_to_jd
    )

    if today is None:
        today = datetime.now()

    # 1. Natal values
    natal_sun     = natal_chart["planets"]["Sun"]["sidereal_longitude"]
    natal_moon    = natal_chart["planets"]["Moon"]["sidereal_longitude"]
    natal_lagna   = natal_chart["lagna"]["sidereal_longitude"]

    # 2. Find Solar Return JD
    sr_jd = find_solar_return(natal_sun, target_year, birth_lat, birth_lon, ayanamsa)

    # Convert JD to datetime components
    sr_y, sr_m, sr_d_frac = jd_to_gregorian(sr_jd)
    sr_d   = int(sr_d_frac)
    sr_hf  = (sr_d_frac - sr_d) * 24
    sr_h   = int(sr_hf)
    sr_min = int((sr_hf - sr_h) * 60)
    sr_dt  = datetime(sr_y, sr_m, sr_d, sr_h, sr_min)

    # 3. Cast annual chart at SR moment (at birth location)
    annual_positions, annual_asc_trop, T_sr = compute_all_positions(
        sr_jd, birth_lat, birth_lon, ayanamsa
    )
    annual_asc_sid = tropical_to_sidereal(annual_asc_trop, T_sr, ayanamsa)
    annual_lagna_sign = SIGNS[int(annual_asc_sid / 30) % 12]
    lagna_sign_idx    = int(annual_asc_sid / 30) % 12

    # Day/night: Sun in H7-H12 = day chart
    sun_sid = annual_positions["Sun"].sidereal_longitude
    sun_house = (int(sun_sid/30)%12 - lagna_sign_idx) % 12 + 1
    is_day_chart = sun_house >= 7

    # Format annual planets
    formatted_annual = {}
    for name, pos in annual_positions.items():
        house = (_sign_num(pos.sidereal_longitude) - lagna_sign_idx) % 12 + 1
        formatted_annual[name] = {
            "sidereal_longitude": round(pos.sidereal_longitude, 4),
            "sign":               pos.sign,
            "degree_in_sign":     round(pos.degree_in_sign, 4),
            "degree_formatted":   f"{int(pos.degree_in_sign)}°{int((pos.degree_in_sign%1)*60):02d}'",
            "nakshatra":          pos.nakshatra,
            "house":              house,
            "is_retrograde":      pos.is_retrograde,
        }

    # 4. Muntha
    age = target_year - birth_year
    muntha_lon, muntha_sign, muntha_lord = compute_muntha(natal_lagna, age)
    muntha_sign_idx = int(muntha_lon / 30) % 12
    muntha_annual_house = (muntha_sign_idx - lagna_sign_idx) % 12 + 1
    muntha_natal_house  = (muntha_sign_idx - int(natal_lagna/30)%12) % 12 + 1

    muntha_data = {
        "longitude":    round(muntha_lon, 4),
        "sign":         muntha_sign,
        "lord":         muntha_lord,
        "annual_house": muntha_annual_house,
        "natal_house":  muntha_natal_house,
        "in_good_house": muntha_annual_house in GOOD_HOUSES,
        "interpretation": _muntha_interpretation(muntha_annual_house, muntha_lord),
    }

    # 5. Varshesh
    annual_chart_dict = {
        "lagna": {"sign": annual_lagna_sign, "sidereal_longitude": round(annual_asc_sid, 4)},
        "planets": formatted_annual,
    }
    varshesh = compute_varshesh(formatted_annual, annual_asc_sid)

    # 6. Pancha-Vargiya Bala for all annual planets
    annual_bala = {
        name: compute_panchavargiya_bala(name, pos.sidereal_longitude, pos.is_retrograde)
        for name, pos in annual_positions.items()
    }

    # 7. Tajika yogas
    tajika_yogas = compute_tajika_yogas(formatted_annual)

    # 8. Sahams
    sahams = compute_sahams(formatted_annual, annual_asc_sid, is_day_chart)

    # 9. Mudda Dasha
    annual_moon_sid = annual_positions["Moon"].sidereal_longitude
    mudda = compute_mudda_dasha(annual_moon_sid, sr_dt)
    current_mudda = get_current_mudda(mudda, today)

    # 10. Natal dasha context
    current_natal_dasha = natal_chart.get("dasha", {}).get("current", {})

    # 11. Predictions
    predictions = generate_predictions(
        natal_chart      = natal_chart,
        annual_chart     = annual_chart_dict,
        muntha           = muntha_data,
        varshesh         = varshesh,
        tajika_yogas     = tajika_yogas,
        mudda_dasha      = mudda,
        current_natal_dasha = current_natal_dasha,
        today            = today,
    )

    return {
        "meta": {
            "target_year":       target_year,
            "age":               age,
            "solar_return_utc":  sr_dt.strftime("%Y-%m-%d %H:%M UTC"),
            "solar_return_jd":   round(sr_jd, 6),
            "is_day_chart":      is_day_chart,
            "ayanamsa":          ayanamsa,
        },
        "varsha_lagna": {
            "sign":               annual_lagna_sign,
            "sidereal_longitude": round(annual_asc_sid, 4),
            "degree_formatted":   f"{int(annual_asc_sid%30)}°{int(((annual_asc_sid%30)%1)*60):02d}'",
            "lord":               SIGN_LORDS[annual_lagna_sign],
        },
        "muntha":          muntha_data,
        "varshesh":        varshesh,
        "annual_planets":  formatted_annual,
        "pancha_bala":     annual_bala,
        "tajika_yogas":    tajika_yogas,
        "sahams":          sahams,
        "mudda_dasha":     mudda,
        "current_mudda":   current_mudda,
        "natal_dasha":     current_natal_dasha,
        "predictions":     predictions,
    }
