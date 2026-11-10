"""Generate the comprehensive EstateIQ Hackathon Team Master Briefing PDF.
Designed for BPUT Hackathon 2026.
Covers: Algorithm Deep-Dive, Mathematical Time & Space Complexity Derivation,
Slide Deck Corrections, Live Hardware Demo Guide, and Judge Defense Matrix.
"""
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT_PDF = ROOT / "output/pdf/estateiq_hackathon_team_master_guide.pdf"
FIG_DIR = ROOT / "research/ieee/figures"
SLIDE_ASSETS_DIR = ROOT / "output/presentation/algorithm_metrics"

# Register TrueType fonts if available, otherwise fallback cleanly
try:
    pdfmetrics.registerFont(TTFont('Times', 'C:/Windows/Fonts/times.ttf'))
    pdfmetrics.registerFont(TTFont('Times-Bold', 'C:/Windows/Fonts/timesbd.ttf'))
    pdfmetrics.registerFont(TTFont('Times-Italic', 'C:/Windows/Fonts/timesi.ttf'))
    pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
    FONT_HEAD = 'Arial-Bold'
    FONT_BODY = 'Times'
    FONT_BODY_BOLD = 'Times-Bold'
    FONT_BODY_ITALIC = 'Times-Italic'
    FONT_SANS = 'Arial'
except Exception:
    FONT_HEAD = 'Helvetica-Bold'
    FONT_BODY = 'Times-Roman'
    FONT_BODY_BOLD = 'Times-Bold'
    FONT_BODY_ITALIC = 'Times-Italic'
    FONT_SANS = 'Helvetica'


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        w, h = letter

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.setFont(FONT_HEAD, 8)
            self.setFillColor(colors.HexColor('#065f46'))
            self.drawString(45, h - 28, "EstateIQ-DIF — BPUT Hackathon 2026 Master Team Briefing")
            self.setFont(FONT_BODY_ITALIC, 8)
            self.setFillColor(colors.HexColor('#64748b'))
            self.drawRightString(w - 45, h - 28, "Algorithm, Metrology & Judge Defense Guide")

            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.5)
            self.line(45, h - 32, w - 45, h - 32)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(45, 36, w - 45, 36)

        self.setFont(FONT_HEAD, 8)
        self.setFillColor(colors.HexColor('#047857'))
        self.drawString(45, 24, "EstateIQ: Decision Intelligence for Sustainable Campuses")

        self.setFont(FONT_SANS, 8)
        self.setFillColor(colors.HexColor('#64748b'))
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(w - 45, 24, page_str)

        self.restoreState()


