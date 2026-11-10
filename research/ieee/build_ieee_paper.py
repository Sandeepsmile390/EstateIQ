"""Typeset the comprehensive EstateIQ-DIF research paper into a professional multi-page IEEE format."""
import os
import re
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, PageBreak, NextPageTemplate, Flowable, Image, FrameBreak
)

ROOT = Path(__file__).resolve().parents[2]
MD = ROOT / 'research/ieee/estateiq_elite_dif_research_paper.md'
OUT = ROOT / 'output/pdf/estateiq_elite_dif_ieee_research_paper.pdf'
FIG_DIR = ROOT / 'research/ieee/figures'
EQ_DIR = ROOT / 'research/ieee/equations'

# Ensure figures and equations exist
if not (FIG_DIR / 'fig8_sensitivity_and_baselines.png').exists():
    import runpy
    runpy.run_path(str(ROOT / 'research/ieee/generate_ieee_figures.py'))

if not (EQ_DIR / 'eq_1.png').exists():
    import runpy
    runpy.run_path(str(ROOT / 'research/ieee/render_equations.py'))

# Register TrueType fonts (Times New Roman for IEEE)
pdfmetrics.registerFont(TTFont('Times', 'C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('Times-Bold', 'C:/Windows/Fonts/timesbd.ttf'))
pdfmetrics.registerFont(TTFont('Times-Italic', 'C:/Windows/Fonts/timesi.ttf'))
pdfmetrics.registerFont(TTFont('Times-BoldItalic', 'C:/Windows/Fonts/timesbi.ttf'))
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))

# Register STIX font for crisp mathematical and logical operator glyphs
import matplotlib
mpl_font_dir = Path(matplotlib.__file__).parent / 'mpl-data/fonts/ttf'
stix_path = mpl_font_dir / 'STIXGeneral.ttf'
if stix_path.exists():
    pdfmetrics.registerFont(TTFont('STIXMath', str(stix_path)))

# Styles
S = getSampleStyleSheet()
S.add(ParagraphStyle(name='Titlex', fontName='Times-Bold', fontSize=17.0, leading=20.0, alignment=TA_CENTER, textColor=colors.HexColor('#111111'), spaceAfter=5))
S.add(ParagraphStyle(name='Authx', fontName='Times', fontSize=8.2, leading=10.4, alignment=TA_CENTER, spaceAfter=5))
S.add(ParagraphStyle(name='Abstractx', fontName='Times', fontSize=8.0, leading=9.8, alignment=TA_JUSTIFY, spaceAfter=4))
S.add(ParagraphStyle(name='Indexx', fontName='Times', fontSize=7.8, leading=9.6, alignment=TA_JUSTIFY, spaceAfter=5))

S.add(ParagraphStyle(name='Secx', fontName='Times-Bold', fontSize=8.8, leading=10.6, alignment=TA_CENTER, textColor=colors.HexColor('#17324D'), spaceBefore=6.5, spaceAfter=3.0, keepWithNext=True))
S.add(ParagraphStyle(name='Subx', fontName='Times-BoldItalic', fontSize=8.0, leading=9.6, spaceBefore=4.0, spaceAfter=2.0, keepWithNext=True))
S.add(ParagraphStyle(name='SubSubx', fontName='Times-Italic', fontSize=7.6, leading=9.0, spaceBefore=3.0, spaceAfter=1.5, keepWithNext=True))

S.add(ParagraphStyle(name='Bodyx', fontName='Times', fontSize=7.4, leading=8.9, alignment=TA_JUSTIFY, firstLineIndent=7.0, spaceAfter=2.0))
S.add(ParagraphStyle(name='BodyNoIndent', fontName='Times', fontSize=7.4, leading=8.9, alignment=TA_JUSTIFY, spaceAfter=2.0))
S.add(ParagraphStyle(name='Bulletx', fontName='Times', fontSize=7.2, leading=8.6, alignment=TA_JUSTIFY, leftIndent=8.0, spaceAfter=1.6))
S.add(ParagraphStyle(name='Equationx', fontName='Times-Italic', fontSize=7.2, leading=8.8, alignment=TA_CENTER, spaceBefore=2.0, spaceAfter=2.5))
S.add(ParagraphStyle(name='FigCaption', fontName='Times', fontSize=6.6, leading=8.0, alignment=TA_JUSTIFY, spaceBefore=2.0, spaceAfter=3.5))

