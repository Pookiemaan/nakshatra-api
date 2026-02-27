"""
matchmaker.py
=============
Ashta Koota (8-factor) Guna matching for Vedic compatibility.

Total points: 36
Recommended minimum: 18 points for compatibility

The 8 Kootas:
  1. Varna   (1 pt)  — Spiritual compatibility
  2. Vashya  (2 pts) — Dominance/attraction
  3. Tara    (3 pts) — Birth star compatibility
  4. Yoni    (4 pts) — Biological/sexual compatibility
  5. Graha Maitri (5 pts) — Friendship between Moon sign lords
  6. Gana    (6 pts) — Temperament (Deva/Manav/Rakshasa)
  7. Rashi   (7 pts) — Moon sign compatibility (Bhakoot)
  8. Nadi    (8 pts) — Pulse/constitution (most important)

Source: Parashara BPHS; standard Ashta Koota algorithm
"""

from typing import Dict, Tuple

# ── Nakshatra data ───────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

# Nakshatra → Gana: 0=Deva, 1=Manav, 2=Rakshasa
GANA = [
    0, 2, 1, 0, 1, 2, 0, 0, 2,   # Ashwini–Ashlesha
    2, 1, 0, 0, 2, 0, 1, 0, 2,   # Magha–Jyeshtha
    2, 1, 0, 0, 1, 2, 1, 0, 0,   # Mula–Revati
]

# Nakshatra → Nadi: 0=Aadi, 1=Madhya, 2=Antya
NADI = [
    0, 1, 2, 2, 1, 0, 0, 1, 2,
    0, 1, 2, 2, 1, 0, 0, 1, 2,
    0, 1, 2, 2, 1, 0, 0, 1, 2,
]

# Nakshatra → Yoni animal (0–13)
YONI = [
    0, 1, 2, 3, 4, 5, 6, 7, 8,   # Horse, Elephant, Goat, Serpent, Dog, Cat, Rat, Cow, Buffalo
    9, 1, 2, 10, 11, 12, 11, 13, 8,
    9, 3, 3, 13, 4, 6, 10, 12, 0,
]

# Yoni compatibility matrix (friend/enemy/neutral)
# 14 animals: Horse, Elephant, Goat, Serpent, Dog, Cat, Rat, Cow, Buffalo,
#             Tiger, Deer, Monkey, Mongoose, Lion
YONI_NAMES = ["Horse","Elephant","Goat","Serpent","Dog","Cat","Rat","Cow",
              "Buffalo","Tiger","Deer","Monkey","Mongoose","Lion"]

YONI_ENEMY = {
    0: 1,   # Horse ↔ Buffalo
    1: 0,
    2: 11,  # Goat ↔ Monkey
    3: 4,   # Serpent ↔ Mongoose (no match in short list, use 4=Dog)
    4: 3,
    5: 6,   # Cat ↔ Rat
    6: 5,
    7: 12,  # Cow ↔ Tiger
    8: 0,
    9: 7,
    10: 9,
    11: 2,
    12: 3,
    13: 10,
}

# Sign → Varna: 0=Brahmin, 1=Kshatriya, 2=Vaishya, 3=Shudra
VARNA = {
    "Cancer":0, "Scorpio":0, "Pisces":0,
    "Aries":1, "Leo":1, "Sagittarius":1,
    "Taurus":2, "Virgo":2, "Capricorn":2,
    "Gemini":3, "Libra":3, "Aquarius":3,
}

# Sign → Vashya group: 0=Chatushpada, 1=Manav, 2=Jalchar, 3=Vanchar, 4=Keeta
VASHYA_GROUP = {
    "Aries":0, "Taurus":0, "Leo":0, "Sagittarius":3, "Capricorn":2,
    "Gemini":1, "Virgo":1, "Libra":1, "Aquarius":1,
    "Cancer":2, "Pisces":2,
    "Scorpio":4,
}

# Sign → ruling planet for Graha Maitri
SIGN_LORD = {
    "Aries":"Mars", "Taurus":"Venus", "Gemini":"Mercury", "Cancer":"Moon",
    "Leo":"Sun", "Virgo":"Mercury", "Libra":"Venus", "Scorpio":"Mars",
    "Sagittarius":"Jupiter", "Capricorn":"Saturn", "Aquarius":"Saturn", "Pisces":"Jupiter"
}

# Planet friendship table: {planet: [friends]}
PLANET_FRIENDS = {
    "Sun":     ["Moon","Mars","Jupiter"],
    "Moon":    ["Sun","Mercury"],
    "Mars":    ["Sun","Moon","Jupiter"],
    "Mercury": ["Sun","Venus"],
    "Jupiter": ["Sun","Moon","Mars"],
    "Venus":   ["Mercury","Saturn"],
    "Saturn":  ["Mercury","Venus"],
}

PLANET_ENEMIES = {
    "Sun":     ["Venus","Saturn"],
    "Moon":    ["None"],
    "Mars":    ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury","Venus"],
    "Venus":   ["Sun","Moon"],
    "Saturn":  ["Sun","Moon","Mars"],
}

