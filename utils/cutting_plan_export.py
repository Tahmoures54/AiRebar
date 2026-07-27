# utils/cutting_plan_export.py
"""
Cutting Plan Export – Ultra‑Professional HTML Report for AI Rebar.
- Accepts pre‑calculated plans to avoid re‑optimisation
- Smart SVG labeling (Length, Position, Listofer)
- Minimal design, print‑optimised, saves toner & paper
- Optional dynamic QR code for project tracking
- Displays listofer number in header and QR code when provided
- Automatic fallback to DB for project/client names
"""

import html
import webbrowser
import os
import base64
import io
import datetime
import sqlite3
from typing import Dict, Optional, List, Tuple, Any

from logic.optimizer import optimize_labeled_cuts
from db.models import ScrapModel
from config import DEFAULT_REBAR_GRADE, DB_PATH

# ------------------------------------------------------------------------------
# QR code generator (optional dependency)
# ------------------------------------------------------------------------------
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

# ---------- Company info (footer & branding) ----------
COMPANY_INFO = {
    "name": "AI Rebar",
    "phone": "+98 916 068 4552",
    "website": "https://airebar.io",
}
_whatsapp_number = ''.join(filter(str.isdigit, COMPANY_INFO['phone']))
WHATSAPP_LINK = f"https://wa.me/{_whatsapp_number}"

# ---------- Company logo SVG (same stirrup as in BBS report) ----------
def _inline_stirrup_svg():
    return '''<svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
        <line x1="10" y1="30" x2="40" y2="30" stroke="#1e3a8a" stroke-width="4" stroke-linecap="round"/>
        <line x1="10" y1="30" x2="10" y2="10" stroke="#1e3a8a" stroke-width="4" stroke-linecap="round"/>
        <line x1="40" y1="30" x2="40" y2="10" stroke="#1e3a8a" stroke-width="4" stroke-linecap="round"/>
        <line x1="10" y1="10" x2="18" y2="10" stroke="#1e3a8a" stroke-width="3" stroke-linecap="round"/>
        <line x1="40" y1="10" x2="32" y2="10" stroke="#1e3a8a" stroke-width="3" stroke-linecap="round"/>
    </svg>'''

# ---------- Bar SVG – clean modern style ----------
def _generate_bar_svg(plan: Dict[str, Any], bar_index: int, max_bar_len_m: float,
                      canvas_width: int = 800, bar_height: int = 40) -> str:
    """Return an SVG snippet representing a single stock bar with its pieces."""
    pieces = plan['bin']
    bar_len = plan['bar_length']
    used = sum(p[0] for p in pieces)
    waste = bar_len - used
    scale = canvas_width / max_bar_len_m if max_bar_len_m > 0 else 1
    svg_height = 80
    bar_top = 35
    label_top = 18

    svg_parts = []
    x_cursor = 0.0

    # Bar outline
    svg_parts.append(
        f'<rect x="0" y="{bar_top-2}" width="{canvas_width}" height="{bar_height+4}" '
        f'fill="#fafafa" stroke="#ccc" stroke-width="0.5" rx="2" />'
    )

    for length_m, lbl in pieces:
        w = length_m * scale
        length_mm = length_m * 1000

        # Safely extract labels (support both possible key names)
        pos = html.escape(str(lbl.get('pos', '-')))
        lf_val = lbl.get('listofer_no', lbl.get('listofer_number', '-'))
        lf = html.escape(str(lf_val))

        tooltip = f"Len: {length_mm:.0f} mm | Pos: {pos} | LF: {lf}"

        # Cut piece rectangle
        rect = (
            f'<rect x="{x_cursor:.1f}" y="{bar_top}" width="{w:.1f}" '
            f'height="{bar_height}" fill="#e8e8e8" stroke="#333" stroke-width="0.8" '
            f'rx="1"><title>{tooltip}</title></rect>'
        )
        svg_parts.append(rect)

        # Smart labeling based on available width
        if w > 85:
            label_text = f"{length_mm:.0f}mm | P:{pos} | LF:{lf}"
            font_size = 9
        elif w > 55:
            label_text = f"{length_mm:.0f} | LF:{lf}"
            font_size = 8.5
        elif w > 25:
            label_text = f"{length_mm:.0f}"
            font_size = 8
        else:
            label_text = ""   # too small for text

        if label_text:
            svg_parts.append(
                f'<text x="{x_cursor + w/2:.1f}" y="{bar_top + bar_height/2 + 4}" '
                f'text-anchor="middle" fill="#111" font-size="{font_size}" font-weight="600">'
                f'{label_text}</text>'
            )

        x_cursor += w

    # Waste section
    if waste > 0.001:
        waste_w = waste * scale
        waste_mm = waste * 1000
        svg_parts.append(
            f'<rect x="{x_cursor:.1f}" y="{bar_top}" width="{waste_w:.1f}" '
            f'height="{bar_height}" fill="#f5f5f5" stroke="#999" stroke-dasharray="4,3" '
            f'rx="1"><title>Waste: {waste_mm:.0f} mm</title></rect>'
        )
        if waste_w > 45:
            svg_parts.append(
                f'<text x="{x_cursor + waste_w/2:.1f}" y="{bar_top + bar_height/2 + 4}" '
                f'text-anchor="middle" fill="#666" font-size="9">Waste {waste_mm:.0f}</text>'
            )

    bar_label = f"Bar #{bar_index+1}  ·  {bar_len*1000:.0f} mm"
    svg = (
        f'<svg viewBox="0 0 {canvas_width} {svg_height}" '
        f'preserveAspectRatio="xMidYMid meet" style="width:100%; height:auto; display:block;">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="5" y="{label_top}" font-size="13" font-weight="bold" fill="#222">{bar_label}</text>'
        f'{"".join(svg_parts)}'
        f'</svg>'
    )
    return svg

