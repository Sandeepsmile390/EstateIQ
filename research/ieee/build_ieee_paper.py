"""Typeset the comprehensive Elite-DIF research paper into a professional 5-page IEEE format."""
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
import pypdf

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

# Styles calibrated to fit under 5 pages exactly matching jbhj.pdf
S = getSampleStyleSheet()
S.add(ParagraphStyle(name='Titlex', fontName='Times-Bold', fontSize=12.0, leading=14.0, alignment=TA_CENTER, textColor=colors.HexColor('#111111'), spaceAfter=2.0))
S.add(ParagraphStyle(name='Authx', fontName='Times', fontSize=6.8, leading=8.4, alignment=TA_CENTER, spaceAfter=2.5))
S.add(ParagraphStyle(name='Abstractx', fontName='Times', fontSize=6.9, leading=8.1, alignment=TA_JUSTIFY, spaceAfter=2.0))
S.add(ParagraphStyle(name='Indexx', fontName='Times', fontSize=6.8, leading=8.0, alignment=TA_JUSTIFY, spaceAfter=2.5))

S.add(ParagraphStyle(name='Secx', fontName='Times-Bold', fontSize=7.6, leading=9.0, alignment=TA_CENTER, textColor=colors.HexColor('#17324D'), spaceBefore=3.0, spaceAfter=1.4, keepWithNext=True))
S.add(ParagraphStyle(name='Subx', fontName='Times-BoldItalic', fontSize=7.0, leading=8.3, spaceBefore=2.0, spaceAfter=1.0, keepWithNext=True))
S.add(ParagraphStyle(name='SubSubx', fontName='Times-Italic', fontSize=6.7, leading=8.0, spaceBefore=1.5, spaceAfter=0.6, keepWithNext=True))

S.add(ParagraphStyle(name='Bodyx', fontName='Times', fontSize=6.95, leading=8.05, alignment=TA_JUSTIFY, firstLineIndent=5.0, spaceAfter=1.0))
S.add(ParagraphStyle(name='BodyNoIndent', fontName='Times', fontSize=6.95, leading=8.05, alignment=TA_JUSTIFY, spaceAfter=1.0))
S.add(ParagraphStyle(name='Bulletx', fontName='Times', fontSize=6.8, leading=7.9, alignment=TA_JUSTIFY, leftIndent=5.0, spaceAfter=0.8))
S.add(ParagraphStyle(name='Equationx', fontName='Times-Italic', fontSize=6.8, leading=8.0, alignment=TA_CENTER, spaceBefore=0.8, spaceAfter=1.0))
S.add(ParagraphStyle(name='FigCaption', fontName='Times', fontSize=5.3, leading=6.5, alignment=TA_JUSTIFY, spaceBefore=1.0, spaceAfter=1.6))

S.add(ParagraphStyle(name='TableTitle', fontName='Times-Bold', fontSize=5.6, leading=6.8, alignment=TA_CENTER, spaceBefore=1.8, spaceAfter=0.6, keepWithNext=True))
S.add(ParagraphStyle(name='TableCaption', fontName='Times-Bold', fontSize=5.4, leading=6.4, alignment=TA_CENTER, spaceAfter=1.2, keepWithNext=True))
S.add(ParagraphStyle(name='TableHeader', fontName='Times-Bold', fontSize=4.6, leading=5.4, alignment=TA_CENTER, textColor=colors.HexColor('#111111')))
S.add(ParagraphStyle(name='TableCell', fontName='Times', fontSize=4.5, leading=5.3, alignment=TA_CENTER))
S.add(ParagraphStyle(name='TableCellLeft', fontName='Times', fontSize=4.5, leading=5.3, alignment=TA_LEFT))
S.add(ParagraphStyle(name='TableCellRight', fontName='Times', fontSize=4.5, leading=5.3, alignment=TA_RIGHT))

S.add(ParagraphStyle(name='Codex', fontName='Courier', fontSize=4.2, leading=4.9, leftIndent=1.5, spaceAfter=1.0))
S.add(ParagraphStyle(name='Refx', fontName='Times', fontSize=5.4, leading=6.4, leftIndent=7.0, firstLineIndent=-7.0, spaceAfter=0.8))