# Bhakoot (Rashi) compatibility: (sign1_idx - sign2_idx) mod 12
BHAKOOT_GOOD = {1, 2, 3, 4, 5, 7, 9, 11}   # Moon sign separations considered good
BHAKOOT_BAD  = {6, 8}                         # 6-8 and 9-5 patterns

# Tara: nakshatra distance groups
def tara_score(nak1: int, nak2: int) -> int:
    """Returns 0, 1.5, or 3 based on Tara compatibility."""
    diff = (nak2 - nak1) % 27
    # Tara groups of 9: Janma, Sampat, Vipat, Kshema, Pratyak, Sadhaka, Vadha, Mitra, Atimitra
    group = diff % 9
    # Good: 2(Sampat), 4(Kshema), 6(Sadhaka), 8(Atimitra) → 0-indexed: 1,3,5,7
    if group in {1, 3, 5, 7}: return 3
    if group in {0, 2, 6}: return 1
    return 0   # Vipat(2→group2=bad), Pratyak(4→bad), Vadha(6→bad)


# ── Koota calculations ───────────────────────────────────────

def varna_score(sign1: str, sign2: str) -> Tuple[int, int]:
    v1 = VARNA.get(sign1, 0)
    v2 = VARNA.get(sign2, 0)
    # Groom's varna should be ≥ bride's; same or higher = 1 pt
    score = 1 if v1 >= v2 else 0
    return score, 1


def vashya_score(sign1: str, sign2: str) -> Tuple[int, int]:
    g1 = VASHYA_GROUP.get(sign1, 1)
    g2 = VASHYA_GROUP.get(sign2, 1)
    if g1 == g2: return 2, 2
    # Simplified: adjacent groups = 1 pt
    if abs(g1 - g2) == 1: return 1, 2
    return 0, 2


def tara_koota(nak1: int, nak2: int) -> Tuple[int, int]:
    s1 = tara_score(nak1, nak2)
    s2 = tara_score(nak2, nak1)
    return min(s1 + s2, 3), 3


def yoni_score(nak1: int, nak2: int) -> Tuple[int, int]:
    y1 = YONI[nak1]
    y2 = YONI[nak2]
    if y1 == y2: return 4, 4
    if YONI_ENEMY.get(y1) == y2: return 0, 4
    return 2, 4


def graha_maitri(sign1: str, sign2: str) -> Tuple[int, int]:
    lord1 = SIGN_LORD.get(sign1, "Sun")
    lord2 = SIGN_LORD.get(sign2, "Moon")
    if lord1 == lord2: return 5, 5
    f1_likes_2 = lord2 in PLANET_FRIENDS.get(lord1, [])
    f2_likes_1 = lord1 in PLANET_FRIENDS.get(lord2, [])
    if f1_likes_2 and f2_likes_1: return 5, 5
    if f1_likes_2 or f2_likes_1: return 3, 5
    e1 = lord2 in PLANET_ENEMIES.get(lord1, [])
    e2 = lord1 in PLANET_ENEMIES.get(lord2, [])
    if e1 or e2: return 1, 5
    return 0, 5


def gana_score(nak1: int, nak2: int) -> Tuple[int, int]:
    g1 = GANA[nak1]
    g2 = GANA[nak2]
    if g1 == g2: return 6, 6
    # Deva-Manav = ok, Manav-Rakshasa = partial, Deva-Rakshasa = bad
    if (g1 == 0 and g2 == 1) or (g1 == 1 and g2 == 0): return 5, 6
    if (g1 == 1 and g2 == 2) or (g1 == 2 and g2 == 1): return 1, 6
    return 0, 6  # Deva-Rakshasa


def bhakoot_score(moon_sign1: str, moon_sign2: str) -> Tuple[int, int]:
    idx1 = SIGNS.index(moon_sign1) if moon_sign1 in SIGNS else 0
    idx2 = SIGNS.index(moon_sign2) if moon_sign2 in SIGNS else 0
    diff = abs(idx1 - idx2)
    if diff in {6, 8} or (12 - diff) in {6, 8}: return 0, 7
    return 7, 7


def nadi_score(nak1: int, nak2: int) -> Tuple[int, int]:
    n1 = NADI[nak1]
    n2 = NADI[nak2]
    # Same nadi = Nadi Dosha (0 pts) — most critical dosha
    if n1 == n2: return 0, 8
    return 8, 8


# ── Manglik check ────────────────────────────────────────────

MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}

def check_manglik(chart: dict) -> dict:
    """
    Manglik = Mars in houses 1, 2, 4, 7, 8, or 12.
    Double Manglik = Mars in 1 or 8 (stronger).
    """
    mars_house = chart.get("planets", {}).get("Mars", {}).get("house", 0)
    is_manglik = mars_house in MANGLIK_HOUSES
    is_double  = mars_house in {1, 8}
    return {
        "is_manglik": is_manglik,
        "is_double_manglik": is_double,
        "mars_house": mars_house,
        "note": (
            "Double Manglik — strong Mars placement. Best matched with another Manglik."
            if is_double else
            "Manglik — Mars in sensitive house. Consider Manglik partner or remedies."
            if is_manglik else
            "Not Manglik."
        )
    }