# ---------- Professional CSS – minimal, print‑ready ----------
_CSS = """
<style>
    :root {
        --border-color: #333;
        --light-border: #ccc;
        --text-primary: #111;
        --bg-card: #fdfdfd;
        --accent: #1e3a8a;
    }
    * { box-sizing: border-box; margin:0; padding:0; }
    body {
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: white;
        color: var(--text-primary);
        line-height: 1.4;
        padding: 20px 25px;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
        border: 1px solid var(--light-border);
        padding: 35px 40px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 2px solid var(--accent);
    }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .company-logo { width: 55px; height: 55px; }
    .header-text { display: flex; flex-direction: column; }
    .company-name { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; color: var(--accent); }
    .company-subtitle { font-size: 13px; color: #555; margin-top: 2px; }
    .project-info { text-align: right; font-size: 13px; color: #333; }
    .project-info strong { font-size: 16px; display: block; margin-bottom: 6px; }

    .diameter-section { margin-bottom: 45px; }
    h2 { font-size: 18px; font-weight: 600; color: var(--accent); margin: 0 0 18px; padding-bottom: 6px; border-bottom: 1px solid var(--light-border); display: flex; align-items: baseline; gap: 8px; }
    h2 span { font-size: 14px; font-weight: 400; color: #666; }

    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 12px; margin: 15px 0 25px; }
    .summary-card { background: var(--bg-card); border: 1px solid var(--light-border); padding: 14px 16px; display: flex; flex-direction: column; justify-content: center; border-radius: 4px;}
    .summary-card h3 { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #666; margin-bottom: 6px; font-weight: 600; }
    .summary-card .value { font-size: 22px; font-weight: 700; line-height: 1.2; }
    .summary-card .unit { font-size: 12px; font-weight: 400; color: #555; margin-left: 1px; }

    .bar-svg { margin: 18px 0 24px; padding: 8px 0; }

    .total-summary { margin-top: 40px; padding-top: 20px; border-top: 2px solid var(--border-color); display: flex; flex-wrap: wrap; gap: 30px; justify-content: space-between; }
    .total-card { min-width: 140px; }
    .total-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #444; margin-bottom: 6px; }
    .total-value { font-size: 24px; font-weight: 700; color: var(--accent); }

    .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #555; border-top: 1px solid var(--light-border); padding-top: 20px; line-height: 1.6; position: relative; }
    .footer a { color: var(--accent); text-decoration: none; font-weight: 600; }
    .footer-qr { position: absolute; right: 0; top: 10px; width: 80px; height: 80px; }

    @media print {
        body { padding: 0; background: white; }
        .container { border: none; box-shadow: none; max-width: 100%; padding: 10mm 5mm; }
        .header { border-bottom-color: #000; }
        .bar-svg { border: none; padding: 4px 0; page-break-inside: avoid; }
        .summary-card, .total-summary { border-color: #000; }
        .footer { border-top-color: #000; page-break-inside: avoid; }
        @page { margin: 10mm; }
    }
</style>
"""