# Geometry setup matching jbhj.pdf
W, H = letter
lm = rm = 26.0
gap = 12.0
cw = (W - lm - rm - gap) / 2.0  # 274.0 pt
top = 20.0
bot = 20.0

# Read markdown manuscript
lines = MD.read_text(encoding='utf-8').splitlines()
title = lines[0].replace('# ', '').strip() if lines and lines[0].startswith('# ') else 'Elite-DIF: An Interpretable Robust Seasonal-Baseline, Scale-Floored Residual Scoring, and Evidence-Fused Decision Intelligence Algorithm for Real-Time Commercial Building Anomaly Triage'
abstract = ''
for i, line in enumerate(lines):
    if line.strip() == '## Abstract':
        for q in lines[i + 1:]:
            if q.strip().startswith('**Index Terms'): break
            if q.strip(): abstract += q.strip() + ' '
        break

header_width = W - lm - rm
hdr_blocks = [
    (Paragraph(title, S['Titlex']), S['Titlex']),
    (Paragraph(
        '<b>Team Elite (Team ID: BH26PS04T039)</b> &nbsp;&bull;&nbsp; '
        '<b>Problem Statement-04: Smart Campus / Institutional Facility Energy &amp; Utility Optimization</b><br/>'
        '<b>BPUT Hackathon 2026 (12&ndash;13 Nov 2026)</b> &nbsp;&bull;&nbsp; '
        '<b>Track:</b> Algorithm Track &amp; Decision Intelligence &nbsp;&bull;&nbsp; '
        '<i>Elite Research Group, Dept. of CSE &amp; AI</i>',
        S['Authx']
    ), S['Authx']),
    (Paragraph('<b><i>Abstract</i>—</b>' + abstract.strip(), S['Abstractx']), S['Abstractx']),
    (Paragraph(
        '<b><i>Index Terms</i>—</b>Building energy management, decision intelligence algorithms, robust statistics, '
        'median absolute deviation, seasonal baselining, scale-floored residual scoring, evidence fusion, '
        'adaptive cadence scheduling, fault detection and diagnostics (FDD), operational decision support.',
        S['Indexx']
    ), S['Indexx']),
]

measured_banner_height = 0.0
for p, style in hdr_blocks:
    _, hh = p.wrap(header_width, 1000)
    measured_banner_height += hh + (style.spaceAfter or 0)

banner_bottom_margin = 5.0
header_bottom = H - top - measured_banner_height - banner_bottom_margin

def page_art(c, doc):
    c.saveState()
    c.setTitle(title)
    c.setAuthor('Team Elite (Team ID: BH26PS04T039)')
    c.setSubject('BPUT Hackathon 2026 - Problem Statement-04 - Elite-DIF Algorithm Research Paper')
    c.setCreator('Elite-DIF IEEE Build Pipeline (ReportLab 5.1.0)')
    c.setKeywords('building energy, decision intelligence algorithms, robust statistics, median absolute deviation, seasonal baseline, evidence fusion, BPUT Hackathon 2026, Team Elite, BH26PS04T039, Problem Statement-04')

    if doc.page == 1:
        y = H - top
        for p, style in hdr_blocks:
            _, hh = p.wrap(header_width, 1000)
            y -= hh
            p.drawOn(c, lm, y)
            y -= (style.spaceAfter or 0)
        c.setStrokeColor(colors.HexColor('#C8D3DC'))
        c.setLineWidth(0.6)
        c.line(lm, header_bottom + 3, W - rm, header_bottom + 3)
    else:
        c.setFont('Times-Italic', 6.0)
        c.setFillColor(colors.HexColor('#596773'))
        c.drawString(lm, H - 15.0, 'ELITE-DIF: ROBUST SEASONAL-BASELINE & EVIDENCE-FUSED DECISION INTELLIGENCE ALGORITHM')
        c.drawRightString(W - rm, H - 15.0, 'BPUT HACKATHON 2026 | TEAM ELITE (BH26PS04T039) | PS-04')
        c.setStrokeColor(colors.HexColor('#D1D9DF'))
        c.setLineWidth(0.4)
        c.line(lm, H - 17.0, W - rm, H - 17.0)

    c.setStrokeColor(colors.HexColor('#D1D9DF'))
    c.setLineWidth(0.4)
    c.line(lm, 16.0, W - rm, 16.0)
    c.setFont('Times', 6.0)
    c.setFillColor(colors.HexColor('#596773'))
    c.drawString(lm, 9.0, 'Team Elite (BH26PS04T039) | Problem Statement-04 | BPUT Hackathon 2026 (12–13 November 2026)')
    c.drawRightString(W - rm, 9.0, f'Page {doc.page}')
    c.restoreState()

doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=lm, rightMargin=rm, topMargin=top, bottomMargin=bot)
first_frames = [
    Frame(lm, bot, cw, header_bottom - bot, id='firstleft', leftPadding=0, rightPadding=1, topPadding=0, bottomPadding=0),
    Frame(lm + cw + gap, bot, cw, header_bottom - bot, id='firstright', leftPadding=1, rightPadding=0, topPadding=0, bottomPadding=0),
]
cols_frames = [
    Frame(lm, bot, cw, H - top - bot, id='col1', leftPadding=0, rightPadding=1, topPadding=0, bottomPadding=0),
    Frame(lm + cw + gap, bot, cw, H - top - bot, id='col2', leftPadding=1, rightPadding=0, topPadding=0, bottomPadding=0),
]
doc.addPageTemplates([
    PageTemplate(id='first', frames=first_frames, onPage=page_art),
    PageTemplate(id='cols', frames=cols_frames, onPage=page_art),
])

def clean_math(txt: str) -> str:
    txt = txt.replace('&', '&amp;')
    txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', txt)
    txt = re.sub(r'\*(.*?)\*', r'<i>\1</i>', txt)
    txt = txt.replace('≥', '&ge;').replace('≤', '&le;').replace('±', '&plusmn;')
    txt = txt.replace('×', '&times;').replace('—', '&mdash;').replace('–', '&ndash;')
    txt = txt.replace(r'\ge', '&ge;').replace(r'\le', '&le;')
    txt = txt.replace(r'\pm', '&plusmn;').replace(r'\times', '&times;')
    txt = txt.replace(r'\cdot', '&bull;').replace(r'\approx', '&asymp;')
    txt = txt.replace(r'\mid', '|').replace(r'\{', '{').replace(r'\}', '}')
    txt = txt.replace(r'\vert', '|').replace(r'\lvert', '|').replace(r'\rvert', '|')
    txt = txt.replace(r'\dots', '...').replace(r'\to', '&rarr;')
    txt = txt.replace(r'\infty', '<font face="STIXMath">&#x221e;</font>')
    txt = txt.replace(r'\in', '<font face="STIXMath">&#x2208;</font>')
    txt = txt.replace(r'\neg', '<font face="STIXMath">&#xac;</font>')
    txt = txt.replace(r'\land', '<font face="STIXMath">&#x2227;</font>')
    txt = txt.replace(r'\lor', '<font face="STIXMath">&#x2228;</font>')
    txt = txt.replace(r'\wedge', '<font face="STIXMath">&#x2227;</font>')
    txt = txt.replace(r'\vee', '<font face="STIXMath">&#x2228;</font>')
    txt = txt.replace(r'\Delta', '&Delta;').replace(r'\epsilon', '&epsilon;')
    txt = txt.replace(r'\sigma', '&sigma;').replace(r'\rho', '&rho;')
    txt = txt.replace(r'\theta', '&theta;').replace(r'\Phi', '&Phi;')
    txt = txt.replace(r'\gamma', '&gamma;').replace(r'\tau', '&tau;')
    txt = txt.replace(r'\psi', '&psi;').replace(r'\mu', '&mu;')
    txt = txt.replace(r'\mathcal{R}', 'R').replace(r'\mathcal{E}', 'E')
    txt = txt.replace(r'\mathcal{B}', 'B').replace(r'\mathcal{H}', 'H')
    txt = txt.replace(r'\mathcal{N}', 'N').replace(r'\mathbb{I}', 'I').replace(r'\mathbb{E}', 'E')
    txt = re.sub(r'\\(?:text|mathrm)\{([^}]+)\}', r'\1', txt)
    txt = re.sub(r'\\mathtt\{([^}]+)\}', r'<font face="Courier">\1</font>', txt)
    txt = txt.replace(r'^\circ\text{C}', '&deg;C').replace(r'^\circ\mathrm{C}', '&deg;C').replace(r'^\circ C', '&deg;C')
    txt = txt.replace(r'^\circ', '&deg;')
    def format_math_block(match):
        s = match.group(1)
        s = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', s)
        s = re.sub(r'\^([0-9a-zA-Z+-]+)', r'<sup>\1</sup>', s)
        s = re.sub(r'\_\{([^}]+)\}', r'<sub>\1</sub>', s)
        s = re.sub(r'\_(&[a-zA-Z]+;|[0-9a-zA-Z]+)', r'<sub>\1</sub>', s)
        return f'<i>{s}</i>'
    txt = re.sub(r'\$([^$]+)\$', format_math_block, txt)
    return txt

