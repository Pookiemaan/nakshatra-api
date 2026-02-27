"""
Nakshatra Astrology Platform — FastAPI Backend v2.0
====================================================
Endpoints:
  POST /api/kundali          — Birth chart + dasha
  POST /api/kundali/unknown  — Unknown birth time (3 variants)
  POST /api/panchang         — Daily panchang
  POST /api/matchmaker       — Compatibility / Guna matching
  POST /api/varshphal        — Annual Solar Return (Varshphal / Tajika)
  POST /api/predictions      — Natal + transit predictions
  POST /api/pdf              — PDF report
  GET  /api/health           — Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import io
import traceback

from kundali_engine import generate_kundali, generate_kundali_unknown_time
from kundali_engine.core.panchang import compute_panchang
from kundali_engine.core.ephemeris import gregorian_to_jd
from kundali_engine.core.varshphal import generate_varshphal
from kundali_engine.core.predictions import generate_predictions, get_today_transits
from matchmaker import compute_compatibility
from pdf_report import generate_pdf_report

app = FastAPI(
    title="Nakshatra Astrology API",
    version="2.0.0",
    description="Complete Vedic astrology engine: Kundali, Varshphal, Predictions, Panchang, Matchmaking",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ─────────────────────────────────────────────

class BirthData(BaseModel):
    year:            int   = Field(..., ge=1800, le=2100)
    month:           int   = Field(..., ge=1,    le=12)
    day:             int   = Field(..., ge=1,    le=31)
    hour:            int   = Field(12,  ge=0,    le=23)
    minute:          int   = Field(0,   ge=0,    le=59)
    second:          int   = Field(0,   ge=0,    le=59)
    timezone_offset: float = Field(0.0, ge=-12,  le=14)
    latitude:        float = Field(..., ge=-90,  le=90)
    longitude:       float = Field(..., ge=-180, le=180)
    house_system:    str   = Field("whole_sign",
                                   pattern="^(whole_sign|placidus|equal|koch)$")
    ayanamsa:        str   = Field("lahiri",
                                   pattern="^(lahiri|raman|kp|fagan)$")


class UnknownTimeBirthData(BaseModel):
    year:            int
    month:           int
    day:             int
    timezone_offset: float
    latitude:        float
    longitude:       float
    ayanamsa:        str = "lahiri"


class MatchmakerRequest(BaseModel):
    person1: BirthData
    person2: BirthData


class PanchangRequest(BaseModel):
    year:            int
    month:           int
    day:             int
    hour:            int   = 6
    minute:          int   = 0
    timezone_offset: float = 0.0
    latitude:        float
    longitude:       float
    ayanamsa:        str   = "lahiri"


class VarshphalRequest(BaseModel):
    year:            int   = Field(..., ge=1800, le=2100)
    month:           int   = Field(..., ge=1,    le=12)
    day:             int   = Field(..., ge=1,    le=31)
    hour:            int   = Field(12,  ge=0,    le=23)
    minute:          int   = Field(0,   ge=0,    le=59)
    second:          int   = Field(0,   ge=0,    le=59)
    timezone_offset: float = Field(0.0, ge=-12,  le=14)
    latitude:        float = Field(..., ge=-90,  le=90)
    longitude:       float = Field(..., ge=-180, le=180)
    ayanamsa:        str   = Field("lahiri",
                                   pattern="^(lahiri|raman|kp|fagan)$")
    target_year:     int   = Field(..., ge=1900, le=2100)
    today_date:      Optional[str] = Field(None,
                          description="Current date YYYY-MM-DD for Mudda Dasha")


class PredictionsRequest(BaseModel):
    year:            int   = Field(..., ge=1800, le=2100)
    month:           int   = Field(..., ge=1,    le=12)
    day:             int   = Field(..., ge=1,    le=31)
    hour:            int   = Field(12,  ge=0,    le=23)
    minute:          int   = Field(0,   ge=0,    le=59)
    second:          int   = Field(0,   ge=0,    le=59)
    timezone_offset: float = Field(0.0, ge=-12,  le=14)
    latitude:        float = Field(..., ge=-90,  le=90)
    longitude:       float = Field(..., ge=-180, le=180)
    ayanamsa:        str   = Field("lahiri",
                                   pattern="^(lahiri|raman|kp|fagan)$")
    today_date:      Optional[str] = Field(None,
                          description="Date for analysis YYYY-MM-DD")


class PDFRequest(BaseModel):
    chart: dict
    name:  Optional[str] = "Native"


# ── Utilities ──────────────────────────────────────────────────

def _parse_date(date_str: Optional[str]) -> datetime:
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now()


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Nakshatra Astrology API",
        "version": "2.0.0",
        "endpoints": [
            "POST /api/kundali",
            "POST /api/kundali/unknown",
            "POST /api/panchang",
            "POST /api/matchmaker",
            "POST /api/varshphal",
            "POST /api/predictions",
            "POST /api/pdf",
        ],
    }


@app.post("/api/kundali")
def kundali_endpoint(data: BirthData):
    try:
        chart = generate_kundali(
            year=data.year, month=data.month, day=data.day,
            hour=data.hour, minute=data.minute, second=data.second,
            timezone_offset=data.timezone_offset,
            latitude=data.latitude, longitude=data.longitude,
            house_system=data.house_system,
            ayanamsa=data.ayanamsa,
        )
        return {"success": True, "chart": chart}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/kundali/unknown")
def kundali_unknown_endpoint(data: UnknownTimeBirthData):
    try:
        result = generate_kundali_unknown_time(
            year=data.year, month=data.month, day=data.day,
            latitude=data.latitude, longitude=data.longitude,
            timezone_offset=data.timezone_offset,
            ayanamsa=data.ayanamsa,
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/panchang")
def panchang_endpoint(data: PanchangRequest):
    try:
        jd = gregorian_to_jd(
            data.year, data.month, data.day,
            data.hour + data.minute / 60 - data.timezone_offset,
        )
        panchang = compute_panchang(jd, data.latitude, data.longitude, data.ayanamsa)
        return {"success": True, "panchang": panchang}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/matchmaker")
def matchmaker_endpoint(data: MatchmakerRequest):
    try:
        def _chart(p):
            return generate_kundali(
                year=p.year, month=p.month, day=p.day,
                hour=p.hour, minute=p.minute,
                timezone_offset=p.timezone_offset,
                latitude=p.latitude, longitude=p.longitude,
                ayanamsa=p.ayanamsa,
            )
        compatibility = compute_compatibility(_chart(data.person1), _chart(data.person2))
        return {"success": True, "compatibility": compatibility}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/varshphal")
def varshphal_endpoint(data: VarshphalRequest):
    """
    Generate a complete Varshphal (Solar Return / Annual Chart).

    Returns:
    • Solar return exact moment (binary-searched to <1 minute precision)
    • Full annual chart — all 9 planets in annual houses
    • Muntha — progressed ascendant with house interpretation
    • Varshesh — year lord with Pancha-Vargiya Bala strength
    • Pancha-Vargiya Bala — 5-fold strength for every annual planet
    • Tajika yogas — Ithasala (applying), Ishrafa (separating), Kambula
    • 16 Sahams (Arabic sensitive points)
    • Mudda Dasha — 360-day compressed Vimshottari timing
    • Domain predictions for Career, Finance, Relationships, Health, Spirituality
    """
    try:
        today = _parse_date(data.today_date)

        natal_chart = generate_kundali(
            year=data.year, month=data.month, day=data.day,
            hour=data.hour, minute=data.minute, second=data.second,
            timezone_offset=data.timezone_offset,
            latitude=data.latitude, longitude=data.longitude,
            house_system="whole_sign",
            ayanamsa=data.ayanamsa,
        )

        varshphal = generate_varshphal(
            natal_chart=natal_chart,
            target_year=data.target_year,
            birth_lat=data.latitude,
            birth_lon=data.longitude,
            birth_year=data.year,
            ayanamsa=data.ayanamsa,
            today=today,
        )

        return {
            "success": True,
            "varshphal": varshphal,
            "natal_chart": natal_chart,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Varshphal error: {str(e)}\n{traceback.format_exc()}",
        )


@app.post("/api/predictions")
def predictions_endpoint(data: PredictionsRequest):
    """
    Generate comprehensive natal + transit predictions.

    Returns:
    • Overall assessment
    • Vimshottari Dasha analysis (Mahadasha + Antardasha themes & quality)
    • Current transit analysis — Saturn Sade Sati/Ashtama, Jupiter, Rahu, Ketu, Mars
    • Domain forecasts: Career, Finance, Relationships, Health, Spirituality
    • Natal yoga detection (Raj, Dhana, Gaja-Kesari, Pancha-Mahapurusha, etc.)
    • House-by-house natal strength analysis (all 12 houses)
    • Personalised Vedic remedies (mantra, gem, charity, practice)
    """
    try:
        today = _parse_date(data.today_date)

        natal_chart = generate_kundali(
            year=data.year, month=data.month, day=data.day,
            hour=data.hour, minute=data.minute, second=data.second,
            timezone_offset=data.timezone_offset,
            latitude=data.latitude, longitude=data.longitude,
            house_system="whole_sign",
            ayanamsa=data.ayanamsa,
        )

        current_transits = get_today_transits(data.ayanamsa)

        predictions = generate_predictions(
            natal_chart=natal_chart,
            current_dasha=natal_chart.get("dasha", {}).get("current", {}),
            today=today,
            current_planet_positions=current_transits,
        )

        return {
            "success": True,
            "predictions": predictions,
            "natal_chart": natal_chart,
            "current_transits": current_transits,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Predictions error: {str(e)}\n{traceback.format_exc()}",
        )


@app.post("/api/pdf")
def pdf_endpoint(data: PDFRequest):
    try:
        pdf_bytes = generate_pdf_report(data.chart, data.name)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=kundali_{data.name}.pdf"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