# ---------- QR Code generation ----------
def _generate_qr_image(text: str, size: int = 80) -> Optional[str]:
    """Return a base64 encoded PNG data URI for a QR code, or None."""
    if not HAS_QR:
        return None
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"

# ---------- Report generation ----------
def generate_cutting_plan_html(
    data_by_key: Dict[Tuple[float, str], List[Tuple[float, Dict[str, Any]]]],
    stock_length: float,
    project_name: str = "",
    client_name: str = "",
    project_id: Optional[int] = None,
    plans_by_key: Optional[Dict[Tuple[float, str], List[Dict[str, Any]]]] = None,
    listofer_filter: Optional[str] = None
) -> str:
    """
    Generate the full HTML report for the cutting plan.
    If plans_by_key is given (from a cached CuttingPlanWindow), those exact plans are used.
    Otherwise optimisation is re‑run.
    """

    # ---- Fallback: fetch project / client from DB if missing ----
    if project_id and (not project_name or not client_name):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.execute("SELECT name, client FROM projects WHERE id=?", (project_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                if not project_name:
                    project_name = row[0] or "Unnamed Project"
                if not client_name:
                    client_name = row[1] or ""
        except Exception:
            pass

    safe_project = html.escape(project_name) if project_name else "Unnamed Project"
    safe_client = html.escape(client_name) if client_name else "N/A"
    safe_listofer = html.escape(listofer_filter) if listofer_filter else "All"

    # Header with company logo, name, and project details
    header_html = f"""
    <div class="header">
        <div class="header-left">
            <div class="company-logo">{_inline_stirrup_svg()}</div>
            <div class="header-text">
                <div class="company-name">{html.escape(COMPANY_INFO['name'])}</div>
                <div class="company-subtitle">Cutting Plan Report</div>
            </div>
        </div>
        <div class="project-info">
            <strong>Cutting Plan Overview</strong>
            Project: {safe_project}<br>
            Client: {safe_client}<br>
            Listofer: <strong>{safe_listofer}</strong><br>
            Stock length: <strong>{stock_length} m</strong>
        </div>
    </div>
    """

    html_parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cutting Plan – {safe_project}</title>
    {_CSS}
</head>
<body><div class="container">
{header_html}
"""]

    total_bars = 0
    total_used = 0.0
    total_waste = 0.0

    for (dia, grade), items in sorted(data_by_key.items(), key=lambda x: (x[0][0], x[0][1])):
        # Use provided plans if available, otherwise re‑optimise
        if plans_by_key and (dia, grade) in plans_by_key:
            plans = plans_by_key[(dia, grade)]
        else:
            available_scraps = []
            if project_id is not None:
                raw_scraps = ScrapModel.get_available_scraps(project_id, dia, grade)
                available_scraps = [s[1] / 1000.0 for s in raw_scraps]
            plans, _ = optimize_labeled_cuts(items, stock_length, available_scraps)

        if not plans:
            continue

        max_bar_len = max(p['bar_length'] for p in plans)
        dia_used = sum(sum(p[0] for p in plan['bin']) for plan in plans)
        dia_waste = sum(plan['bar_length'] - sum(p[0] for p in plan['bin']) for plan in plans)
        dia_bars = len(plans)
        dia_waste_pct = (dia_waste / (dia_used + dia_waste)) * 100 if (dia_used + dia_waste) > 0 else 0.0

        grade_str = f" ({html.escape(grade)})" if grade else f" ({DEFAULT_REBAR_GRADE})"
        html_parts.append(f'<div class="diameter-section">')
        html_parts.append(f'<h2>{dia} mm<span>{grade_str}</span></h2>')

        html_parts.append(f'''
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Bars Used</h3>
                <div class="value">{dia_bars}</div>
            </div>
            <div class="summary-card">
                <h3>Total Cut Length</h3>
                <div class="value">{dia_used*1000:,.0f} <span class="unit">mm</span></div>
            </div>
            <div class="summary-card">
                <h3>Total Waste</h3>
                <div class="value">{dia_waste*1000:,.0f} <span class="unit">mm</span></div>
            </div>
            <div class="summary-card">
                <h3>Waste Ratio</h3>
                <div class="value">{dia_waste_pct:.1f}<span class="unit">%</span></div>
            </div>
        </div>
        ''')

        for i, plan in enumerate(plans):
            bar_svg = _generate_bar_svg(plan, i, max_bar_len)
            html_parts.append(f'<div class="bar-svg">{bar_svg}</div>')
            used_in_bar = sum(p[0] for p in plan['bin'])
            waste_in_bar = plan['bar_length'] - used_in_bar
            total_bars += 1
            total_used += used_in_bar
            total_waste += waste_in_bar

        html_parts.append('</div>')

    waste_pct = (total_waste / (total_used + total_waste)) * 100 if (total_used + total_waste) > 0 else 0.0

    html_parts.append(f"""
    <div class="total-summary">
        <div class="total-card">
            <div class="total-label">Overall Bars</div>
            <div class="total-value">{total_bars}</div>
        </div>
        <div class="total-card">
            <div class="total-label">Overall Cut Length</div>
            <div class="total-value">{total_used*1000:,.0f} mm</div>
        </div>
        <div class="total-card">
            <div class="total-label">Overall Waste</div>
            <div class="total-value">{total_waste*1000:,.0f} mm</div>
        </div>
        <div class="total-card">
            <div class="total-label">Overall Waste %</div>
            <div class="total-value">{waste_pct:.1f}%</div>
        </div>
    </div>
    """)

    # --- QR Code (includes listofer if provided) ---
    qr_data_lines = [
        f"Project: {project_name}",
        f"Client: {client_name}",
        f"Listofer: {safe_listofer}",
        f"Date: {datetime.date.today().isoformat()}"
    ]
    qr_data = "\n".join(qr_data_lines)
    qr_src = _generate_qr_image(qr_data)
    qr_img_tag = f'<img class="footer-qr" src="{qr_src}" alt="Project QR" />' if qr_src else ""

    html_parts.append(f"""
    <div class="footer">
        {qr_img_tag}
        <p><strong>{html.escape(COMPANY_INFO['name'])}</strong> – Smart Reinforcement Detailing & Cutting Optimization</p>
        <p>Report dynamically generated by <a href="{COMPANY_INFO['website']}" target="_blank">{html.escape(COMPANY_INFO['name'])}</a></p>
        <p>Technical Support: <a href="{WHATSAPP_LINK}" target="_blank">WhatsApp Chat</a></p>
    </div>
    """)

    html_parts.append("</div></body></html>")
    return "\n".join(html_parts)


def export_cutting_plan_html(
    filepath: str,
    data_by_key: Dict[Tuple[float, str], List[Tuple[float, Dict[str, Any]]]],
    stock_length: float,
    project_name: str = "",
    client_name: str = "",
    project_id: Optional[int] = None,
    plans_by_key: Optional[Dict[Tuple[float, str], List[Dict[str, Any]]]] = None,
    listofer_filter: Optional[str] = None,
    open_browser: bool = True
) -> None:
    """Generates the HTML file and opens it in the default browser."""
    html_str = generate_cutting_plan_html(
        data_by_key, stock_length, project_name, client_name,
        project_id, plans_by_key, listofer_filter
    )

    # Ensure directory exists before writing
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_str)

    if open_browser:
        webbrowser.open('file:///' + os.path.abspath(filepath).replace('\\', '/'))