story = [NextPageTemplate('cols')]
start_idx = next(i for i, x in enumerate(lines) if x.strip() == '## I. Introduction')
i = start_idx
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue
    
    if line.startswith('## '):
        sec_title = line[3:].strip()
        story.append(Paragraph(sec_title.upper(), S['Secx']))
        i += 1
        continue
    if line.startswith('### '):
        sub_title = line[4:].strip()
        story.append(Paragraph(sub_title, S['Subx']))
        i += 1
        continue
    if line.startswith('$$') and line.endswith('$$'):
        m = re.search(r'\\tag\{(\d+)\}', line)
        if m:
            eq_num = int(m.group(1))
            eq_img = EQ_DIR / f'eq_{eq_num}.png'
            if eq_img.exists():
                if eq_num in [10, 19, 27]: eh = 20.0
                elif eq_num in [21, 26]: eh = 30.0
                elif eq_num in [2, 4, 12, 13, 15, 22, 25, 28, 29, 30]: eh = 12.0
                else: eh = 9.5
                story.extend([Spacer(1, 0.4), Image(str(eq_img), width=cw - 11, height=eh), Spacer(1, 0.6)])
                i += 1
                continue
        eq_text = line[2:-2].strip()
        story.append(Paragraph(clean_math(eq_text), S['Equationx']))
        i += 1
        continue
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
                if 'fig1' in fpath: img_h = 88
                elif 'fig2' in fpath: img_h = 75
                elif 'fig3' in fpath: img_h = 72
                elif 'fig4' in fpath: img_h = 78
                elif 'fig5' in fpath: img_h = 90
                elif 'fig6' in fpath: img_h = 75
                elif 'fig7' in fpath: img_h = 68
                elif 'fig8' in fpath: img_h = 80
                elif 'fig9' in fpath: img_h = 110
                else: img_h = 75
                story.extend([Spacer(1, 0.8), Image(str(full_img_path), width=cw, height=img_h), Spacer(1, 0.3), Paragraph(clean_math(caption), S['FigCaption']), Spacer(1, 0.8)])
            i += 1
            continue
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
            clean_row = raw_row.strip('|').replace(r'\|', '__ESCAPED_PIPE__')
            clean_row = re.sub(r'\$[^$]+\$', lambda m: m.group(0).replace('|', '__MATH_PIPE__'), clean_row)
            cells = [x.replace('__ESCAPED_PIPE__', '|').replace('__MATH_PIPE__', '|').strip() for x in clean_row.split('|')]
            if not all(set(x) <= set('-: ') for x in cells): tab.append(cells)
            i += 1
        if tab:
            ncols = len(tab[0])
            header_str = ' '.join(tab[0])
            if ncols == 4:
                if 'Feature' in header_str or 'Scope' in header_str: col_w = [cw * 0.22, cw * 0.23, cw * 0.23, cw * 0.32]
                else: col_w = [cw * 0.30, cw * 0.16, cw * 0.16, cw * 0.38]
            elif ncols == 5: col_w = [cw * 0.35, cw * 0.16, cw * 0.15, cw * 0.16, cw * 0.18]
            elif ncols == 6:
                if 'MAE' in header_str: col_w = [cw * 0.31, cw * 0.14, cw * 0.14, cw * 0.10, cw * 0.13, cw * 0.18]
                elif 'Building ID' in header_str: col_w = [cw * 0.18, cw * 0.16, cw * 0.18, cw * 0.16, cw * 0.16, cw * 0.16]
                elif 'Strategy' in header_str: col_w = [cw * 0.26, cw * 0.17, cw * 0.17, cw * 0.12, cw * 0.12, cw * 0.16]
                else: col_w = [cw * 0.18, cw * 0.15, cw * 0.16, cw * 0.16, cw * 0.16, cw * 0.19]
            elif ncols == 7: col_w = [cw * 0.31, cw * 0.105, cw * 0.105, cw * 0.105, cw * 0.11, cw * 0.11, cw * 0.155]
            elif ncols == 8: col_w = [cw * 0.28, cw * 0.09, cw * 0.09, cw * 0.09, cw * 0.09, cw * 0.11, cw * 0.11, cw * 0.14]
            elif ncols == 9:
                if 'Threshold' in header_str: col_w = [cw * 0.17, cw * 0.075, cw * 0.075, cw * 0.075, cw * 0.075, cw * 0.13, cw * 0.13, cw * 0.13, cw * 0.14]
                else: col_w = [cw * 0.34, cw * 0.065, cw * 0.065, cw * 0.07, cw * 0.065, cw * 0.10, cw * 0.095, cw * 0.095, cw * 0.095]
            else: col_w = [cw / ncols] * ncols
            fmt_tab = []
            for row_idx, row in enumerate(tab):
                fmt_row = []
                for col_idx, cell in enumerate(row):
                    if row_idx == 0: st = S['TableHeader']
                    elif col_idx == 0: st = S['TableCellLeft']
                    elif re.match(r'^-?\d+(?:\.\d+)?%?$', cell): st = S['TableCellRight']
                    else: st = S['TableCell']
                    fmt_row.append(Paragraph(clean_math(cell), st))
                fmt_tab.append(fmt_row)
            t = Table(fmt_tab, colWidths=col_w, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Times'),
                ('FONTSIZE', (0, 0), (-1, -1), 4.3),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAEFF4')),
                ('LINEABOVE', (0, 0), (-1, 0), 1.0, colors.HexColor('#17324D')),
                ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor('#17324D')),
                ('LINEBELOW', (0, -1), (-1, -1), 1.0, colors.HexColor('#17324D')),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#D5DEE5')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 0.7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0.7),
                ('LEFTPADDING', (0, 0), (-1, -1), 0.7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0.7),
            ]))
            story.extend([Spacer(1, 0.8), t, Spacer(1, 1.0)])
        continue
    if line.startswith('```'):
        code = []
        i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            code.append(lines[i]); i += 1
        code_txt = '<br/>'.join(x.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for x in code)
        story.extend([Spacer(1, 0.8), Paragraph(code_txt, S['Codex']), Spacer(1, 0.8)])
        i += 1
        continue
    if re.match(r'^\[\d+\]', line):
        story.append(Paragraph(clean_math(line), S['Refx']))
        i += 1
        continue
    if line.startswith(('**Authors:**', '**Affiliation:**', '**Contact:**', '**Funding:**', '**Target Venue:**', '**Manuscript Status:**', '**Index Terms', '**Team Name:', '**Team ID:', '**Problem Statement:', '**Venue / Event:', '**Track:')):
        i += 1
        continue
    if re.match(r'^(?:[-*]|\d+\.)\s+', line):
        bullet_txt = re.sub(r'^(?:[-*]|\d+\.)\s+', '', line)
        story.append(Paragraph('&bull; ' + clean_math(bullet_txt), S['Bulletx']))
        i += 1
        continue
    paragraph = line
    i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '|', '```', '**', '[', '- ', '* ', '1.', '2.', '3.', '4.', '5.', '$$', '![', 'TABLE ')):
        paragraph += ' ' + lines[i].strip()
        i += 1
    story.append(Paragraph(clean_math(paragraph), S['Bodyx']))

doc.build(story)
r = pypdf.PdfReader(str(OUT))
print(f"Generated multi-page IEEE PDF: {OUT} (Total Pages: {len(r.pages)})")
