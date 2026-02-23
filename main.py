"""
Nakshatra Astrology Platform — FastAPI Backend
==============================================
Endpoints:
  POST /api/kundali          — Generate birth chart
  POST /api/kundali/unknown  — Unknown birth time (3 variants)
  POST /api/panchang         — Daily panchang for location
  POST /api/matchmaker       — Compatibility / Guna matching
  POST /api/pdf              — Generate PDF report
  GET  /api/health           — Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import io
import traceback

from kundali_engine import generate_kundali, generate_kundali_unknown_time
from kundali_engine.core.panchang import compute_panchang
from kundali_engine.core.ephemeris import gregorian_to_jd
from matchmaker import compute_compatibility
from pdf_report import generate_pdf_report

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Nakshatra Astrology API",
    version="1.0.0",
    description="Vedic astrology calculation engine powered by Swiss Ephemeris algorithms",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production: restrict to your domain
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ────────────────────────────────────────────

class BirthData(BaseModel):
    year: int = Field(..., ge=1800, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(12, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    second: int = Field(0, ge=0, le=59)
    timezone_offset: float = Field(0.0, ge=-12, le=14)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    house_system: str = Field("whole_sign", pattern="^(whole_sign|placidus|equal|koch)$")
    ayanamsa: str = Field("lahiri", pattern="^(lahiri|raman|kp|fagan)$")


class UnknownTimeBirthData(BaseModel):
    year: int
    month: int
    day: int
    timezone_offset: float
    latitude: float
    longitude: float
    ayanamsa: str = "lahiri"


class MatchmakerRequest(BaseModel):
    person1: BirthData
    person2: BirthData


class PanchangRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int = 6
    minute: int = 0
    timezone_offset: float = 0.0
    latitude: float
    longitude: float
    ayanamsa: str = "lahiri"


class PDFRequest(BaseModel):
    chart: dict
    name: Optional[str] = "Native"


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Nakshatra Astrology API", "version": "1.0.0"}


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
        jd = gregorian_to_jd(data.year, data.month, data.day,
                             data.hour + data.minute/60 - data.timezone_offset)
        panchang = compute_panchang(jd, data.latitude, data.longitude, data.ayanamsa)
        return {"success": True, "panchang": panchang}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/matchmaker")
def matchmaker_endpoint(data: MatchmakerRequest):
    try:
        chart1 = generate_kundali(
            year=data.person1.year, month=data.person1.month, day=data.person1.day,
            hour=data.person1.hour, minute=data.person1.minute,
            timezone_offset=data.person1.timezone_offset,
            latitude=data.person1.latitude, longitude=data.person1.longitude,
            ayanamsa=data.person1.ayanamsa,
        )
        chart2 = generate_kundali(
            year=data.person2.year, month=data.person2.month, day=data.person2.day,
            hour=data.person2.hour, minute=data.person2.minute,
            timezone_offset=data.person2.timezone_offset,
            latitude=data.person2.latitude, longitude=data.person2.longitude,
            ayanamsa=data.person2.ayanamsa,
        )
        compatibility = compute_compatibility(chart1, chart2)
        return {"success": True, "compatibility": compatibility}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/pdf")
def pdf_endpoint(data: PDFRequest):
    try:
        pdf_bytes = generate_pdf_report(data.chart, data.name)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=kundali_{data.name}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
