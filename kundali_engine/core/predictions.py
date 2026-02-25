"""
predictions.py  --  Deep Vedic Astrology Predictions Engine
============================================================
Synthesizes six layers:
  1. Natal chart yogas (Parashari system)
  2. House-by-house natal analysis
  3. Vimshottari Dasha timing
  4. Gochara (transit) analysis from Moon & Lagna
  5. Varshphal (annual chart) context
  6. Domain-specific synthesis: career, finance, love, health, spirituality

Sources: BPHS, B.V. Raman "300 Combinations", K.N. Rao, SJC transit rules
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter",
}
OWN_SIGNS = {
    "Sun":["Leo"],"Moon":["Cancer"],"Mars":["Aries","Scorpio"],
    "Mercury":["Gemini","Virgo"],"Jupiter":["Sagittarius","Pisces"],
    "Venus":["Taurus","Libra"],"Saturn":["Capricorn","Aquarius"],
}
EXALTATION_SIGN = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra","Rahu":"Taurus","Ketu":"Scorpio",
}
EXALTATION_DEGREE = {
    "Sun":10,"Moon":3,"Mars":28,"Mercury":15,"Jupiter":5,"Venus":27,"Saturn":20,
    "Rahu":3,"Ketu":3,
}
DEBILITATION_SIGN = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries","Rahu":"Scorpio","Ketu":"Taurus",
}
PLANET_KARAKAS = {
    "Sun":     ["career","authority","father","government","vitality","leadership","soul"],
    "Moon":    ["mind","mother","emotions","popularity","travel","imagination","public life"],
    "Mars":    ["energy","siblings","courage","property","competition","surgery","ambition"],
    "Mercury": ["intellect","communication","trade","writing","education","analysis","skill"],
    "Jupiter": ["wisdom","fortune","children","religion","expansion","guidance","dharma"],
    "Venus":   ["love","beauty","luxury","arts","marriage","finance","harmony","pleasure"],
    "Saturn":  ["discipline","longevity","service","karma","delays","persistence","structure"],
    "Rahu":    ["ambition","innovation","foreign","technology","sudden change","obsession","illusion"],
    "Ketu":    ["spirituality","intuition","research","isolation","liberation","past karma","moksha"],
}
BENEFIC_PLANETS = {"Jupiter","Venus","Moon","Mercury"}
MALEFIC_PLANETS = {"Saturn","Mars","Sun","Rahu","Ketu"}
SATURN_FAV_FROM_MOON  = {3,6,11}
JUPITER_FAV_FROM_MOON = {2,5,7,9,11}
RAHU_FAV_FROM_MOON    = {3,6,10,11}

HOUSE_THEMES = {
    1: ("self","health","personality","vitality","body","life direction"),
    2: ("wealth","family","speech","accumulation","food","values"),
    3: ("courage","siblings","communication","short travel","skills","efforts"),
    4: ("home","mother","property","vehicles","happiness","inner peace"),
    5: ("children","creativity","romance","intellect","past life merit","speculation"),
    6: ("enemies","disease","debts","service","competition","daily work"),
    7: ("marriage","partnership","business","public relations","spouse","contracts"),
    8: ("transformation","inheritance","occult","longevity","secrets","hidden matters"),
    9: ("fortune","religion","higher education","long travel","guru","dharma"),
    10: ("career","reputation","authority","father","public life","achievements"),
    11: ("gains","friends","aspirations","elder siblings","networks","desires fulfilled"),
    12: ("loss","isolation","foreign lands","spirituality","moksha","expenditure"),
}

HOUSE_SIGNIFICATIONS = {
    1:  "self, body, personality, life path",
    2:  "wealth, speech, family, food, face",
    3:  "courage, siblings, efforts, short trips, communication",
    4:  "mother, home, property, comfort, peace of mind",
    5:  "children, creativity, romance, intellect, investments",
    6:  "health, enemies, debts, service, competition",
    7:  "spouse, partnerships, business, public image",
    8:  "longevity, transformation, occult, inheritance, secrets",
    9:  "luck, father, religion, higher education, long journeys",
    10: "career, status, fame, government, authority",
    11: "income, gains, friends, fulfilled wishes, networks",
    12: "expenditure, foreign, spirituality, losses, isolation",
}

NAKSHATRA_LORDS = (
    ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3
)
DASHA_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
               "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}

def _n(x): return x % 360.0
def _sign(lon): return SIGNS[int(lon/30)%12]
def _sign_idx(lon): return int(lon/30)%12
def _house_from(base_lon, planet_lon): return (_sign_idx(planet_lon) - _sign_idx(base_lon)) % 12 + 1
def _score_label(s):
    if s >= 4: return "Exceptional"
    if s >= 3: return "Very Favorable"
    if s >= 2: return "Favorable"
    if s >= 1: return "Mildly Favorable"
    if s == 0: return "Neutral"
    if s == -1: return "Mildly Challenging"
    if s == -2: return "Challenging"
    return "Requires Attention"


# ── Planet Dignity ──────────────────────────────────────────────────────────

def _planet_dignity(planet: str, sign: str, degree_in_sign: float = 0.0) -> dict:
    """Returns comprehensive dignity analysis for a planet."""
    is_own       = sign in OWN_SIGNS.get(planet, [])
    is_exalt     = sign == EXALTATION_SIGN.get(planet, "")
    is_debit     = sign == DEBILITATION_SIGN.get(planet, "")
    
    # Deep exaltation / deep debilitation
    exalt_deg = EXALTATION_DEGREE.get(planet, 0)
    is_deep_exalt = is_exalt and abs(degree_in_sign - exalt_deg) <= 3
    is_deep_debit = is_debit and abs(degree_in_sign - (exalt_deg + 30) % 30) <= 3

    if is_deep_exalt:
        dignity, strength = "Deep Exaltation", "Exceptional"
    elif is_exalt:
        dignity, strength = "Exalted", "Strong"
    elif is_own:
        dignity, strength = "Own Sign", "Strong"
    elif is_debit:
        dignity, strength = "Debilitated", "Weak"
    else:
        dignity, strength = "Neutral", "Moderate"

    return {"dignity": dignity, "strength": strength,
            "is_strong": strength in ("Exceptional","Strong"),
            "is_weak": is_debit, "is_exalt": is_exalt, "is_own": is_own}


# ── House Lord Analysis ─────────────────────────────────────────────────────

def _get_house_lord(lagna_sign: str, house_num: int) -> str:
    lagna_idx = SIGNS.index(lagna_sign)
    target_sign = SIGNS[(lagna_idx + house_num - 1) % 12]
    return SIGN_LORDS[target_sign]

def _house_lord_quality(lord: str, house_placed: int) -> Tuple[str, str]:
    """Whether house lord is in a good/bad position."""
    if house_placed in (1,5,9,10,11):
        return "Favorable", f"{lord} placed in upachaya/trikona — house themes strongly supported"
    elif house_placed in (2,3,4,7):
        return "Mixed", f"{lord} in neutral house — moderate outcomes"
    else:  # 6, 8, 12
        return "Challenging", f"{lord} in dusthana (H{house_placed}) — house themes face obstacles"


# ── Natal Yoga Detection ────────────────────────────────────────────────────

def detect_natal_yogas(natal_chart: dict) -> List[dict]:
    yogas = []
    planets = natal_chart.get("planets", {})
    lagna_sign = natal_chart.get("lagna", {}).get("sign", "Aries")
    li = SIGNS.index(lagna_sign)

    def ph(p): return planets.get(p, {}).get("house", 0)
    def ps(p): return planets.get(p, {}).get("sign", "")
    def pd(p): return planets.get(p, {}).get("degree_in_sign", 0)

    def is_strong(p):
        s = ps(p)
        return s in OWN_SIGNS.get(p, []) or s == EXALTATION_SIGN.get(p, "")

    def hl(h): return SIGN_LORDS[SIGNS[(li + h - 1) % 12]]

    kl = {hl(h) for h in (1, 4, 7, 10)}
    tl = {hl(h) for h in (1, 5, 9)}

    # ── Raj Yoga
    for k in kl:
        for t in tl:
            if k != t and ph(k) == ph(t) and ph(k) > 0:
                yogas.append({
                    "name": "Raj Yoga",
                    "planets": [k, t],
                    "description": (f"{k} (Kendra lord) + {t} (Trikona lord) conjunct in H{ph(k)} — "
                                    f"career elevation, authority, public recognition. One of the most auspicious combinations."),
                    "strength": "Strong" if (is_strong(k) or is_strong(t)) else "Moderate",
                    "domain": ["career", "authority", "recognition", "status"],
                })

    # ── Dhana Yoga
    l2 = hl(2); l11 = hl(11); l5 = hl(5); l9 = hl(9)
    if ph(l2) == ph(l11) and ph(l2) > 0:
        yogas.append({
            "name": "Dhana Yoga (2L+11L)",
            "planets": [l2, l11],
            "description": f"2nd lord {l2} + 11th lord {l11} in same house — powerful wealth yoga; accumulation and income growth.",
            "strength": "Strong" if (is_strong(l2) or is_strong(l11)) else "Moderate",
            "domain": ["finance", "wealth", "income"],
        })
    if ph(l5) == ph(l9) and ph(l5) > 0:
        yogas.append({
            "name": "Lakshmi Yoga",
            "planets": [l5, l9],
            "description": f"5th lord {l5} + 9th lord {l9} conjunct — fortune, wisdom, and divine blessings; exceptional prosperity.",
            "strength": "Strong" if (is_strong(l5) or is_strong(l9)) else "Moderate",
            "domain": ["fortune", "spirituality", "wealth"],
        })

    # ── Gaja-Kesari
    moon_si = _sign_idx(planets.get("Moon", {}).get("sidereal_longitude", 0))
    jup_si  = _sign_idx(planets.get("Jupiter", {}).get("sidereal_longitude", 0))
    jfm = (jup_si - moon_si) % 12 + 1
    if jfm in (1, 4, 7, 10):
        yogas.append({
            "name": "Gaja-Kesari Yoga",
            "planets": ["Jupiter", "Moon"],
            "description": (f"Jupiter in {jfm}th from Moon (Kendra) — intelligence, fame, fortune, "
                            f"and commanding presence. Highly regarded wisdom attracts recognition."),
            "strength": "Strong" if is_strong("Jupiter") else "Moderate",
            "domain": ["fame", "wisdom", "prosperity", "respect"],
        })

    # ── Budha-Aditya
    if ph("Sun") == ph("Mercury") and ph("Sun") > 0:
        yogas.append({
            "name": "Budha-Aditya Yoga",
            "planets": ["Sun", "Mercury"],
            "description": ("Sun + Mercury conjunct — sharp analytical mind, excellent communication, "
                            "administrative talent, and intellectual leadership."),
            "strength": "Moderate",
            "domain": ["intellect", "communication", "administration"],
        })

    # ── Pancha-Mahapurusha: Sasa
    sat_h = ph("Saturn"); sat_s = ps("Saturn")
    if sat_h in (1, 4, 7, 10) and sat_s in (OWN_SIGNS.get("Saturn", []) + [EXALTATION_SIGN.get("Saturn", "")]):
        yogas.append({
            "name": "Sasa Yoga (Pancha-Mahapurusha)",
            "planets": ["Saturn"],
            "description": (f"Saturn in Kendra ({sat_h}th house) in own/exalted sign — great discipline, "
                            f"administrative mastery, longevity, public leadership. Long-lasting legacy."),
            "strength": "Very Strong",
            "domain": ["discipline", "power", "longevity", "leadership"],
        })

    # ── Hamsa
    jup_h = ph("Jupiter"); jup_s = ps("Jupiter")
    if jup_h in (1, 4, 7, 10) and jup_s in (OWN_SIGNS.get("Jupiter", []) + [EXALTATION_SIGN.get("Jupiter", "")]):
        yogas.append({
            "name": "Hamsa Yoga (Pancha-Mahapurusha)",
            "planets": ["Jupiter"],
            "description": (f"Jupiter in Kendra ({jup_h}th house) in own/exalted sign — wisdom, "
                            f"prosperity, spiritual leadership, compassion, and great fortune."),
            "strength": "Very Strong",
            "domain": ["wisdom", "fortune", "spirituality", "generosity"],
        })

    # ── Ruchaka (Mars)
    mars_h = ph("Mars"); mars_s = ps("Mars")
    if mars_h in (1, 4, 7, 10) and mars_s in (OWN_SIGNS.get("Mars", []) + [EXALTATION_SIGN.get("Mars", "")]):
        yogas.append({
            "name": "Ruchaka Yoga (Pancha-Mahapurusha)",
            "planets": ["Mars"],
            "description": (f"Mars in Kendra ({mars_h}th house) in own/exalted sign — military/athletic "
                            f"prowess, sharp mind, fearlessness, and executive leadership."),
            "strength": "Very Strong",
            "domain": ["energy", "courage", "ambition", "victory"],
        })

    # ── Viparita Raj Yoga
    for dh in (6, 8, 12):
        dl = hl(dh)
        if ph(dl) in (6, 8, 12) and ph(dl) != dh:
            yogas.append({
                "name": "Viparita Raj Yoga",
                "planets": [dl],
                "description": (f"Dusthana lord {dl} (H{dh}) placed in another dusthana — rise from adversity, "
                                 f"unexpected gains from enemies' downfall. Setbacks become springboards."),
                "strength": "Moderate",
                "domain": ["resilience", "unexpected gains", "reversal of fortune"],
            })

    # ── Neecha Bhanga (debilitation cancellation)
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
        if ps(p) == DEBILITATION_SIGN.get(p, ""):
            deb_sign_lord = SIGN_LORDS[ps(p)]
            if ph(deb_sign_lord) in (1,4,7,10) and is_strong(deb_sign_lord):
                yogas.append({
                    "name": f"Neecha Bhanga — {p}",
                    "planets": [p, deb_sign_lord],
                    "description": (f"{p} debilitated in {ps(p)}, but {deb_sign_lord} (sign lord) is strong — "
                                    f"debilitation is cancelled. Planet's themes materialize after initial struggle."),
                    "strength": "Moderate",
                    "domain": PLANET_KARAKAS.get(p, [])[:3],
                })

    # ── Kala Sarpa Yoga
    planets_list = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
    rahu_lon = planets.get("Rahu", {}).get("sidereal_longitude", 0)
    ketu_lon = planets.get("Ketu", {}).get("sidereal_longitude", 0)
    
    def between_rahu_ketu(lon):
        """Check if lon is between Rahu and Ketu in forward direction."""
        r, k = rahu_lon % 360, ketu_lon % 360
        if r > k:
            return k <= lon <= r
        else:
            return lon >= r or lon <= k
    
    all_between = all(
        between_rahu_ketu(planets.get(p, {}).get("sidereal_longitude", 0))
        for p in planets_list if p in planets
    )
    if all_between:
        yogas.append({
            "name": "Kala Sarpa Yoga",
            "planets": ["Rahu", "Ketu"],
            "description": ("All planets hemmed between Rahu and Ketu — intense karma, extraordinary destiny. "
                            "Life alternates between peaks and valleys; spiritual practice transforms this yoga's challenge into power."),
            "strength": "Very Strong (both positive and negative potential)",
            "domain": ["karma", "transformation", "destiny"],
        })

    return yogas


# ── Natal Chart House Analysis ──────────────────────────────────────────────

def analyze_natal_houses(natal_chart: dict) -> dict:
    """Deep analysis of all 12 houses based on occupants, lords, and aspects."""
    planets   = natal_chart.get("planets", {})
    lagna_sig = natal_chart.get("lagna", {}).get("sign", "Aries")
    lagna_lon = natal_chart.get("lagna", {}).get("sidereal_longitude", 0)
    li        = SIGNS.index(lagna_sig)

    def ph(p):  return planets.get(p, {}).get("house", 0)
    def ps(p):  return planets.get(p, {}).get("sign", "")
    def pd(p):  return planets.get(p, {}).get("degree_in_sign", 0)
    def pr(p):  return planets.get(p, {}).get("is_retrograde", False)
    def hl(h):  return SIGN_LORDS[SIGNS[(li + h - 1) % 12]]

    # Planets grouped by house
    house_occupants = {i: [] for i in range(1, 13)}
    for pname, pdata in planets.items():
        h_num = pdata.get("house", 0)
        if 1 <= h_num <= 12:
            house_occupants[h_num].append(pname)

    analysis = {}

    for house_num in range(1, 13):
        lord = hl(house_num)
        lord_house = ph(lord)
        lord_sign  = ps(lord)
        lord_dign  = _planet_dignity(lord, lord_sign, pd(lord))
        lord_qual, lord_note = _house_lord_quality(lord, lord_house)
        occupants = house_occupants[house_num]

        # Score: lord's placement + occupants
        score = 0
        notes = []

        # Lord placement scoring
        if lord_house in (1,5,9,10,11):
            score += 2
        elif lord_house in (2,3,4,7):
            score += 1
        elif lord_house in (6,8,12):
            score -= 1

        if lord_dign["is_strong"]:
            score += 1
            notes.append(f"Lord {lord} is {lord_dign['dignity']} — powerful expression of this house's themes.")
        elif lord_dign["is_weak"]:
            score -= 1
            notes.append(f"Lord {lord} is {lord_dign['dignity']} — house themes require extra effort to manifest.")

        if lord_house not in (6, 8, 12):
            notes.append(f"Lord {lord} in H{lord_house} ({HOUSE_SIGNIFICATIONS.get(lord_house, '...')}) — {lord_note}.")

        # Occupant analysis
        benefic_occ = [p for p in occupants if p in BENEFIC_PLANETS]
        malefic_occ = [p for p in occupants if p in MALEFIC_PLANETS]

        if benefic_occ:
            score += len(benefic_occ)
            notes.append(f"Benefic(s) {', '.join(benefic_occ)} in this house — natural protection and positive expression.")
        if malefic_occ:
            score -= len(malefic_occ) // 2  # malefics give challenge but also drive
            notes.append(f"Malefic(s) {', '.join(malefic_occ)} here — drive and discipline, but also friction in {HOUSE_SIGNIFICATIONS.get(house_num, 'these themes')}.")

        analysis[house_num] = {
            "house": house_num,
            "signification": HOUSE_SIGNIFICATIONS.get(house_num, ""),
            "lord": lord,
            "lord_house": lord_house,
            "lord_dignity": lord_dign["dignity"],
            "lord_quality": lord_qual,
            "occupants": occupants,
            "benefic_occupants": benefic_occ,
            "malefic_occupants": malefic_occ,
            "score": score,
            "quality": _score_label(score),
            "notes": notes,
        }

    return analysis


# ── Transit Analysis ────────────────────────────────────────────────────────

def analyze_transits(natal_chart: dict, current_planet_positions: dict) -> dict:
    planets    = natal_chart.get("planets", {})
    natal_moon = planets.get("Moon", {}).get("sidereal_longitude", 0)
    natal_lagna = natal_chart.get("lagna", {}).get("sidereal_longitude", 0)

    results = {}

    # Saturn
    sat_lon = current_planet_positions.get("Saturn", {}).get("sidereal_longitude", 0)
    sat_sign = current_planet_positions.get("Saturn", {}).get("sign", _sign(sat_lon))
    sfm = _house_from(natal_moon, sat_lon)
    sfl = _house_from(natal_lagna, sat_lon)
    is_sade_sati  = sfm in {12, 1, 2}
    is_ashtama    = sfm == 8
    is_kantak     = sfl == 4

    if is_sade_sati:
        sq = "Challenging (Sade Sati)"
        phase = {"12": "Rising Phase — approaching storm", "1": "Peak Phase — full karmic reckoning", "2": "Setting Phase — resolution emerging"}[str(sfm)]
        si = (f"SADE SATI [{phase}] — Saturn transits H{sfm} from natal Moon (in {sat_sign}). "
              f"A 7.5-year karmic cycle of restructuring, delays, and emotional depth. Life's "
              f"foundations are tested to be rebuilt stronger. Integrity, humility, and service are "
              f"the only antidotes. This is not punishment — it is preparation for greater heights.")
    elif is_ashtama:
        sq = "Very Challenging (Ashtama Shani)"
        si = (f"ASHTAMA SHANI — Saturn H8 from natal Moon. A 2.5-year period of intense karmic pressure "
              f"on health, finances, and relationships. Minimize speculation, avoid major life changes "
              f"unless forced. Spiritual practice and service become lifelines. What survives this transit is built to last.")
    elif is_kantak:
        sq = "Challenging (Kantak Shani)"
        si = (f"KANTAK SHANI — Saturn H4 from Lagna ({sat_sign}). Domestic unrest, career setbacks, "
              f"property issues, or relationship with mother strained. Patience and perseverance are required. "
              f"Home and inner peace need conscious effort to maintain.")
    elif sfm in SATURN_FAV_FROM_MOON:
        sq = "Favorable"
        si = (f"Saturn H{sfm} from Moon ({sat_sign}) — disciplined work receives recognition. "
              f"Career advancement, financial stability, and tangible results for past efforts. "
              f"A productive, grounded period favoring long-term commitments.")
    else:
        sq = "Mixed"
        si = (f"Saturn H{sfm} from Moon ({sat_sign}) — restraint and caution are advisable. "
              f"Some delays but steady progress possible through disciplined effort.")

    results["Saturn"] = {
        "transit_sign": sat_sign, "from_moon_house": sfm, "from_lagna_house": sfl,
        "is_sade_sati": is_sade_sati, "is_ashtama": is_ashtama, "is_kantak": is_kantak,
        "quality": sq, "interpretation": si
    }

    # Jupiter
    jup_lon  = current_planet_positions.get("Jupiter", {}).get("sidereal_longitude", 0)
    jup_sign = current_planet_positions.get("Jupiter", {}).get("sign", _sign(jup_lon))
    jfm = _house_from(natal_moon, jup_lon)
    jfl = _house_from(natal_lagna, jup_lon)
    jq  = "Favorable" if jfm in JUPITER_FAV_FROM_MOON else "Challenging"
    ji  = (
        f"Jupiter transiting {jup_sign}, H{jfm} from natal Moon. "
        + (f"Exceptional year for expansion, fortune, wisdom, and blessings — especially in {HOUSE_SIGNIFICATIONS.get(jfm,'these areas')}."
           if jq == "Favorable"
           else f"Caution with over-optimism and inflated expectations. Focus on consolidation rather than expansion in {HOUSE_SIGNIFICATIONS.get(jfm,'these areas')}.")
    )
    results["Jupiter"] = {"transit_sign": jup_sign, "from_moon_house": jfm, "from_lagna_house": jfl, "quality": jq, "interpretation": ji}

    # Rahu
    rahu_lon  = current_planet_positions.get("Rahu", {}).get("sidereal_longitude", 0)
    rahu_sign = current_planet_positions.get("Rahu", {}).get("sign", _sign(rahu_lon))
    rfm = _house_from(natal_moon, rahu_lon)
    rfl = _house_from(natal_lagna, rahu_lon)
    rq  = "Favorable" if rfm in RAHU_FAV_FROM_MOON else "Challenging"
    ri  = (
        f"Rahu transiting {rahu_sign}, H{rfm} from Moon. "
        + (f"Ambition surges — foreign opportunities, technology, and unconventional paths open. "
           f"Trust your instincts but verify before acting."
           if rq == "Favorable"
           else f"Guard against illusions, deception, and impulsive choices in {HOUSE_SIGNIFICATIONS.get(rfm,'these matters')}. "
                f"Clarity and grounded thinking are essential counterweights.")
    )
    results["Rahu"] = {"transit_sign": rahu_sign, "from_moon_house": rfm, "from_lagna_house": rfl, "quality": rq, "interpretation": ri}

    # Ketu
    ketu_lon  = current_planet_positions.get("Ketu", {}).get("sidereal_longitude", 0)
    ketu_sign = current_planet_positions.get("Ketu", {}).get("sign", _sign(ketu_lon))
    kfm = _house_from(natal_moon, ketu_lon)
    kq  = "Favorable" if kfm in {3, 6, 11} else "Challenging"
    ki  = (
        f"Ketu transiting {ketu_sign}, H{kfm} from Moon. "
        + ("Spiritual insight deepens. Research, intuition, and detachment serve well."
           if kq == "Favorable"
           else f"Unexpected separations or disruptions in {HOUSE_SIGNIFICATIONS.get(kfm,'these areas')}. "
                f"Introspection and releasing attachments are the path forward.")
    )
    results["Ketu"] = {"transit_sign": ketu_sign, "from_moon_house": kfm, "quality": kq, "interpretation": ki}

    # Mars
    mars_lon  = current_planet_positions.get("Mars", {}).get("sidereal_longitude", 0)
    mars_sign = current_planet_positions.get("Mars", {}).get("sign", _sign(mars_lon))
    mfm = _house_from(natal_moon, mars_lon)
    mq  = "Favorable" if mfm in {3, 6, 10, 11} else "Challenging"
    mi  = (
        f"Mars transiting {mars_sign}, H{mfm} from Moon. "
        + ("Energy, initiative, and competitive drive are well-directed. Good for new ventures and physical activities."
           if mq == "Favorable"
           else f"Frustration, aggression, or conflicts possible in {HOUSE_SIGNIFICATIONS.get(mfm,'these areas')}. "
                f"Channel energy constructively; avoid impulsive confrontations.")
    )
    results["Mars"] = {"transit_sign": mars_sign, "from_moon_house": mfm, "quality": mq, "interpretation": mi}

    return results


# ── Dasha Analysis ──────────────────────────────────────────────────────────

def analyze_dasha_period(natal_chart: dict, current_dasha: dict) -> dict:
    planets    = natal_chart.get("planets", {})
    lagna_sign = natal_chart.get("lagna", {}).get("sign", "Aries")
    li         = SIGNS.index(lagna_sign)

    def analyze_one(pname):
        if not pname or pname == "?":
            return {"planet": pname, "quality": "Unknown", "themes": [], "interpretation": ""}
        pdata   = planets.get(pname, {})
        p_house = pdata.get("house", 0)
        p_sign  = pdata.get("sign", "")
        p_retro = pdata.get("is_retrograde", False)
        p_deg   = pdata.get("degree_in_sign", 0)
        dign    = _planet_dignity(pname, p_sign, p_deg)
        themes  = PLANET_KARAKAS.get(pname, [])[:5]
        ht_keys = HOUSE_THEMES.get(p_house, ("various topics",))

        if dign["is_strong"] and p_house in (1,5,9,10,11):
            quality = "Excellent"
        elif dign["is_weak"] or p_house in (6, 8):
            quality = "Challenging"
        elif (dign["is_strong"]) or p_house in (1,5,9,10):
            quality = "Favorable"
        elif p_retro:
            quality = "Mixed — delays, then gains (retrograde energy)"
        else:
            quality = "Moderate"

        ht = ht_keys[0] if ht_keys else "various"
        interp = (
            f"{pname} Dasha ({dign['dignity']}, H{p_house}—{ht}): "
            f"{'Strong and supportive' if dign['is_strong'] else 'Requires effort'} period for "
            f"{', '.join(themes[:3])}."
        )
        if p_retro:
            interp += " Retrograde adds introspection and revisiting past matters before forward movement."
        if dign["is_weak"]:
            interp += f" Planet's debilitation means results come through struggle; discipline and remedies help."

        return {"planet": pname, "house": p_house, "sign": p_sign, "dignity": dign["dignity"],
                "quality": quality, "themes": themes, "interpretation": interp}

    maha  = current_dasha.get("maha_dasha", "?")
    antar = current_dasha.get("antardasha", "?") or "?"

    maha_analysis  = analyze_one(maha)
    antar_analysis = analyze_one(antar)

    # Combined themes
    maha_k  = PLANET_KARAKAS.get(maha, [])[:4]
    antar_k = PLANET_KARAKAS.get(antar, [])[:3]
    combined = list(dict.fromkeys(maha_k + antar_k))[:6]  # deduplicate

    combined_note = (
        f"Under {maha}–{antar} Dasha, the life chapters of "
        f"{', '.join(combined[:4])} take center stage. "
        f"{maha_analysis['interpretation']} {antar_analysis['interpretation']}"
    )

    return {
        "maha_dasha": maha, "maha_analysis": maha_analysis,
        "antardasha": antar, "antar_analysis": antar_analysis,
        "combined_themes": combined,
        "combined_interpretation": combined_note,
    }


# ── Remedies ────────────────────────────────────────────────────────────────

def _suggest_remedies(maha: str, antar: str, sade_sati: bool, ashtama: bool,
                      natal_yogas: List[dict] = None) -> List[dict]:
    remedies = []
    pr = {
        "Sun": {
            "mantra": "Om Hraam Hreem Hraum Sah Suryaya Namah (108× on Sundays at sunrise)",
            "gem": "Ruby (Manik) in gold on right ring finger (test first)",
            "charity": "Donate wheat, copper vessel, or jaggery on Sundays",
            "practice": "Surya Namaskar at sunrise; honor father; eat before sunset on Sundays",
            "timing": "Sunday mornings, sunrise hour",
        },
        "Moon": {
            "mantra": "Om Sraam Sreem Sraum Sah Chandraya Namah (108× on Mondays)",
            "gem": "Natural Pearl or Moonstone in silver on right little finger",
            "charity": "Donate rice, milk, or white cloth on Mondays",
            "practice": "Meditation near water; honor mother; fast on Mondays",
            "timing": "Monday evenings at moonrise",
        },
        "Mars": {
            "mantra": "Om Kraam Kreem Kraum Sah Bhoumaya Namah (108× on Tuesdays)",
            "gem": "Red Coral (Moonga) in copper or gold on right ring finger",
            "charity": "Donate red lentils, jaggery, or copper items on Tuesdays",
            "practice": "Physical exercise; practice patience; visit Hanuman temple on Tuesdays",
            "timing": "Tuesday mornings",
        },
        "Mercury": {
            "mantra": "Om Braam Breem Braum Sah Budhaya Namah (108× on Wednesdays)",
            "gem": "Emerald (Panna) in gold on right little finger",
            "charity": "Donate green moong dal or green vegetables on Wednesdays",
            "practice": "Journaling; learn a new skill; recite Vishnu Sahasranama",
            "timing": "Wednesday mornings",
        },
        "Jupiter": {
            "mantra": "Om Graam Greem Graum Sah Guruve Namah (108× on Thursdays)",
            "gem": "Yellow Sapphire (Pukhraj) in gold on right index finger",
            "charity": "Donate turmeric, chickpeas, or yellow cloth on Thursdays",
            "practice": "Study scriptures; seek guidance from teacher/mentor; practice generosity",
            "timing": "Thursday mornings",
        },
        "Venus": {
            "mantra": "Om Draam Dreem Draum Sah Shukraya Namah (108× on Fridays)",
            "gem": "Diamond or White Sapphire in platinum/silver on right middle finger",
            "charity": "Donate white sweets, rice, or silk on Fridays",
            "practice": "Cultivate beauty, art, music; practice gratitude; honor women in your life",
            "timing": "Friday evenings",
        },
        "Saturn": {
            "mantra": "Om Praam Preem Praum Sah Shanaischaraya Namah (108× on Saturdays)",
            "gem": "Blue Sapphire (Neelam) in silver — test for 7 days before wearing",
            "charity": "Donate sesame, black lentils (urad dal), or mustard oil on Saturdays",
            "practice": "Serve the elderly, poor, or disabled; fast on Saturdays; Hanuman Chalisa",
            "timing": "Saturday mornings, Saturn hora",
        },
        "Rahu": {
            "mantra": "Om Bhraam Bhreem Bhraum Sah Rahave Namah (108× on Saturdays)",
            "gem": "Hessonite Garnet (Gomed) — test first, consult astrologer",
            "charity": "Feed crows or donate blue items on Saturdays",
            "practice": "Durga/Kali puja; maintain clarity and truth; avoid deception",
            "timing": "Saturday evenings or Rahu Kaal",
        },
        "Ketu": {
            "mantra": "Om Sraam Sreem Sraum Sah Ketave Namah (108× on Tuesdays)",
            "gem": "Cat's Eye (Lahsuniya) — test first, consult astrologer",
            "charity": "Donate sesame, blanket, or multicolored cloth on Tuesdays",
            "practice": "Ganesha puja; spiritual study and meditation; release material attachments",
            "timing": "Tuesday mornings",
        },
    }

    if maha in pr:
        r = pr[maha]
        remedies.append({"for": f"{maha} Mahadasha", "priority": "High", **r})

    if antar and antar != maha and antar in pr:
        r = pr[antar]
        remedies.append({"for": f"{antar} Antardasha", "priority": "Medium", **r})

    if sade_sati:
        remedies.append({
            "for": "Sade Sati — Saturn Transit",
            "priority": "High",
            "mantra": "Om Praam Preem Praum Sah Shanaischaraya Namah + Hanuman Chalisa daily",
            "gem": "Avoid new gemstones during Sade Sati unless tested and confirmed",
            "charity": "Donate black sesame, mustard oil, and iron items every Saturday",
            "practice": (
                "Hanuman Chalisa on Saturdays; fast on Saturdays; serve the poor and elderly; "
                "practice radical acceptance and non-attachment. Sade Sati is karmic purification — "
                "it removes what no longer serves the soul's growth."
            ),
            "timing": "Saturday morning through Saturn hora",
        })

    if ashtama:
        remedies.insert(0, {
            "for": "Ashtama Shani — Critical Saturn Transit",
            "priority": "Urgent",
            "mantra": "Maha Mrityunjaya Mantra (108× daily) + Shiva Panchakshara Stotra",
            "gem": "Avoid major gem changes during this period",
            "charity": "Donate iron, sesame, black cloth, and shoes to the poor every Saturday",
            "practice": (
                "Daily Shiva puja; avoid major decisions, speculation, and risky ventures; "
                "health checkups essential; Navagraha Shanti recommended; focus on spiritual merit."
            ),
            "timing": "Daily, with special emphasis on Saturdays and ashtami tithis",
        })

    return remedies


# ── Main Prediction Engine ──────────────────────────────────────────────────

def generate_predictions(
    natal_chart: dict,
    current_dasha: dict,
    today: datetime = None,
    current_planet_positions: Optional[dict] = None,
    varshphal_context: Optional[dict] = None,
) -> dict:
    """
    Generate comprehensive Vedic astrology predictions.
    
    Layers synthesized:
    1. Natal yogas → lifelong backdrop
    2. House analysis → permanent strengths/weaknesses  
    3. Dasha → current life chapter
    4. Transits → current environmental conditions
    5. Varshphal → annual overlay (optional)
    6. Domain synthesis → career, finance, love, health, spirituality
    """
    if today is None:
        today = datetime.now()

    planets    = natal_chart.get("planets", {})
    lagna_sign = natal_chart.get("lagna", {}).get("sign", "Aries")
    lagna_lon  = natal_chart.get("lagna", {}).get("sidereal_longitude", 0)
    moon_lon   = planets.get("Moon", {}).get("sidereal_longitude", 0)
    moon_sign  = natal_chart.get("moon_sign", _sign(moon_lon))
    li         = SIGNS.index(lagna_sign)

    def ph(p):  return planets.get(p, {}).get("house", 0)
    def ps(p):  return planets.get(p, {}).get("sign", "")
    def pd(p):  return planets.get(p, {}).get("degree_in_sign", 0)
    def pr(p):  return planets.get(p, {}).get("is_retrograde", False)
    def hl(h):  return SIGN_LORDS[SIGNS[(li + h - 1) % 12]]

    # If no current positions given, use today's positions
    if current_planet_positions is None:
        try:
            from .ephemeris import compute_all_positions, gregorian_to_jd
            jd = gregorian_to_jd(today.year, today.month, today.day,
                                  today.hour + today.minute / 60)
            raw_pos, _, _ = compute_all_positions(jd, 0.0, 0.0)
            current_planet_positions = {
                name: {"sidereal_longitude": round(pos.sidereal_longitude, 4), "sign": pos.sign}
                for name, pos in raw_pos.items()
            }
        except Exception:
            current_planet_positions = {}

    # ── Core analyses
    natal_yogas    = detect_natal_yogas(natal_chart)
    house_analysis = analyze_natal_houses(natal_chart)
    transit_data   = analyze_transits(natal_chart, current_planet_positions)
    dasha_analysis = analyze_dasha_period(natal_chart, current_dasha)

    maha  = current_dasha.get("maha_dasha", "?")
    antar = current_dasha.get("antardasha", "?") or "?"

    sat_transit = transit_data.get("Saturn", {})
    jup_transit = transit_data.get("Jupiter", {})
    sade_sati   = sat_transit.get("is_sade_sati", False)
    ashtama     = sat_transit.get("is_ashtama", False)
    kantak      = sat_transit.get("is_kantak", False)
    jup_good    = jup_transit.get("quality") == "Favorable"

    # ── Domain: Career & Status ──────────────────────────────────
    cs = 0; cp = []

    # H10 analysis
    h10_occ = [p for p, d in planets.items() if d.get("house") == 10]
    h10_benefic = [p for p in h10_occ if p in BENEFIC_PLANETS]
    h10_malefic = [p for p in h10_occ if p in MALEFIC_PLANETS]
    l10 = hl(10)
    l10_house = ph(l10)
    l10_dig = _planet_dignity(l10, ps(l10), pd(l10))

    if l10_house in (1,5,9,10,11):
        cs += 2
        cp.append(f"10th lord {l10} in H{l10_house} ({l10_dig['dignity']}) — strong career foundation; ambitions naturally materialize.")
    elif l10_house in (6,8,12):
        cs -= 1
        cp.append(f"10th lord {l10} in H{l10_house} — career through unconventional or service-oriented paths; effort required.")

    if h10_benefic:
        cs += 2
        cp.append(f"{', '.join(h10_benefic)} in 10th house — career blessed by benefic energy; recognition and advancement supported.")
    if h10_malefic:
        cp.append(f"{', '.join(h10_malefic)} in 10th house — strong drive and ambition; authority conflicts possible; persistence wins.")

    if maha in ("Jupiter","Sun","Saturn","Mercury") or antar in ("Jupiter","Sun","Mercury"):
        cs += 1
        cp.append(f"{maha} Mahadasha + {antar} Antardasha activates career, authority, and professional reputation.")

    if jup_good:
        cs += 1
        cp.append(f"Jupiter transiting H{jup_transit.get('from_moon_house')} from Moon — expansion and recognition in professional life.")

    if sade_sati:
        cs -= 2
        cp.append("Sade Sati active — career restructuring period. Foundations tested. Focus on integrity; what's built now lasts.")
    elif ashtama:
        cs -= 2
        cp.append("Ashtama Shani — significant career challenges; avoid job changes if possible; build resilience.")

    if any(y["name"] in ("Raj Yoga","Budha-Aditya Yoga","Sasa Yoga","Ruchaka Yoga") for y in natal_yogas):
        cs += 1
        yoga_names = [y["name"] for y in natal_yogas if y["name"] in ("Raj Yoga","Budha-Aditya Yoga","Sasa Yoga","Ruchaka Yoga")]
        cp.append(f"Natal {', '.join(yoga_names)} — long-term career elevation and authority are karmically promised.")

    # Varshphal overlay
    if varshphal_context:
        vp_career = varshphal_context.get("domains", {}).get("Career & Status", {})
        if vp_career.get("score", 0) >= 2:
            cs += 1; cp.append("Annual chart strongly supports career advancement this year.")
        muntha_h = varshphal_context.get("muntha", {}).get("annual_house", 0)
        if muntha_h == 10:
            cs += 2; cp.append("Muntha in annual H10 — an outstanding year for career peak.")

    # ── Domain: Finance & Wealth ─────────────────────────────────
    fs = 0; fp = []

    l2 = hl(2); l11 = hl(11)
    l2_dig = _planet_dignity(l2, ps(l2), pd(l2))
    l11_dig = _planet_dignity(l11, ps(l11), pd(l11))

    if ph(l2) in (1,2,5,9,10,11):
        fs += 2
        fp.append(f"2nd lord {l2} ({l2_dig['dignity']}) in H{ph(l2)} — strong wealth generation and family resources.")
    if ph(l11) in (1,2,5,9,10,11):
        fs += 1
        fp.append(f"11th lord {l11} in H{ph(l11)} — income and gains actively flowing.")

    h2_h11_planets = [p for p, d in planets.items() if d.get("house") in (2, 11)]
    h2_h11_benefic = [p for p in h2_h11_planets if p in BENEFIC_PLANETS]
    if h2_h11_benefic:
        fs += 2
        fp.append(f"{', '.join(h2_h11_benefic)} in wealth houses (H2/H11) — natural abundance and financial ease.")

    if any(y["name"] in ("Dhana Yoga (2L+11L)","Lakshmi Yoga") for y in natal_yogas):
        fs += 2
        fp.append("Natal Dhana/Lakshmi Yoga — wealth accumulation strongly supported over lifetime; periodic windfalls.")

    venus_dig = _planet_dignity("Venus", ps("Venus"), pd("Venus"))
    if venus_dig["is_strong"]:
        fs += 1
        fp.append(f"Venus {venus_dig['dignity']} in {ps('Venus')} — inherent financial magnetism and luxury.")

    if maha in ("Venus","Jupiter","Mercury") or antar in ("Venus","Jupiter","Moon"):
        fs += 1
        fp.append(f"{maha}–{antar} Dasha supports wealth themes.")

    if sade_sati:
        fs -= 1
        fp.append("Sade Sati: unexpected expenses or financial restructuring. Build reserves; avoid speculation.")
    if ashtama:
        fs -= 2
        fp.append("Ashtama Shani: significant financial caution required; minimize large expenditures.")

    if jup_good:
        fs += 1
        fp.append("Jupiter's favorable transit creates income and savings opportunities.")

    # ── Domain: Relationships & Marriage ─────────────────────────
    rs = 0; rp = []

    l7 = hl(7)
    l7_dig = _planet_dignity(l7, ps(l7), pd(l7))
    h7_occ = [p for p, d in planets.items() if d.get("house") == 7]

    if ph(l7) in (1,2,5,7,9,10,11):
        rs += 2
        rp.append(f"7th lord {l7} ({l7_dig['dignity']}) in H{ph(l7)} — partnerships and marriage supported.")
    elif ph(l7) in (6,8,12):
        rs -= 1
        rp.append(f"7th lord {l7} in H{ph(l7)} — relationship karma; requires patience and maturity.")

    ven_dig = _planet_dignity("Venus", ps("Venus"), pd("Venus"))
    jup_dig = _planet_dignity("Jupiter", ps("Jupiter"), pd("Jupiter"))
    if ven_dig["is_strong"]:
        rs += 1
        rp.append(f"Venus {ven_dig['dignity']} — strong magnetism, harmonious relationships, attractiveness.")
    if jup_dig["is_strong"]:
        rs += 1
        rp.append(f"Jupiter {jup_dig['dignity']} — wise, devoted, and blessed partnerships.")

    if any(p in BENEFIC_PLANETS for p in h7_occ):
        rs += 1
        rp.append(f"Benefic planet(s) {', '.join(p for p in h7_occ if p in BENEFIC_PLANETS)} in H7 — positive relationship environment.")

    if maha in ("Venus","Moon","Jupiter") or antar in ("Venus","Moon","Jupiter"):
        rs += 1
        rp.append(f"{maha}–{antar} Dasha activates love, marriage, and partnership themes.")

    if jup_good:
        rs += 1
        rp.append("Jupiter favorable — blessings in marriage, family, and important partnerships.")

    if sade_sati:
        rs -= 1
        rp.append("Sade Sati: emotional strain on relationships; conscious, patient communication is essential.")

    if ph("Saturn") == 7 and not _planet_dignity("Saturn", ps("Saturn"), pd("Saturn"))["is_strong"]:
        rs -= 1
        rp.append("Natal Saturn in H7 — relationship karma; delay possible, but maturity yields deep commitment.")

    # ── Domain: Health & Vitality ─────────────────────────────────
    hs = 2; hp = []

    l1 = hl(1)
    l1_dig = _planet_dignity(l1, ps(l1), pd(l1))
    h1_occ = [p for p, d in planets.items() if d.get("house") == 1]
    h6_occ = [p for p, d in planets.items() if d.get("house") == 6]

    if l1_dig["is_strong"]:
        hs += 1
        hp.append(f"Lagna lord {l1} {l1_dig['dignity']} — strong constitution and resilience.")
    elif l1_dig["is_weak"]:
        hs -= 1
        hp.append(f"Lagna lord {l1} debilitated — health sensitive; preventive care important.")

    if any(p in MALEFIC_PLANETS for p in h1_occ):
        hs -= 1
        hp.append(f"Malefic(s) {', '.join(p for p in h1_occ if p in MALEFIC_PLANETS)} in Lagna — health vigilance required.")

    if h6_occ:
        hp.append(f"Planets in H6: {', '.join(h6_occ)} — health themes activated; preventive and routine care is rewarded.")

    if ph("Moon") in (6,8,12):
        hs -= 1
        hp.append(f"Moon in H{ph('Moon')} natally — emotional and mental health sensitivity; stress management essential.")

    if sade_sati:
        hs -= 1
        hp.append("Sade Sati: fatigue, mental stress, and immune challenges. Rest, routine, and nature are medicine.")
    if ashtama:
        hs -= 2
        hp.append("Ashtama Shani: significant health vigilance required. Medical checkups essential; avoid surgery unless urgent.")

    if jup_good:
        hs += 1
        hp.append("Jupiter's favorable transit supports recovery, healing, and overall vitality.")

    if maha in ("Saturn","Mars","Rahu") or antar in ("Saturn","Mars","Rahu"):
        hs -= 1
        hp.append(f"{maha or antar} Dasha: physical demands increase; stress management and preventive care are essential.")
    elif maha in ("Jupiter","Venus") or antar in ("Jupiter","Venus","Moon"):
        hs += 1
        hp.append(f"{maha}–{antar} Dasha: vitality and healing energy amplified; good period for recovery.")

    # ── Domain: Spirituality & Growth ────────────────────────────
    ss = 0; sp = []

    h9_occ  = [p for p, d in planets.items() if d.get("house") == 9]
    h12_occ = [p for p, d in planets.items() if d.get("house") == 12]
    l9 = hl(9)
    l9_dig = _planet_dignity(l9, ps(l9), pd(l9))

    if l9_dig["is_strong"]:
        ss += 2
        sp.append(f"9th lord {l9} {l9_dig['dignity']} — strong dharmic instinct and spiritual fortune.")

    if any(p in ("Jupiter","Ketu") for p in h9_occ):
        ss += 1
        sp.append("Jupiter or Ketu in H9 — natural spiritual inclination, access to wisdom, and higher learning.")

    if ph("Ketu") in (9,12,4):
        ss += 1
        sp.append(f"Ketu in H{ph('Ketu')} — profound past-life spiritual merit; intuition and liberation are natural gifts.")

    if maha in ("Saturn","Ketu","Jupiter","Rahu"):
        ss += 1
        sp.append(f"{maha} Mahadasha — a period of deep introspection, karma resolution, and inner transformation.")
    if antar in ("Ketu","Jupiter","Saturn"):
        ss += 1
        sp.append(f"{antar} Antardasha activates wisdom, spiritual practice, and inner guidance.")
    if sade_sati:
        ss += 1
        sp.append("Sade Sati, while challenging materially, is a profound catalyst for spiritual awakening.")

    if any(y["name"] in ("Hamsa Yoga","Viparita Raj Yoga") for y in natal_yogas):
        ss += 1
        sp.append("Natal Hamsa/Viparita yoga — spiritual wisdom and dharmic purpose are deeply embedded in the chart.")

    # ── Remedies ──────────────────────────────────────────────────
    remedies = _suggest_remedies(maha, antar, sade_sati, ashtama, natal_yogas)

    # ── Overall Assessment ────────────────────────────────────────
    total = cs + fs + rs + hs + ss
    if total >= 12: overall = "Exceptional — a standout period. Multiple domains are strongly favored."
    elif total >= 8: overall = "Excellent — strong forward momentum across career, finance, and relationships."
    elif total >= 5: overall = "Favorable — positive trends dominate; focus delivers results."
    elif total >= 2: overall = "Mixed — opportunities and challenges in balance; selective action is key."
    elif total >= -2: overall = "Challenging — patience and persistence required; build internal strength."
    else: overall = "Demanding — a period of karmic reckoning; spiritual practice and remedies are vital."

    # ── Timing Highlights ─────────────────────────────────────────
    timing_notes = []
    maha_end   = current_dasha.get("maha_dasha_end", "")
    antar_end  = current_dasha.get("antardasha_end", "")
    antar_start = current_dasha.get("antardasha_start", "")
    if antar_start and antar_end:
        timing_notes.append(f"{antar} Antardasha active {antar_start} → {antar_end}: themes of {', '.join(PLANET_KARAKAS.get(antar,[])[:3])}.")
    if maha_end:
        timing_notes.append(f"{maha} Mahadasha runs until {maha_end}.")

    return {
        "prediction_date":    today.strftime("%Y-%m-%d"),
        "moon_sign":          moon_sign,
        "lagna":              lagna_sign,
        "overall_assessment": overall,

        "dasha": {
            "maha_dasha":  maha,
            "maha_period": f"{current_dasha.get('maha_dasha_start','')} to {current_dasha.get('maha_dasha_end','')}",
            "antardasha":  antar,
            "antar_period":f"{current_dasha.get('antardasha_start','')} to {current_dasha.get('antardasha_end','')}",
            "analysis":    dasha_analysis,
        },

        "transits": transit_data,

        "domains": {
            "Career & Status": {
                "rating": _score_label(cs), "score": cs,
                "insights": cp[:6],
                "summary": _career_summary(cs, maha, sade_sati, ashtama),
            },
            "Finance & Wealth": {
                "rating": _score_label(fs), "score": fs,
                "insights": fp[:6],
                "summary": _finance_summary(fs, maha, sade_sati),
            },
            "Relationships & Marriage": {
                "rating": _score_label(rs), "score": rs,
                "insights": rp[:6],
                "summary": _relationship_summary(rs, maha, sade_sati),
            },
            "Health & Vitality": {
                "rating": _score_label(hs), "score": hs,
                "insights": hp[:6],
                "summary": _health_summary(hs, sade_sati, ashtama),
            },
            "Spirituality & Growth": {
                "rating": _score_label(ss), "score": ss,
                "insights": sp[:5],
                "summary": _spiritual_summary(ss, maha, sade_sati),
            },
        },

        "natal_yogas": natal_yogas,
        "house_analysis": house_analysis,
        "remedies": remedies,
        "timing_highlights": timing_notes,
    }


# ── Domain Summary Helpers ──────────────────────────────────────────────────

def _career_summary(score, maha, sade_sati, ashtama):
    if ashtama:
        return "Career under significant pressure this period. Avoid risky moves; consolidate what you have."
    if sade_sati:
        return "Career restructuring likely. Foundations are tested — what survives will be more solid."
    if score >= 3:
        return "A strong period for career advancement, recognition, and increased authority."
    if score >= 1:
        return "Moderate career growth. Consistent effort and strategic positioning yield results."
    if score <= -1:
        return "Career patience required. Focus on skill-building and long-term positioning."
    return "Career on steady ground. Maintain momentum; avoid unnecessary risks."

def _finance_summary(score, maha, sade_sati):
    if sade_sati:
        return "Financial discipline is key. Reduce debt, build reserves, avoid speculation."
    if score >= 3:
        return "Excellent financial period. Multiple income streams and smart investments thrive."
    if score >= 1:
        return "Positive financial trajectory. Income grows with focused effort."
    if score <= -1:
        return "Financial caution advised. Budget carefully; delay major purchases."
    return "Stable finances. Save more than you spend; opportunities are building."

def _relationship_summary(score, maha, sade_sati):
    if sade_sati:
        return "Relationships require patience and honest communication. Don't take loved ones for granted."
    if score >= 3:
        return "Beautiful time for love, commitment, and deep partnership. Doors open."
    if score >= 1:
        return "Positive relationship energy. Nurture existing bonds and be open to meaningful connections."
    if score <= -1:
        return "Relationship karma active. Work through patterns consciously; growth is the purpose."
    return "Relationships are stable. Small gestures of care deepen existing bonds."

def _health_summary(score, sade_sati, ashtama):
    if ashtama:
        return "Health vigilance essential. Proactive checkups, stress reduction, and adequate rest are priorities."
    if sade_sati:
        return "Manage stress and fatigue proactively. Routine, nature, and rest are your best medicine."
    if score >= 3:
        return "Strong vitality. Capitalize on good health energy for physical goals."
    if score >= 1:
        return "Good health baseline. Maintain consistent routines and preventive care."
    if score <= -1:
        return "Health deserves extra attention. Don't ignore small symptoms; preventive care now saves later."
    return "Health is stable. Maintain wellness routines and adequate rest."

def _spiritual_summary(score, maha, sade_sati):
    if sade_sati:
        return "A profound period for spiritual acceleration. The outer challenges are the inner teacher."
    if score >= 3:
        return "A deeply auspicious time for spiritual practice, wisdom, and inner transformation."
    if score >= 1:
        return "Growth and wisdom are accessible. Seek good teachings and meaningful practices."
    if score <= 0:
        return "Build a daily spiritual anchor — even 10 minutes of stillness creates cumulative transformation."
    return "Spiritual growth unfolds quietly. Trust the process."


# ── Today's Transit Fetcher ─────────────────────────────────────────────────

def get_today_transits(ayanamsa: str = "lahiri") -> dict:
    from .ephemeris import compute_all_positions, gregorian_to_jd
    now = datetime.utcnow()
    jd  = gregorian_to_jd(now.year, now.month, now.day, now.hour + now.minute/60 + now.second/3600)
    positions, _, _ = compute_all_positions(jd, 0.0, 0.0, ayanamsa)
    return {
        name: {
            "sidereal_longitude": round(pos.sidereal_longitude, 4),
            "sign": pos.sign,
            "degree_in_sign": round(pos.degree_in_sign, 4),
            "nakshatra": pos.nakshatra,
            "is_retrograde": pos.is_retrograde,
        }
        for name, pos in positions.items()
    }
