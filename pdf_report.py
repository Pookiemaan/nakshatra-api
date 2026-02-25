"""
pdf_report.py
=============
Generates a printable Kundali PDF report.
Uses ReportLab for PDF generation.

Install: pip install reportlab
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime

# ── Color palette ──────────────────────────────────────────────
VOID      = HexColor("#0B0B0F")
PARCHMENT = HexColor("#F5F0E8")
GOLD      = HexColor("#C9A96E")
SURFACE   = HexColor("#1E1C28")
MUTED     = HexColor("#6E6A7C")
VIOLET    = HexColor("#7B6FA0")
GREEN     = HexColor("#6DBF8E")
WHITE     = HexColor("#FFFFFF")


def generate_pdf_report(chart: dict, name: str = "Native") -> bytes:
    """
    Generate a complete Kundali PDF report.
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Kundali Report — {name}",
        author="Nakshatra Astrology Platform",
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Custom styles ──────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"],
        fontSize=28, fontName="Helvetica",
        textColor=VOID, alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica",
        textColor=MUTED, alignment=TA_CENTER,
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=13, fontName="Helvetica-Bold",
        textColor=VOID, spaceBefore=16, spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        textColor=VOID, spaceAfter=4,
        leading=14,
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold",
        textColor=MUTED,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["Normal"],
        fontSize=7, fontName="Helvetica-Oblique",
        textColor=MUTED, alignment=TA_CENTER,
        spaceBefore=20,
    )

    def gold_bar(text):
        return Table(
            [[Paragraph(text, ParagraphStyle("GoldBar", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica-Bold",
                textColor=WHITE, alignment=TA_LEFT))]],
            colWidths=[17*cm],
            style=TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), VOID),
                ("TOPPADDING",    (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                ("LEFTPADDING",   (0,0), (-1,-1), 12),
                ("RIGHTPADDING",  (0,0), (-1,-1), 12),
            ])
        )

    # ── HEADER ────────────────────────────────────────────────
    story.append(Paragraph("☽  NAKSHATRA", title_style))
    story.append(Paragraph("Vedic Astrology Platform · Kundali Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 0.4*cm))

    # ── BIRTH DETAILS ─────────────────────────────────────────
    story.append(gold_bar("BIRTH DETAILS"))
    story.append(Spacer(1, 0.3*cm))

    meta = chart.get("meta", {}).get("input", {})
    lagna = chart.get("lagna", {})
    details_data = [
        ["Name", name, "Date", meta.get("date", "—")],
        ["Lagna (Ascendant)", lagna.get("sign", "—"), "Time", meta.get("time", "—")],
        ["Moon Sign", chart.get("moon_sign", "—"), "Timezone", f"UTC{meta.get('timezone_offset', 0):+.1f}"],
        ["Moon Nakshatra", f"{chart.get('moon_nakshatra','—')} (Pada {chart.get('moon_nakshatra_pada','—')})",
         "Latitude", str(meta.get("latitude","—"))],
        ["Ayanamsa", meta.get("ayanamsa","Lahiri").title(),
         "Longitude", str(meta.get("longitude","—"))],
        ["House System", meta.get("house_system","whole_sign").replace("_"," ").title(),
         "Julian Day", str(chart.get("meta",{}).get("julian_day","—"))],
    ]

    det_table = Table(details_data, colWidths=[4*cm, 5*cm, 3.5*cm, 4.5*cm])
    det_table.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",    (2,0), (2,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0,0), (0,-1), MUTED),
        ("TEXTCOLOR",   (2,0), (2,-1), MUTED),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [HexColor("#FAFAFA"), WHITE]),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#E0E0E0")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 0.5*cm))

    # ── PLANET POSITIONS ──────────────────────────────────────
    story.append(gold_bar("PLANETARY POSITIONS  (Sidereal · Lahiri Ayanamsa)"))
    story.append(Spacer(1, 0.3*cm))

    planet_header = [["Planet", "Sign", "Degree", "Nakshatra", "Pada", "House", "Retro"]]
    planet_rows = []
    for pname, pdata in chart.get("planets", {}).items():
        planet_rows.append([
            pname,
            pdata.get("sign", "—"),
            pdata.get("degree_formatted", "—"),
            pdata.get("nakshatra", "—"),
            str(pdata.get("nakshatra_pada", "—")),
            f"H{pdata.get('house', '—')}",
            "℞" if pdata.get("is_retrograde") else "",
        ])

    planet_table = Table(
        planet_header + planet_rows,
        colWidths=[2.8*cm, 3.2*cm, 2.8*cm, 3.8*cm, 1.2*cm, 1.5*cm, 1.2*cm]
    )
    planet_table.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("BACKGROUND",  (0,0), (-1,0),  SURFACE),
        ("TEXTCOLOR",   (0,0), (-1,0),  GOLD),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[HexColor("#FAFAFA"), WHITE]),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("ALIGN",       (4,0), (4,-1),  "CENTER"),
        ("ALIGN",       (5,0), (5,-1),  "CENTER"),
        ("ALIGN",       (6,0), (6,-1),  "CENTER"),
    ]))
    story.append(planet_table)
    story.append(Spacer(1, 0.5*cm))

    # ── PANCHANG ──────────────────────────────────────────────
    panchang = chart.get("panchang", {})
    if panchang:
        story.append(gold_bar("PANCHANG"))
        story.append(Spacer(1, 0.3*cm))
        tithi   = panchang.get("tithi", {})
        nak     = panchang.get("nakshatra", {})
        rk      = panchang.get("rahu_kala", {})
        p_data = [
            ["Vara (Day)", panchang.get("vara", "—"),
             "Sunrise (UTC)", panchang.get("sunrise", "—")],
            ["Tithi", f"{tithi.get('name','—')} · {tithi.get('paksha','—')} Paksha",
             "Sunset (UTC)", panchang.get("sunset", "—")],
            ["Nakshatra", f"{nak.get('name','—')} · Pada {nak.get('pada','—')}",
             "Rahu Kala", f"{rk.get('start','—')} – {rk.get('end','—')}"],
            ["Yoga", panchang.get("yoga",{}).get("name","—"),
             "Karana", panchang.get("karana",{}).get("name","—")],
        ]
        p_table = Table(p_data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
        p_table.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
            ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",    (2,0), (2,-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8.5),
            ("TEXTCOLOR",   (0,0), (0,-1), MUTED),
            ("TEXTCOLOR",   (2,0), (2,-1), MUTED),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[HexColor("#FAFAFA"), WHITE]),
            ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(p_table)
        story.append(Spacer(1, 0.5*cm))

    # ── DASHA ─────────────────────────────────────────────────
    dasha = chart.get("dasha", {})
    if dasha:
        story.append(gold_bar("VIMSHOTTARI DASHA TIMELINE"))
        story.append(Spacer(1, 0.3*cm))

        cur = dasha.get("current", {})
        if cur and cur.get("maha_dasha"):
            story.append(Paragraph(
                f"<b>Active Maha Dasha:</b> {cur.get('maha_dasha','—')} "
                f"({cur.get('maha_dasha_start','—')} → {cur.get('maha_dasha_end','—')})",
                body_style
            ))
            if cur.get("antardasha"):
                story.append(Paragraph(
                    f"<b>Antardasha (Bhukti):</b> {cur.get('antardasha','—')} "
                    f"({cur.get('antardasha_start','—')} → {cur.get('antardasha_end','—')})",
                    body_style
                ))
            story.append(Spacer(1, 0.2*cm))

        dasha_header = [["Maha Dasha Lord", "Start Date", "End Date", "Duration (yrs)"]]
        dasha_rows = [
            [p.get("lord","—"), p.get("start","—"), p.get("end","—"),
             str(p.get("duration_years","—"))]
            for p in dasha.get("all_periods", [])
        ]

        d_table = Table(dasha_header + dasha_rows, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        d_table.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",    (0,0), (-1,-1), 8.5),
            ("BACKGROUND",  (0,0), (-1,0),  SURFACE),
            ("TEXTCOLOR",   (0,0), (-1,0),  GOLD),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[HexColor("#FAFAFA"), WHITE]),
            ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(d_table)
        story.append(Spacer(1, 0.5*cm))

    # ── DIVISIONAL CHARTS ─────────────────────────────────────
    div_charts = chart.get("divisional_charts", {})
    if div_charts:
        story.append(gold_bar("DIVISIONAL CHARTS"))
        story.append(Spacer(1, 0.3*cm))
        for div_name, div_data in div_charts.items():
            story.append(Paragraph(f"{div_name} Chart", section_style))
            div_header = [["Planet", "Sign", "Degree"]]
            div_rows = [[p, d.get("sign","—"), f"{d.get('degree',0):.2f}°"]
                        for p, d in div_data.items()]
            dv_table = Table(div_header + div_rows, colWidths=[5*cm, 6*cm, 6*cm])
            dv_table.setStyle(TableStyle([
                ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
                ("FONTSIZE",    (0,0), (-1,-1), 8.5),
                ("BACKGROUND",  (0,0), (-1,0),  HexColor("#E8E4DC")),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[HexColor("#FAFAFA"), WHITE]),
                ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
                ("TOPPADDING",  (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LEFTPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(dv_table)
            story.append(Spacer(1, 0.3*cm))

    # ── FOOTER DISCLAIMER ─────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Paragraph(
        f"Generated by Nakshatra Astrology Platform · {datetime.now().strftime('%d %B %Y')} · "
        "pookiemaan.github.io/nakshatra-jyotish",
        disclaimer_style
    ))
    story.append(Paragraph(
        "⚠ AI-Generated Report Disclaimer: This report is produced algorithmically for informational "
        "purposes only. It does not constitute professional astrological advice. Calculations use "
        "VSOP87 series algorithms. Consult a qualified Jyotish practitioner for personal guidance.",
        disclaimer_style
    ))

    # ── BUILD PDF ─────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