S.add(ParagraphStyle(name='TableTitle', fontName='Times-Bold', fontSize=6.8, leading=8.2, alignment=TA_CENTER, spaceBefore=4.0, spaceAfter=1.0, keepWithNext=True))
S.add(ParagraphStyle(name='TableCaption', fontName='Times-Bold', fontSize=6.0, leading=7.2, alignment=TA_CENTER, spaceAfter=2.5, keepWithNext=True))
S.add(ParagraphStyle(name='TableHeader', fontName='Times-Bold', fontSize=5.4, leading=6.6, alignment=TA_CENTER, textColor=colors.HexColor('#111111')))
S.add(ParagraphStyle(name='TableCell', fontName='Times', fontSize=5.4, leading=6.6, alignment=TA_CENTER))
S.add(ParagraphStyle(name='TableCellLeft', fontName='Times', fontSize=5.4, leading=6.6, alignment=TA_LEFT))
S.add(ParagraphStyle(name='TableCellRight', fontName='Times', fontSize=5.4, leading=6.6, alignment=TA_RIGHT))

S.add(ParagraphStyle(name='Codex', fontName='Courier', fontSize=5.6, leading=6.6, leftIndent=3.0, spaceAfter=2.5))
S.add(ParagraphStyle(name='Refx', fontName='Times', fontSize=6.4, leading=7.5, leftIndent=9.0, firstLineIndent=-9.0, spaceAfter=1.8))


# Geometry setup (Letter: 612 x 792 pt)
W, H = letter
lm = rm = 0.56 * inch      # 40.32 pt
top = 0.48 * inch          # 34.56 pt
bot = 0.50 * inch          # 36.00 pt
gap = 0.20 * inch          # 14.40 pt
cw = (W - lm - rm - gap) / 2.0  # 258.48 pt


# Read markdown manuscript
lines = MD.read_text(encoding='utf-8').splitlines()

title = lines[0].replace('# ', '').strip() if lines and lines[0].startswith('# ') else 'EstateIQ-DIF: A Robust Seasonal-Baseline and Rule-Fusion Framework for Building Energy Anomaly Triage'
abstract = ''
for i, line in enumerate(lines):
    if line.strip() == '## Abstract':
        for q in lines[i + 1:]:
            if q.strip().startswith('**Index Terms'):
                break
            if q.strip():
                abstract += q.strip() + ' '
        break

# Compute header banner height dynamically
header_width = W - lm - rm
hdr_blocks = [
    (Paragraph(title, S['Titlex']), S['Titlex']),
    (Paragraph(
        '<b>[Author Name(s) Placeholder]</b> &nbsp;&bull;&nbsp; '
        '<i>Department of Electrical and Computer Engineering / Smart Facilities Lab</i><br/>'
        '<b>[Author Affiliation / Institution Placeholder]</b> &nbsp;&bull;&nbsp; '
        '<b>Contact:</b> [Author Contact / Email Placeholder]<br/>'
        '<b>Target Venue:</b> [Target IEEE Conference Placeholder - Generic Research Draft] &nbsp;&bull;&nbsp; '
        '<b>Funding:</b> [Funding Sponsor / Grant Details Placeholder - None Declared]',
        S['Authx']
    ), S['Authx']),
    (Paragraph('<b><i>Abstract</i>—</b>' + abstract.strip(), S['Abstractx']), S['Abstractx']),
    (Paragraph(
        '<b><i>Index Terms</i>—</b>Building energy management, anomaly detection, robust statistics, median absolute deviation, seasonal baseline, telemetry processing, fault detection and diagnostics (FDD), decision support. '
        '<i>Draft Notice:</i> Generic IEEE conference-style draft; venue template not yet selected; results evaluated on generated telemetry.',
        S['Indexx']
    ), S['Indexx']),
]

measured_banner_height = 0.0
for p, style in hdr_blocks:
    _, hh = p.wrap(header_width, 1000)
    measured_banner_height += hh + (style.spaceAfter or 0)

banner_bottom_margin = 10.0
header_bottom = H - top - measured_banner_height - banner_bottom_margin