# ── Main compatibility function ───────────────────────────────

def compute_compatibility(chart1: dict, chart2: dict) -> dict:
    """
    Compute full Ashta Koota compatibility between two charts.
    """
    moon1 = chart1.get("moon_sign", "Aries")
    moon2 = chart2.get("moon_sign", "Aries")

    nak1_name = chart1.get("moon_nakshatra", "Ashwini")
    nak2_name = chart2.get("moon_nakshatra", "Ashwini")
    nak1 = NAKSHATRAS.index(nak1_name) if nak1_name in NAKSHATRAS else 0
    nak2 = NAKSHATRAS.index(nak2_name) if nak2_name in NAKSHATRAS else 0

    # Compute each koota
    v_sc,  v_mx  = varna_score(moon1, moon2)
    vs_sc, vs_mx = vashya_score(moon1, moon2)
    t_sc,  t_mx  = tara_koota(nak1, nak2)
    y_sc,  y_mx  = yoni_score(nak1, nak2)
    gm_sc, gm_mx = graha_maitri(moon1, moon2)
    ga_sc, ga_mx = gana_score(nak1, nak2)
    b_sc,  b_mx  = bhakoot_score(moon1, moon2)
    n_sc,  n_mx  = nadi_score(nak1, nak2)

    total = v_sc + vs_sc + t_sc + y_sc + gm_sc + ga_sc + b_sc + n_sc
    max_total = 36

    # Dosha flags
    nadi_dosha   = n_sc == 0
    bhakoot_dosha = b_sc == 0
    gana_dosha   = ga_sc == 0

    # Compatibility rating
    pct = total / max_total
    if pct >= 0.72:   rating = "Excellent"
    elif pct >= 0.55: rating = "Good"
    elif pct >= 0.41: rating = "Average"
    else:             rating = "Below Average"

    # Interpretation
    if total >= 27:
        interpretation = "Highly compatible match. Strong alignment across all key areas of life."
    elif total >= 21:
        interpretation = "Good compatibility. Minor differences can be worked through with mutual effort."
    elif total >= 18:
        interpretation = "Acceptable match. Some areas need attention, particularly those with low scores."
    else:
        interpretation = "Challenging compatibility. Careful consideration and consultation with an astrologer is advised."

    manglik1 = check_manglik(chart1)
    manglik2 = check_manglik(chart2)

    # Manglik compatibility note
    manglik_note = ""
    if manglik1["is_manglik"] and manglik2["is_manglik"]:
        manglik_note = "Both are Manglik — the doshas cancel each other. Favourable."
    elif manglik1["is_manglik"] or manglik2["is_manglik"]:
        manglik_note = "One partner is Manglik. Consider remedies or consult an astrologer."
    else:
        manglik_note = "Neither is Manglik. No Manglik consideration needed."

    return {
        "total_score": total,
        "max_score": max_total,
        "percentage": round(pct * 100, 1),
        "rating": rating,
        "interpretation": interpretation,
        "kootas": {
            "varna":        {"score": v_sc,  "max": v_mx,  "label": "Varna",        "meaning": "Spiritual compatibility"},
            "vashya":       {"score": vs_sc, "max": vs_mx, "label": "Vashya",       "meaning": "Dominance and attraction"},
            "tara":         {"score": t_sc,  "max": t_mx,  "label": "Tara",         "meaning": "Birth star compatibility"},
            "yoni":         {"score": y_sc,  "max": y_mx,  "label": "Yoni",         "meaning": "Biological compatibility"},
            "graha_maitri": {"score": gm_sc, "max": gm_mx, "label": "Graha Maitri", "meaning": "Planetary friendship"},
            "gana":         {"score": ga_sc, "max": ga_mx, "label": "Gana",         "meaning": "Temperament match"},
            "bhakoot":      {"score": b_sc,  "max": b_mx,  "label": "Bhakoot",      "meaning": "Moon sign compatibility"},
            "nadi":         {"score": n_sc,  "max": n_mx,  "label": "Nadi",         "meaning": "Constitution/pulse match"},
        },
        "doshas": {
            "nadi_dosha":    {"present": nadi_dosha,    "severity": "High",   "remedy": "Nadi Dosha Nivaran puja recommended"},
            "bhakoot_dosha": {"present": bhakoot_dosha, "severity": "Medium", "remedy": "Consult astrologer for remedies"},
            "gana_dosha":    {"present": gana_dosha,    "severity": "Low",    "remedy": "Patience and communication"},
        },
        "manglik": {
            "person1": manglik1,
            "person2": manglik2,
            "note": manglik_note,
        },
        "moon_signs": {"person1": moon1, "person2": moon2},
        "nakshatras":  {"person1": nak1_name, "person2": nak2_name},
    }