def build_team_guide_pdf():
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=42,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName=FONT_HEAD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#064e3b'),
        alignment=TA_LEFT,
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        fontName=FONT_SANS,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#047857'),
        alignment=TA_LEFT,
        spaceAfter=8
    )
    meta_box_style = ParagraphStyle(
        'MetaBox',
        fontName=FONT_SANS,
        fontSize=8.0,
        leading=11.2,
        textColor=colors.HexColor('#334155')
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        fontName=FONT_HEAD,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#065f46'),
        spaceBefore=0,
        spaceAfter=4,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        fontName=FONT_HEAD,
        fontSize=9.8,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        fontName=FONT_BODY,
        fontSize=8.8,
        leading=12.2,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_JUSTIFY,
        spaceAfter=4
    )
    callout_style = ParagraphStyle(
        'Callout_Text',
        fontName=FONT_SANS,
        fontSize=8.3,
        leading=11.5,
        textColor=colors.HexColor('#0f172a')
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName=FONT_SANS,
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor('#1e293b')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName=FONT_HEAD,
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor('#0f172a')
    )
    table_head_style = ParagraphStyle(
        'TableHead',
        fontName=FONT_HEAD,
        fontSize=8.2,
        leading=10.5,
        textColor=colors.white
    )
    script_speaker = ParagraphStyle(
        'ScriptSpeaker',
        fontName=FONT_HEAD,
        fontSize=8.8,
        leading=11.5,
        textColor=colors.HexColor('#047857'),
        spaceBefore=4,
        spaceAfter=1,
        keepWithNext=True
    )
    script_dialogue = ParagraphStyle(
        'ScriptDialogue',
        fontName=FONT_BODY_ITALIC,
        fontSize=8.5,
        leading=11.8,
        textColor=colors.HexColor('#334155'),
        leftIndent=10,
        spaceAfter=4
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE, META, EXECUTIVE OVERVIEW & PRESENTATION SCRIPT
    # =========================================================================
    story.append(Paragraph("EstateIQ-DIF — Hackathon Team Master Briefing", title_style))
    story.append(Paragraph("<b>BPUT HACKATHON 2026:</b> Algorithm Deep-Dive, Complexity Analysis, Presentation Pitch & Live Hardware Protocol", subtitle_style))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>Project:</b> EstateIQ Decision Intelligence (DIF)<br/><b>Hardware:</b> ESP32 NodeMCU + PZEM + Sonar + Flow + Gas", meta_box_style),
            Paragraph("<b>Target Event:</b> BPUT Hackathon 2026<br/><b>Repository:</b> <code>github.com/estateiq/model</code>", meta_box_style),
            Paragraph("<b>Date:</b> November 2026<br/><b>Status:</b> Fully Synchronized (218 Tests Pass)", meta_box_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[180, 180, 162])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#86efac')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bbf7d0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Executive Overview & The 60-Second Hackathon Elevator Pitch", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))
    
    pitch_text = (
        "<b>The Fundamental Problem:</b> Commercial campuses face two severe bottlenecks in facility operations. "
        "First, static rule thresholds (e.g. 'flag if power &gt; 50 kW') fail completely because they conflate normal diurnal rhythms with faults: "
        "50 kW on a Wednesday afternoon is normal class activity, but 50 kW at 2:00 AM on Sunday is a catastrophic chiller leak. "
        "Second, continuous high-frequency IoT streaming over-saturates Wi-Fi networks and exhausts gateway power. "
        "<br/><br/>"
        "<b>The EstateIQ-DIF Solution:</b> We built the <i>EstateIQ Decision Intelligence Framework (EstateIQ-DIF)</i>. "
        "It decouples 2.0-second local edge metrology from a dynamic, 7-day rolling seasonal baseline (672 quarter-hour slots) "
        "using robust Median Absolute Deviation (MAD) bounds. An <b>O(1) fast-path filter</b> approves 95% of nominal readings in &lt;2 ms. "
        "When anomalies occur, <b>convex evidence fusion</b> (80% residual + 20% multi-sensor context) and a <b>temporal persistence gate (n &ge; 2)</b> "
        "suppress 86.7% of false alarms from transient motor inrushes, achieving <b>0 false alarms</b> in holdout testing. "
        "Simultaneously, our <b>adaptive reporting cadence</b> cuts network transmission volume by <b>66.7%</b>."
    )
    
    t_pitch = Table([[Paragraph(pitch_text, callout_style)]], colWidths=[522])
    t_pitch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#047857')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_pitch)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Team Role Assignments & 3-Minute Presentation Delivery Flow", h2_style))
    story.append(Paragraph("<b>Speaker 1 — Problem & Vision Lead (0:00 - 0:50):</b>", script_speaker))
    story.append(Paragraph(
        "\"Respected judges, every university and commercial facility suffers from silent resource leaks—unnoticed water overflows, "
        "nighttime HVAC runaways, and unmonitored waste bins. Traditional BMS systems flood operators with false alarms because they rely "
        "on fixed static thresholds. Today, we present EstateIQ: an end-to-end Decision Intelligence Framework powered by real edge hardware "
        "and adaptive machine learning that eliminates 86.7% of false alarms while cutting IoT network traffic by 66.7%.\"",
        script_dialogue
    ))

    story.append(Paragraph("<b>Speaker 2 — Algorithm & AI Lead (0:50 - 1:50):</b>", script_speaker))
    story.append(Paragraph(
        "\"At the heart of EstateIQ is our DIF Engine. Instead of rigid cutoffs, we construct a 7-day seasonal profile across 672 weekly "
        "quarter-hour slots using the non-parametric Median and Median Absolute Deviation (MAD). Nominal readings exit in under 2 ms via an O(1) "
        "fast path. For abnormal deviations, we perform convex evidence fusion—combining statistical residuals with operational domain rules—and "
        "pass the score through a 2-interval temporal persistence filter. This guarantees that short-duration motor inrush surges never trigger a panic alert. "
        "Furthermore, our AI Assistant is strictly grounded in live telemetry evidence, computing the real Cost of Inaction at ₹9.50 per kWh.\"",
        script_dialogue
    ))

    story.append(Paragraph("<b>Hardware Lead — Live Sensor Demo (1:50 - 3:00):</b>", script_speaker))
    story.append(Paragraph(
        "\"Here on the table is our physical ESP32 gateway, running FreeRTOS with Modbus RTU electrical submetering, dual ultrasonic sonar, "
        "and water flow pulse interrupts. Right now, as I raise an obstruction above this ultrasonic sensor, watch the live dashboard: "
        "the edge firmware immediately detects a 3-centimeter delta, shifts cadence from 15-minute nominal to 5-minute alert, and dispatches "
        "a verified anomaly packet to our FastAPI backend in sub-second time without missing a beat.\"",
        script_dialogue
    ))

    # Clean Page Break -> Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: STEP-BY-STEP ALGORITHM MECHANICS & ARCHITECTURE FIGURE
    # =========================================================================
    story.append(Paragraph("2. Deep-Dive: How EstateIQ-DIF Detects Anomalies (End-to-End)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "EstateIQ-DIF operates through a seven-phase deterministic pipeline designed to provide mathematical rigor, "
        "explainable auditability, and edge computational feasibility without black-box opacity.",
        body_style
    ))

    stages_data = [
        [Paragraph("Pipeline Stage", table_head_style), Paragraph("Mathematical / Engineering Mechanism", table_head_style), Paragraph("Operational Impact", table_head_style)],
        [
            Paragraph("<b>1. Multi-Modal Edge Metrology</b>", table_cell_bold),
            Paragraph("PZEM-004T (UART2 9600 baud), Dual Sonar (AJ-SR04M & HC-SR04) with 3-sample median filter, ZJ-S201 turbine hardware pulse interrupts (450 pulses/L).", table_cell_style),
            Paragraph("Captures true physical telemetry directly on ESP32 in a 2.0s non-blocking loop.", table_cell_style)
        ],
        [
            Paragraph("<b>2. 7-Day Seasonal Baseline</b>", table_cell_bold),
            Paragraph("Divides the week into <b>672 quarter-hour intervals</b> (7 &times; 96). Computes group median &mu;&#771;<sub>b,s</sub> and MAD dispersion &sigma;<sub>MAD</sub> = 1.4826 &times; median(|y<sub>i</sub> - &mu;&#771;|).", table_cell_style),
            Paragraph("Replaces brittle static limits with diurnal occupancy rhythms. Achieves <b>1.59 kWh MAE</b> (R&sup2; = 0.9875).", table_cell_style)
        ],
        [
            Paragraph("<b>3. O(1) Fast-Path Filter</b>", table_cell_bold),
            Paragraph("Computes percentage deviation d<sub>t</sub> and normalized residual z<sub>t</sub> = (y<sub>t</sub> - &mu;&#771;) / &sigma;. If |d<sub>t</sub>| &lt; 15% and |z<sub>t</sub>| &lt; 1.875, exit immediately.", table_cell_style),
            Paragraph("Approves <b>&gt;95% of nominal readings</b> in &lt;2 ms, completely bypassing expensive downstream ML inference.", table_cell_style)
        ],
        [
            Paragraph("<b>4. Convex Evidence Fusion</b>", table_cell_bold),
            Paragraph("Fuses statistical residual score C(z<sub>t</sub>) and contextual operating rule signal R<sub>t</sub> via: <b>S<sub>t</sub> = 0.80 &middot; C(z<sub>t</sub>) + 0.20 &middot; R<sub>t</sub></b>. Threshold &theta; = 55.0.", table_cell_style),
            Paragraph("Combines quantitative statistical deviation with contextual sanity (e.g. HVAC on during closed building schedule).", table_cell_style)
        ],
        [
            Paragraph("<b>5. Temporal Persistence Gating</b>", table_cell_bold),
            Paragraph("Maintains consecutive abnormal count n<sub>t</sub>. An anomaly is escalated if and only if <b>n<sub>t</sub> &ge; 2</b> consecutive intervals exceed threshold &theta; = 55.0.", table_cell_style),
            Paragraph("Filters out transient motor inrush spikes. <b>Suppresses 86.7% of false positives</b>; achieves 100% specificity.", table_cell_style)
        ],
        [
            Paragraph("<b>6. Decoupled Adaptive Telemetry</b>", table_cell_bold),
            Paragraph("Finite State Machine (FSM): NOMINAL (15 min / 900s) &harr; ANOMALY (5 min / 300s) &harr; RECOVERY (3-cycle confirmation). Immediate dispatch on edge delta &ge; 3cm.", table_cell_style),
            Paragraph("<b>66.7% reduction in network transmissions</b> during normal operation with sub-second alert escalation on fault.", table_cell_style)
        ],
        [
            Paragraph("<b>7. Actionable Cost of Inaction</b>", table_cell_bold),
            Paragraph("Excess kWh = (y<sub>t</sub> - &mu;&#771;) &times; 0.25h. Cost = Excess kWh &times; ₹9.50/kWh. CO<sub>2</sub> = Excess kWh &times; 0.82 kg/kWh.", table_cell_style),
            Paragraph("Translates raw sensor telemetry into executive financial liabilities and environmental carbon impact for administrators.", table_cell_style)
        ]
    ]

    t_stages = Table(stages_data, colWidths=[115, 255, 152])
    t_stages.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t_stages)
    story.append(Spacer(1, 8))

    # Architecture Diagram on Page 2
    fig1_path = FIG_DIR / "fig1_dif_architecture.png"
    if fig1_path.exists():
        story.append(Paragraph("<b>End-to-End Decision Intelligence Framework (DIF) Architecture</b>", h2_style))
        story.append(Image(str(fig1_path), width=500, height=188))
        story.append(Paragraph("<i>Fig. 1: Modular DIF pipeline integrating edge telemetry ingestion, 672-slot seasonal profiling, evidence fusion, and adaptive cadence switching.</i>", ParagraphStyle('Caption1', fontName=FONT_BODY_ITALIC, fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)))

    # Clean Page Break -> Page 3
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: MATHEMATICAL & COMPUTATIONAL COMPLEXITY DEEP-DIVE
    # =========================================================================
    story.append(Paragraph("3. Mathematical & Computational Complexity Deep-Dive", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    complexity_intro = (
        "<b>Rigorous Complexity Formulation:</b> In our presentation slide, we present the formal computational bounds of the "
        "Decision Intelligence Framework: <b>Time Complexity: O(M + K log K + F)</b> and <b>Space Complexity: O(M + K + F)</b>. "
        "Here is the exact mathematical derivation and physical meaning to explain when asked by judges:<br/>"
        "&bull; <b>M:</b> Number of specialist-model signals evaluated (e.g. electrical power, water tank depth, flow rate, air quality ADC).<br/>"
        "&bull; <b>K:</b> Number of candidate operational actions / recommendations being ranked (e.g. throttle HVAC, isolate water branch, dispatch waste crew).<br/>"
        "&bull; <b>F:</b> Number of contextual features fused into the decision matrix (e.g. weather, occupancy, HVAC schedules, tariff ₹9.50/kWh)."
    )
    t_c_intro = Table([[Paragraph(complexity_intro, callout_style)]], colWidths=[522])
    t_c_intro.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#86efac')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#059669')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_c_intro)
    story.append(Spacer(1, 6))

    # Complexity Breakdown Table
    c_table_data = [
        [Paragraph("Decision Pipeline Stage", table_head_style), Paragraph("Algorithmic Operation", table_head_style), Paragraph("Time Complexity", table_head_style), Paragraph("Space Complexity", table_head_style)],
        [
            Paragraph("<b>Stage 1: Validation & Baseline</b>", table_cell_bold),
            Paragraph("Scalar boundary check + hash lookup of 15-minute weekday slot in 672-entry profile table.", table_cell_style),
            Paragraph("<b>O(1)</b>", table_cell_bold),
            Paragraph("<b>O(1)</b> (O(S) profile retained)", table_cell_style)
        ],
        [
            Paragraph("<b>Stage 2: Specialist Signals</b>", table_cell_bold),
            Paragraph("Ingest and normalize M telemetry streams, computing residuals across active sensors.", table_cell_style),
            Paragraph("<b>O(M)</b>", table_cell_bold),
            Paragraph("<b>O(M)</b> working buffers", table_cell_style)
        ],
        [
            Paragraph("<b>Stage 3: Contextual Feature Fusion</b>", table_cell_bold),
            Paragraph("Linear weighting of F external parameters (weather, occupancy, HVAC schedules, tariff rates).", table_cell_style),
            Paragraph("<b>O(F)</b>", table_cell_bold),
            Paragraph("<b>O(F)</b> feature vector", table_cell_style)
        ],
        [
            Paragraph("<b>Stage 4: Action Ranking</b>", table_cell_bold),
            Paragraph("Multi-attribute utility calculation + comparison sorting (Timsort) of K candidate recommendations.", table_cell_style),
            Paragraph("<b>O(K log K)</b>", table_cell_bold),
            Paragraph("<b>O(K)</b> priority queue", table_cell_style)
        ],
        [
            Paragraph("<b>Stage 5: Recommendation Dispatch</b>", table_cell_bold),
            Paragraph("Emit top-ranked actionable dispatch payload with explanation and ₹ financial liability.", table_cell_style),
            Paragraph("<b>O(1)</b>", table_cell_bold),
            Paragraph("<b>O(1)</b> payload buffer", table_cell_style)
        ],
        [
            Paragraph("<b>Full Pipeline Decision Bound</b>", table_cell_bold),
            Paragraph("<b>End-to-End Decision Layer Execution</b> (combines signals, context fusion, and ranking).", table_cell_bold),
            Paragraph("<b>O(M + K log K + F)</b>", table_cell_bold),
            Paragraph("<b>O(M + K + F)</b>", table_cell_bold)
        ]
    ]

    t_comp = Table(c_table_data, colWidths=[130, 202, 100, 90])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e6f5ef')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 6))

    # Fast-Path & Memory Footprint Highlight Box
    latency_text = (
        "<b>Why EstateIQ Runs in Sub-Second Runtime (&lt;2.0 ms) with &lt;15 KB Heap:</b><br/>"
        "&bull; <b>Fast-Path O(1) Early Exit:</b> For &gt;95% of incoming readings where deviation is within normal diurnal limits "
        "(|d<sub>t</sub>| &lt; 15% and |z<sub>t</sub>| &lt; 1.875), the framework terminates in Stage 1 via an O(1) hash check, "
        "completely skipping the O(K log K) ranker. Average query latency is <b>1.8 ms</b>.<br/>"
        "&bull; <b>Bounded Memory Footprint:</b> In production, M &approx; 6 sensors, K &le; 8 actions, and F &approx; 10 context features. "
        "The total auxiliary working memory is under <b>15 KB</b>. This proves the algorithm can execute directly on edge gateways "
        "(Raspberry Pi, industrial gateways) or scale horizontally across 10,000+ campus nodes in the cloud without server bottlenecks."
    )
    t_lat = Table([[Paragraph(latency_text, callout_style)]], colWidths=[522])
    t_lat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bfdbfe')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#2563eb')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_lat)
    story.append(Spacer(1, 6))

    # Bottom Complexity Graphic Asset Embed
    comp_fig_path = SLIDE_ASSETS_DIR / "panel_bottom_complexity_pipeline.png"
    if comp_fig_path.exists():
        story.append(Paragraph("<b>Verified Presentation Graphic: Complexity Cards & Decision Pipeline</b>", h2_style))
        story.append(Image(str(comp_fig_path), width=510, height=116))
        story.append(Paragraph("<i>Embedded asset generated in <code>output/presentation/algorithm_metrics/panel_bottom_complexity_pipeline.png</code></i>", ParagraphStyle('CaptionC', fontName=FONT_BODY_ITALIC, fontSize=7.2, leading=9, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)))

    # Clean Page Break -> Page 4
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: SLIDE DECK AUDIT & EXACT CORRECTIONS WITH FIGURE 4
    # =========================================================================
    story.append(Paragraph("4. Slide Deck Audit & Exact Corrections for Presentation", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "To ensure the presentation is 100% bulletproof under technical scrutiny from the judges, "
        "the team must implement the following specific corrections across the two slides.",
        body_style
    ))

    slide_audit_data = [
        [Paragraph("Slide / Element", table_head_style), Paragraph("Current Issue in PPT", table_head_style), Paragraph("Required Correction", table_head_style), Paragraph("Judge Impact", table_head_style)],
        [
            Paragraph("<b>Slide 1: Panel D<br/>ROC Curve</b>", table_cell_bold),
            Paragraph("Blue ROC curve <b>bows downwards below the diagonal</b> (y &lt; x), looking like an inverted classifier (worse than random guessing), while claiming AUC = 1.00.", table_cell_style),
            Paragraph("Replace with <code>figures/fig4_roc_pr_curves.png</code>. The curve arches upward toward (0,1) with <b>ROC-AUC = 0.9846</b> and <b>PR-AUC = 0.9712</b>.", table_cell_style),
            Paragraph("<b>Critical:</b> ML judges know that an inverted curve means AUC &lt; 0.50. Fixing this demonstrates true statistical credibility.", table_cell_style)
        ],
        [
            Paragraph("<b>Slide 2: Stage 5<br/>Spelling Errors</b>", table_cell_bold),
            Paragraph("Contains 5 typographical errors:<br/>&bull; <code>ENGIIE</code><br/>&bull; <code>Trustworthiiess</code><br/>&bull; <code>Agreiment</code><br/>&bull; <code>Compateness</code><br/>&bull; <code>Reliabiliy</code>", table_cell_style),
            Paragraph("Fix spelling to:<br/>&bull; <b>ENGINE</b><br/>&bull; <b>Trustworthiness</b><br/>&bull; <b>Agreement</b><br/>&bull; <b>Completeness</b><br/>&bull; <b>Reliability</b>", table_cell_style),
            Paragraph("Eliminates visible typos from the architecture slide, ensuring a professional appearance.", table_cell_style)
        ],
        [
            Paragraph("<b>Slide 2: Column 01<br/>Telemetry Inputs</b>", table_cell_bold),
            Paragraph("Only lists macro inputs (Building Meters, Occupancy, Ambient Temp, HVAC Schedules), omitting physical edge sensors.", table_cell_style),
            Paragraph("Add actual IoT hardware on desk:<br/>&bull; PZEM-004T (Power Meter)<br/>&bull; HC-SR04 / AJ-SR04M (Sonar)<br/>&bull; ZJ-S201 (Flow Turbine)<br/>&bull; MQ-135 & DHT11 (Air & Climate)", table_cell_style),
            Paragraph("Bridges the physical hardware sitting on the table directly into the theoretical architecture slide.", table_cell_style)
        ]
    ]

    t_slide_audit = Table(slide_audit_data, colWidths=[105, 150, 155, 112])
    t_slide_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t_slide_audit)
    story.append(Spacer(1, 8))

    # Figure 4 Preview on Page 4
    fig4_path = FIG_DIR / "fig4_roc_pr_curves.png"
    if fig4_path.exists():
        story.append(Paragraph("<b>Reference Figure for Slide 1 (Panel D): Verified ROC & PR Curves (AUC = 0.9846, AP = 0.9712)</b>", h2_style))
        story.append(Image(str(fig4_path), width=500, height=164))
        story.append(Paragraph("<i>Fig. 4: Verified Anomaly Discrimination Curves. (a) ROC curve with proper upper-left convexity (AUC = 0.9846); (b) Precision-Recall curve with operational threshold at S &ge; 55.0 (Average Precision = 0.9712).</i>", ParagraphStyle('Caption4', fontName=FONT_BODY_ITALIC, fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)))
        story.append(Spacer(1, 6))

    # Callout about ready master slide
    master_box = (
        "<b>Ready-to-Use Slide Asset:</b> We have generated the complete full-bleed replacement slide at "
        "<code>output/presentation/algorithm_metrics/master_slide_algorithm_metrics_bput2026.png</code> (3200 &times; 1800 px, 200 DPI). "
        "The team can drop this single image directly into PowerPoint as a full slide to fix the ROC curve and typography in one step."
    )
    t_master = Table([[Paragraph(master_box, callout_style)]], colWidths=[522])
    t_master.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#86efac')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#059669')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_master)

    # Clean Page Break -> Page 5
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: LIVE HARDWARE DEMO PROTOCOL & TABLETOP EXECUTION GUIDE
    # =========================================================================
    story.append(Paragraph("5. Live Hardware Demo Protocol & Tabletop Execution Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "The EstateIQ live demo bridges physical sensor transducers to the real-time web dashboard. "
        "The table below details the exact hardware wiring, pin assignments, and interactive demo triggers to execute in front of judges.",
        body_style
    ))

    hw_pin_data = [
        [Paragraph("Subsystem", table_head_style), Paragraph("Hardware Model", table_head_style), Paragraph("Electrical Interface", table_head_style), Paragraph("Calibrated Operating Range", table_head_style), Paragraph("Live Demo Trigger Action", table_head_style)],
        [
            Paragraph("<b>Waste Bin Fill</b>", table_cell_bold),
            Paragraph("HC-SR04 Ultrasonic Sonar", table_cell_style),
            Paragraph("Trig: GPIO 5 / Echo: GPIO 18<br/>(Bench Sonar Auto-Route)", table_cell_style),
            Paragraph("4.0 &ndash; 400.0 cm<br/>(0 &ndash; 100% Volumetric Fill)", table_cell_style),
            Paragraph("<b>Wave hand over sonar sensor.</b> Moving distance by &ge; 3 cm triggers immediate event dispatch &amp; UI alert card.", table_cell_style)
        ],
        [
            Paragraph("<b>Water Tank Level</b>", table_cell_bold),
            Paragraph("AJ-SR04M Waterproof Sonar", table_cell_style),
            Paragraph("Trig: GPIO 5 / Echo: GPIO 18<br/>(1k&Omega;/2.2k&Omega; Divider)", table_cell_style),
            Paragraph("20.0 &ndash; 450.0 cm<br/>(0 &ndash; 100% Tank Level)", table_cell_style),
            Paragraph("Physical immersion or distance shift. Auto-routes between tank and waste bin.", table_cell_style)
        ],
        [
            Paragraph("<b>Electricity Meter</b>", table_cell_bold),
            Paragraph("Peacefair PZEM-004T 10A", table_cell_style),
            Paragraph("UART2 (RX: GPIO 16, TX: GPIO 17)<br/>Modbus RTU Protocol", table_cell_style),
            Paragraph("80 &ndash; 260 VAC, 0.0 &ndash; 10.0 A<br/>Class 1.0 Revenue Grade", table_cell_style),
            Paragraph("Connect AC test load or toggle software load simulator (Port 8502).", table_cell_style)
        ],
        [
            Paragraph("<b>Water Flow Meter</b>", table_cell_bold),
            Paragraph("ZJ-S201 Hall Turbine", table_cell_style),
            Paragraph("Hardware Interrupt (GPIO 4)<br/>450 Pulses per Liter", table_cell_style),
            Paragraph("1.0 &ndash; 30.0 L/min<br/>(0.1 L resolution)", table_cell_style),
            Paragraph("Blow lightly into turbine rotor to generate pulse frequency.", table_cell_style)
        ],
        [
            Paragraph("<b>Air Quality / Gas</b>", table_cell_bold),
            Paragraph("MQ-135 Gas Sensor", table_cell_style),
            Paragraph("Analog ADC1 (GPIO 34)<br/>Resistive Voltage Divider", table_cell_style),
            Paragraph("0 &ndash; 4095 ADC counts<br/>(Relative trend index)", table_cell_style),
            Paragraph("Hold alcohol swab or lighter gas near sensor to observe relative ADC spike.", table_cell_style)
        ],
        [
            Paragraph("<b>On-Device OLED</b>", table_cell_bold),
            Paragraph("0.96\" SSD1306 OLED", table_cell_style),
            Paragraph("I2C (SDA: GPIO 21, SCL: GPIO 22)", table_cell_style),
            Paragraph("128 &times; 64 Dot Matrix", table_cell_style),
            Paragraph("Real-time on-device status: displays current IP, sequence #, cadence, and tank/waste level.", table_cell_style)
        ]
    ]

    t_hw = Table(hw_pin_data, colWidths=[80, 105, 115, 102, 120])
    t_hw.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t_hw)
    story.append(Spacer(1, 8))

    # Seasonal Baseline Reference on Page 5
    fig2_path = FIG_DIR / "fig2_seasonal_baseline.png"
    if fig2_path.exists():
        story.append(Paragraph("<b>7-Day Diurnal Seasonal Baseline with Robust MAD Dispersion Bands</b>", h2_style))
        story.append(Image(str(fig2_path), width=500, height=159))
        story.append(Paragraph("<i>Fig. 2: Continuous 7-day seasonal energy profile across 672 quarter-hour intervals, illustrating dynamic confidence bands that track academic campus occupancy.</i>", ParagraphStyle('Caption2', fontName=FONT_BODY_ITALIC, fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)))

    # Clean Page Break -> Page 6
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: WI-FI CONTINGENCY & ADAPTIVE CADENCE STATE MACHINE
    # =========================================================================
    story.append(Paragraph("6. Wi-Fi Configuration, Dual Redundancy & Cadence Control", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    contingency_text = (
        "<b>Venue Wi-Fi vs Serial Fallback:</b> During hackathons, college venue Wi-Fi networks often feature client isolation "
        "or strict firewalls that block local IP connections between the ESP32 and the laptop. EstateIQ includes an automated dual-redundancy protocol:<br/>"
        "&bull; <b>Primary Mode (LAN / Wi-Fi Hotspot):</b> Connect the laptop and ESP32 to a mobile phone hotspot (e.g. <code>sandeepsmile390</code>). "
        "The ESP32 communicates directly with <code>http://&lt;laptop-ip&gt;:8000/api/v1/iot/telemetry</code>.<br/>"
        "&bull; <b>Secondary Contingency Mode (USB-Serial Bridge):</b> If Wi-Fi fails or drops, connect the ESP32 via Micro-USB cable to <code>COM7</code> "
        "and execute: <code>python tools/esp32_serial_bridge.py --port COM7 --baud 115200</code>. "
        "The bridge parses raw hardware serial packets and pushes them directly into the FastAPI backend over <code>localhost:8000</code>. "
        "<b>Zero Wi-Fi or router is required for the demo to succeed 100%.</b>"
    )
    t_contingency = Table([[Paragraph(contingency_text, callout_style)]], colWidths=[522])
    t_contingency.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bfdbfe')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#2563eb')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_contingency)
    story.append(Spacer(1, 8))

    # Cadence State Machine Figure on Page 6
    fig9_path = FIG_DIR / "fig9_anomaly_cadence_trace.png"
    if fig9_path.exists():
        story.append(Paragraph("<b>Adaptive Telemetry Reporting State Machine (15m &rarr; 5m &rarr; Recovery Hysteresis)</b>", h2_style))
        story.append(Image(str(fig9_path), width=500, height=262))
        story.append(Paragraph("<i>Fig. 9: Adaptive cadence transition trace showing 66.7% bandwidth reduction during nominal 15-minute reporting, instantaneous edge alert trigger, and 3-cycle recovery confirmation.</i>", ParagraphStyle('Caption9', fontName=FONT_BODY_ITALIC, fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)))
        story.append(Spacer(1, 6))

    # Metrological Honesty Callout
    honesty_text = (
        "<b>Metrological Precision Disclosure (Tell the Judges!):</b><br/>"
        "We distinguish revenue-grade submeter readings (PZEM-004T Class 1.0) and calibrated flow turbine pulses (450 p/L) as "
        "<b>metrologically verified measurements</b>. Conversely, MQ-135 readings are recorded as raw ADC voltage counts (0&ndash;4095) "
        "reflecting relative indoor trend indices, and are not presented as certified laboratory CO<sub>2</sub> concentrations. "
        "Judges appreciate this level of scientific honesty."
    )
    t_honesty = Table([[Paragraph(honesty_text, callout_style)]], colWidths=[522])
    t_honesty.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#64748b')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_honesty)

    # Clean Page Break -> Page 7
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: JUDGE Q&A DEFENSE MATRIX & PRE-PITCH CHECKLIST
    # =========================================================================
    story.append(Paragraph("7. Judge Q&A Defense Matrix: The 8 Toughest Questions & Winning Responses", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#047857'), spaceBefore=2, spaceAfter=6))

    qa_data = [
        [Paragraph("Judge Tough Question", table_head_style), Paragraph("Winning Technical Response for Team", table_head_style)],
        [
            Paragraph("<b>1. \"Why not just train an LSTM, Transformer, or Deep Autoencoder?\"</b>", table_cell_bold),
            Paragraph(
                "\"Deep neural networks are computationally heavy black boxes that cannot run locally on an edge microcontroller and "
                "require hundreds of hours of labeled training data. If an LSTM hallucinates or drifts under seasonal changes, facility engineers "
                "cannot audit its hidden layers. EstateIQ-DIF combines a deterministic 7-day seasonal baseline (MAE = 1.59 kWh) with convex evidence "
                "fusion. It executes in <b>under 2 milliseconds</b>, requires minimal O(M) memory, and provides mathematically verifiable evidence.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>2. \"What does O(M + K log K + F) actually mean in practice?\"</b>", table_cell_bold),
            Paragraph(
                "\"M is our specialist model streams, F is our contextual features, and K log K is the comparison-based sorting of candidate recommendations "
                "by multi-attribute utility. Because >95% of nominal readings exit early via an O(1) hash check, the ranker only runs when an anomaly is verified, "
                "keeping runtime under 2 ms with less than 15 KB memory footprint.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>3. \"How do you prevent false alarms when large AC compressors switch on?\"</b>", table_cell_bold),
            Paragraph(
                "\"Heavy inductive motors create single-interval inrush spikes upon startup. Traditional static threshold systems trigger an immediate false alarm. "
                "EstateIQ incorporates a <b>Temporal Persistence Gate (n &ge; 2)</b>. When a spike occurs, it is flagged as an unconfirmed candidate on interval 1. "
                "Only if the abnormal load sustains into interval 2 is an alert generated. This <b>suppressed 86.7% of false positives</b> in holdout benchmarks.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>4. \"How does your AI Copilot avoid hallucinating false numbers?\"</b>", table_cell_bold),
            Paragraph(
                "\"Our AI Assistant uses strict context grounding: it cannot invent sensor values. Every answer must cite exact JSON evidence "
                "from our API (`observed_reading`, `provenance: REAL_SENSOR`, `confidence_pct`). If a sensor is disconnected, it explicitly reports STANDBY.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>5. \"What happens during campus holidays, semester breaks, or exam weeks?\"</b>", table_cell_bold),
            Paragraph(
                "\"Our baseline is dynamic and non-parametric: it computes the <b>rolling median</b> across the 672 weekly quarter-hour slots, "
                "meaning it smoothly adapts to changing baseline levels over successive weeks. Additionally, our Stage 2 Context Filter accepts scheduled "
                "occupancy and HVAC schedules, automatically scaling the baseline expectation up or down for pre-scheduled events.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>6. \"Why don't you transmit sensor data continuously every 1 second over Wi-Fi?\"</b>", table_cell_bold),
            Paragraph(
                "\"Streaming continuous 1-second packets from hundreds of building nodes congests campus Wi-Fi and drains power. By decoupling "
                "<b>2.0-second local edge acquisition</b> from <b>15-minute nominal transmission</b>, we achieve a <b>66.7% reduction in network overhead</b>, "
                "while our edge delta trigger (&ge; 3cm) guarantees immediate sub-second alert escalation on real faults.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>7. \"What happens if Wi-Fi disconnects or power drops temporarily?\"</b>", table_cell_bold),
            Paragraph(
                "\"Our ESP32 firmware includes a <b>30-packet volatile DRAM circular queue</b>. If HTTP POST fails, packets are safely buffered on the edge. "
                "When Wi-Fi reconnects, the queue flushes stored telemetry sequentially. Furthermore, our offline USB-Serial Bridge provides a zero-Wi-Fi fallback.\"",
                table_cell_style
            )
        ],
        [
            Paragraph("<b>8. \"What is the real business impact or ROI for estate managers?\"</b>", table_cell_bold),
            Paragraph(
                "\"Instead of displaying an abstract anomaly score, EstateIQ calculates the direct <b>Cost of Inaction in Indian Rupees</b> "
                "(Excess kWh &times; ₹9.50/kWh) and carbon impact (0.82 kg CO<sub>2</sub>/kWh). This gives campus administrators instant, dollar-for-dollar "
                "financial justification to dispatch maintenance technicians and stop resource waste before utility bills arrive.\"",
                table_cell_style
            )
        ]
    ]

    t_qa = Table(qa_data, colWidths=[155, 367])
    t_qa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t_qa)
    story.append(Spacer(1, 6))

    # Final Team Checklist Callout
    final_box = (
        "<b>Pre-Pitch Master Checklist for Teammates:</b><br/>"
        "1. Laptop plugged in to AC power, FastAPI running at <code>http://0.0.0.0:8000</code>.<br/>"
        "2. ESP32 powered via USB; verify OLED displays live IP and sequence counter incrementing.<br/>"
        "3. Live dashboard open in Chrome at <code>http://localhost:8000</code> (verify waste/water cards display live cm readings).<br/>"
        "4. Have a ruler or test object ready to demonstrate the 3 cm sonar delta in front of the judges.<br/>"
        "5. Keep PPT slides on Slide 1 &amp; Slide 2 with the corrected ROC curve and fixed typography."
    )
    t_final = Table([[Paragraph(final_box, callout_style)]], colWidths=[522])
    t_final.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#86efac')),
        ('LINELEFT', (0,0), (-1,-1), 3.5, colors.HexColor('#059669')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_final)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated updated team master briefing PDF at: {OUT_PDF}")


if __name__ == '__main__':
    build_team_guide_pdf()