def page_art(c, doc):
    c.saveState()

    # Populate PDF metadata
    c.setTitle(title)
    c.setAuthor('[Author Name(s) Placeholder]')
    c.setSubject('Generic IEEE Conference Draft - Building Energy Anomaly Triage')
    c.setCreator('EstateIQ-DIF IEEE Build Pipeline (ReportLab 5.1.0)')
    c.setKeywords('building energy, anomaly detection, robust statistics, seasonal baseline, telemetry, decision support')

    if doc.page == 1:
        y = H - top
        for p, style in hdr_blocks:
            _, hh = p.wrap(header_width, 1000)
            y -= hh
            p.drawOn(c, lm, y)
            y -= (style.spaceAfter or 0)
        c.setStrokeColor(colors.HexColor('#C8D3DC'))
        c.setLineWidth(0.6)
        c.line(lm, header_bottom + 4, W - rm, header_bottom + 4)
    else:
        # Running header on page 2+
        c.setFont('Times-Italic', 6.0)
        c.setFillColor(colors.HexColor('#596773'))
        c.drawString(lm, H - 0.35 * inch, 'ESTATEIQ-DIF: ADAPTIVE MULTI-MODAL TELEMETRY & DECISION FRAMEWORK FOR BUILDING TRIAGE')
        c.drawRightString(W - rm, H - 0.35 * inch, 'GENERIC IEEE RESEARCH DRAFT')
        c.setStrokeColor(colors.HexColor('#D1D9DF'))
        c.setLineWidth(0.4)
        c.line(lm, H - 0.38 * inch, W - rm, H - 0.38 * inch)

    # Footer on all pages
    c.setStrokeColor(colors.HexColor('#D1D9DF'))
    c.setLineWidth(0.4)
    c.line(lm, 0.38 * inch, W - rm, 0.38 * inch)
    c.setFont('Times', 6.0)
    c.setFillColor(colors.HexColor('#596773'))
    c.drawString(lm, 0.24 * inch, 'EstateIQ-DIF | Generic IEEE conference-style research draft (simulated telemetry)')
    c.drawRightString(W - rm, 0.24 * inch, f"Page {doc.page}")

    c.restoreState()


doc = BaseDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=lm,
    rightMargin=rm,
    topMargin=top,
    bottomMargin=bot,
    title='EstateIQ-DIF Research Paper',
    author='[Author Name(s) Placeholder]',
    subject='Generic IEEE Conference Draft',
    creator='EstateIQ-DIF IEEE Build Pipeline',
)

first_frames = [
    Frame(lm, bot, cw, header_bottom - bot, id='firstleft', leftPadding=1, rightPadding=2, topPadding=1, bottomPadding=1),
    Frame(lm + cw + gap, bot, cw, header_bottom - bot, id='firstright', leftPadding=2, rightPadding=1, topPadding=1, bottomPadding=1),
]

cols_frames = [
    Frame(lm, bot, cw, H - top - bot, id='col1', leftPadding=1, rightPadding=2, topPadding=1, bottomPadding=1),
    Frame(lm + cw + gap, bot, cw, H - top - bot, id='col2', leftPadding=2, rightPadding=1, topPadding=1, bottomPadding=1),
]

doc.addPageTemplates([
    PageTemplate(id='first', frames=first_frames, onPage=page_art),
    PageTemplate(id='cols', frames=cols_frames, onPage=page_art),
])

story = [NextPageTemplate('cols')]

start_idx = next(i for i, x in enumerate(lines) if x.strip() == '## I. Introduction')
i = start_idx


def clean_math(txt: str) -> str:
    """Format markdown and mathematical expressions cleanly for ReportLab."""
    txt = txt.replace('&', '&amp;')
    txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', txt)
    txt = re.sub(r'\*(.*?)\*', r'<i>\1</i>', txt)

    # Common symbols and replacements
    txt = txt.replace('≥', '&ge;').replace('≤', '&le;').replace('±', '&plusmn;')
    txt = txt.replace('×', '&times;').replace('—', '&mdash;').replace('–', '&ndash;')
    txt = txt.replace(r'\ge', '&ge;').replace(r'\le', '&le;')
    txt = txt.replace(r'\pm', '&plusmn;').replace(r'\times', '&times;')
    txt = txt.replace(r'\cdot', '&bull;').replace(r'\approx', '&asymp;')
    txt = txt.replace(r'\mid', '|').replace(r'\{', '{').replace(r'\}', '}')
    txt = txt.replace(r'\vert', '|').replace(r'\lvert', '|').replace(r'\rvert', '|')
    # Mathematical symbols and logical operators via STIXMath font
    txt = txt.replace(r'\dots', '...').replace(r'\to', '&rarr;')
    # Handle \infty before \in to prevent partial replacement
    txt = txt.replace(r'\infty', '<font face="STIXMath">&#x221e;</font>')
    txt = txt.replace(r'\in', '<font face="STIXMath">&#x2208;</font>')
    txt = txt.replace(r'\neg', '<font face="STIXMath">&#xac;</font>')
    txt = txt.replace(r'\land', '<font face="STIXMath">&#x2227;</font>')
    txt = txt.replace(r'\lor', '<font face="STIXMath">&#x2228;</font>')
    txt = txt.replace(r'\wedge', '<font face="STIXMath">&#x2227;</font>')
    txt = txt.replace(r'\vee', '<font face="STIXMath">&#x2228;</font>')

    # Greek letters
    txt = txt.replace(r'\Delta', '&Delta;').replace(r'\epsilon', '&epsilon;')
    txt = txt.replace(r'\sigma', '&sigma;').replace(r'\rho', '&rho;')
    txt = txt.replace(r'\theta', '&theta;').replace(r'\Phi', '&Phi;')
    txt = txt.replace(r'\gamma', '&gamma;').replace(r'\tau', '&tau;')
    txt = txt.replace(r'\psi', '&psi;').replace(r'\mu', '&mu;')

    # Calligraphic and blackboard bold (pure letters to prevent nested tags)
    txt = txt.replace(r'\mathcal{R}', 'R').replace(r'\mathcal{E}', 'E')
    txt = txt.replace(r'\mathcal{B}', 'B').replace(r'\mathcal{H}', 'H')
    txt = txt.replace(r'\mathcal{N}', 'N')
    txt = txt.replace(r'\mathbb{I}', 'I').replace(r'\mathbb{E}', 'E')

    # Text commands
    txt = re.sub(r'\\(?:text|mathrm)\{([^}]+)\}', r'\1', txt)
    txt = re.sub(r'\\mathtt\{([^}]+)\}', r'<font face="Courier">\1</font>', txt)
    txt = txt.replace(r'^\circ\text{C}', '&deg;C').replace(r'^\circ\mathrm{C}', '&deg;C').replace(r'^\circ C', '&deg;C')
    txt = txt.replace(r'^\circ', '&deg;')

    # Subscripts and superscripts inside $...$
    def format_math_block(match):
        s = match.group(1)
        s = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', s)
        s = re.sub(r'\^([0-9a-zA-Z+-]+)', r'<sup>\1</sup>', s)
        s = re.sub(r'\_\{([^}]+)\}', r'<sub>\1</sub>', s)
        s = re.sub(r'\_(&[a-zA-Z]+;|[0-9a-zA-Z]+)', r'<sub>\1</sub>', s)
        return f"<i>{s}</i>"

    txt = re.sub(r'\$([^$]+)\$', format_math_block, txt)
    return txt


while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue

    # Major Section Header
    if line.startswith('## '):
        sec_title = line[3:].strip()
        if sec_title == 'References':
            story.append(FrameBreak())
        story.append(Paragraph(sec_title.upper(), S['Secx']))
        i += 1
        continue

    # Subsection Header
    if line.startswith('### '):
        sub_title = line[4:].strip()
        if sub_title == 'B. Environment and Artifact Provenance':
            story.append(FrameBreak())
        story.append(Paragraph(sub_title, S['Subx']))
        i += 1
        continue

    # Display Equations ($$ ... $$)
    if line.startswith('$$') and line.endswith('$$'):
        m = re.search(r'\\tag\{(\d+)\}', line)
        if m:
            eq_num = int(m.group(1))
            eq_img = EQ_DIR / f'eq_{eq_num}.png'
            if eq_img.exists():
                if eq_num in [10, 19, 27]:
                    eh = 36.0
                elif eq_num in [21, 26]:
                    eh = 49.0
                elif eq_num in [2, 4, 12, 13, 15, 22, 25, 28, 29, 30]:
                    eh = 28.5
                else:
                    eh = 24.5
                story.extend([
                    Spacer(1, 1.5),
                    Image(str(eq_img), width=cw, height=eh),
                    Spacer(1, 2.0),
                ])
                i += 1
                continue
        # Fallback if no tag found
        eq_text = line[2:-2].strip()
        story.append(Paragraph(clean_math(eq_text), S['Equationx']))
        i += 1
        continue

    # Image Figures in Markdown
    if line.startswith('![') and '](' in line:
        m = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if m:
            alt, fpath = m.group(1), m.group(2)
            full_img_path = ROOT / 'research/ieee' / fpath if not Path(fpath).is_absolute() else Path(fpath)
            caption = alt
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('*Fig.'):
                caption = lines[i + 1].strip().strip('*')
                i += 1
            if full_img_path.exists():
                img_w = cw
                if 'fig1' in fpath: img_h = 100
                elif 'fig2' in fpath: img_h = 84
                elif 'fig3' in fpath: img_h = 80
                elif 'fig4' in fpath: img_h = 88
                elif 'fig5' in fpath: img_h = 88
                elif 'fig6' in fpath: img_h = 84
                elif 'fig7' in fpath: img_h = 76
                elif 'fig8' in fpath: img_h = 91
                elif 'fig9' in fpath: img_h = 136
                else: img_h = 85

                story.extend([
                    Spacer(1, 2),
                    Image(str(full_img_path), width=img_w, height=img_h),
                    Spacer(1, 1),
                    Paragraph(clean_math(caption), S['FigCaption']),
                    Spacer(1, 2)
                ])
            i += 1
            continue

    # Markdown Tables
    if line.startswith('TABLE '):
        t_num = line
        t_cap = lines[i + 1].strip() if i + 1 < len(lines) and not lines[i + 1].startswith('|') else ''
        if t_cap: i += 1
        story.append(Paragraph(t_num, S['TableTitle']))
        if t_cap: story.append(Paragraph(t_cap, S['TableCaption']))
        i += 1
        continue

    if line.startswith('|'):
        tab = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            raw_row = lines[i].strip()
            # Protect escaped pipes \| and pipes inside math blocks $...$
            clean_row = raw_row.strip('|')
            clean_row = clean_row.replace(r'\|', '__ESCAPED_PIPE__')
            clean_row = re.sub(r'\$[^$]+\$', lambda m: m.group(0).replace('|', '__MATH_PIPE__'), clean_row)
            cells = [
                x.replace('__ESCAPED_PIPE__', '|').replace('__MATH_PIPE__', '|').strip()
                for x in clean_row.split('|')
            ]
            if not all(set(x) <= set('-: ') for x in cells):
                tab.append(cells)
            i += 1
        if tab:
            ncols = len(tab[0])
            header_str = ' '.join(tab[0])
            if ncols == 4:
                # Table I (Scope Classification) vs Table II (Complexity Breakdown)
                if 'Feature' in header_str or 'Scope' in header_str or 'Claim' in header_str:
                    col_w = [cw * 0.22, cw * 0.23, cw * 0.23, cw * 0.32]
                else:
                    col_w = [cw * 0.30, cw * 0.16, cw * 0.16, cw * 0.38]
            elif ncols == 5:
                # Table V: Event-Level Metrics
                col_w = [cw * 0.35, cw * 0.16, cw * 0.15, cw * 0.16, cw * 0.18]
            elif ncols == 6:
                # Table II (Forecasting), Table VII (Held-Out FPR), Table X (Network Transmission), or Table XI (Microbenchmark)
                if 'MAE' in header_str:
                    col_w = [cw * 0.31, cw * 0.14, cw * 0.14, cw * 0.10, cw * 0.13, cw * 0.18]
                elif 'Building ID' in header_str:
                    col_w = [cw * 0.18, cw * 0.16, cw * 0.18, cw * 0.16, cw * 0.16, cw * 0.16]
                elif 'Strategy' in header_str or 'Reporting' in header_str:
                    col_w = [cw * 0.26, cw * 0.17, cw * 0.17, cw * 0.12, cw * 0.12, cw * 0.16]
                else:
                    col_w = [cw * 0.18, cw * 0.15, cw * 0.16, cw * 0.16, cw * 0.16, cw * 0.19]
            elif ncols == 7:
                # Table IV: Anomaly Detection Benchmark and Baseline Comparisons
                col_w = [cw * 0.31, cw * 0.105, cw * 0.105, cw * 0.105, cw * 0.11, cw * 0.11, cw * 0.155]
            elif ncols == 8:
                # Table IX: Sequential Replay Benchmark
                col_w = [cw * 0.28, cw * 0.09, cw * 0.09, cw * 0.09, cw * 0.09, cw * 0.11, cw * 0.11, cw * 0.14]
            elif ncols == 9:
                # Table IV (Ablation) or Table VI (Threshold Sensitivity)
                if 'Threshold' in header_str:
                    col_w = [cw * 0.17, cw * 0.075, cw * 0.075, cw * 0.075, cw * 0.075, cw * 0.13, cw * 0.13, cw * 0.13, cw * 0.14]
                else:
                    col_w = [cw * 0.34, cw * 0.065, cw * 0.065, cw * 0.07, cw * 0.065, cw * 0.10, cw * 0.095, cw * 0.095, cw * 0.095]
            else:
                col_w = [cw / ncols] * ncols

            fmt_tab = []
            for row_idx, row in enumerate(tab):
                fmt_row = []
                for col_idx, cell in enumerate(row):
                    if row_idx == 0:
                        st = S['TableHeader']
                    elif col_idx == 0:
                        st = S['TableCellLeft']
                    elif re.match(r'^-?\d+(?:\.\d+)?%?$', cell):
                        st = S['TableCellRight']
                    else:
                        st = S['TableCell']
                    fmt_row.append(Paragraph(clean_math(cell), st))
                fmt_tab.append(fmt_row)

            t = Table(fmt_tab, colWidths=col_w, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Times'),
                ('FONTSIZE', (0, 0), (-1, -1), 5.4),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAEFF4')),
                ('LINEABOVE', (0, 0), (-1, 0), 1.0, colors.HexColor('#17324D')),
                ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor('#17324D')),
                ('LINEBELOW', (0, -1), (-1, -1), 1.0, colors.HexColor('#17324D')),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#D5DEE5')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 1.8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
                ('LEFTPADDING', (0, 0), (-1, -1), 1.4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1.4),
            ]))
            story.extend([Spacer(1, 2), t, Spacer(1, 3)])
        continue

    # Code Blocks / Pseudocode
    if line.startswith('```'):
        code = []
        i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            code.append(lines[i])
            i += 1
        code_txt = '<br/>'.join(
            x.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for x in code
        )
        story.extend([
            Spacer(1, 2),
            Paragraph(code_txt, S['Codex']),
            Spacer(1, 2)
        ])
        i += 1
        continue

    # References
    if re.match(r'^\[\d+\]', line):
        story.append(Paragraph(clean_math(line), S['Refx']))
        i += 1
        continue

    # Front matter metadata tags
    if line.startswith('**Authors:**') or line.startswith('**Affiliation:**') or \
       line.startswith('**Contact:**') or line.startswith('**Funding:**') or \
       line.startswith('**Target Venue:**') or line.startswith('**Manuscript Status:**') or \
       line.startswith('**Index Terms'):
        i += 1
        continue

    # Bullet / List Items
    if re.match(r'^(?:[-*]|\d+\.)\s+', line):
        bullet_txt = re.sub(r'^(?:[-*]|\d+\.)\s+', '', line)
        story.append(Paragraph('&bull; ' + clean_math(bullet_txt), S['Bulletx']))
        i += 1
        continue

    # Regular paragraph
    paragraph = line
    i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '|', '```', '**', '[', '- ', '* ', '1.', '2.', '3.', '4.', '5.', '$$', '![', 'TABLE ')):
        paragraph += ' ' + lines[i].strip()
        i += 1

    story.append(Paragraph(clean_math(paragraph), S['Bodyx']))

doc.build(story)
print(f"Generated multi-page IEEE PDF: {OUT}")
