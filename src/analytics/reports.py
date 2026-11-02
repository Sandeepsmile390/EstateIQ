"""
EstateIQ Reporting & Scoped Export Engine (src/analytics/reports.py).
Generates scoped summary reports, CSV exports, and printable HTML views:
- Strictly filters by facility_id, zone_id, metric_type, and date range.
- Includes data provenance labels, quality health status, model evaluation metrics, and action history.
- Explicitly documents assumptions and limitations:
  "Operational indicator; not an official government certification or verified savings."
"""

import io
import csv
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.data.canonical_db import (
    get_facility, list_zones, query_readings, list_alerts, list_actions, SourceType
)
from src.analytics.kpis import calculate_facility_kpis
from src.analytics.forecast import generate_energy_forecast

def generate_report_summary(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Compiles a scoped facility-period executive report."""
    fac = get_facility(facility_id, db_path=db_path) or {
        "id": facility_id, "name": "GEC Smart Campus", "timezone": "Asia/Kolkata"
    }

    # KPIs
    kpi_res = calculate_facility_kpis(
        facility_id=facility_id,
        zone_id=zone_id,
        start_time=start_time,
        end_time=end_time,
        db_path=db_path
    )

    # Scoped Alerts
    alerts = list_alerts(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        limit=50,
        db_path=db_path
    )

    # Scoped Actions
    actions = list_actions(limit=50, db_path=db_path)
    # Filter actions belonging to scoped alerts
    alert_ids = {a["id"] for a in alerts}
    scoped_actions = [act for act in actions if act.get("alert_id") in alert_ids] if alert_ids else actions[:10]

    # Model evaluation metrics
    forecast_data = generate_energy_forecast(
        facility_id=facility_id,
        zone_id=zone_id,
        horizon_hours=24,
        db_path=db_path
    )

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "report_id": f"REP_{facility_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "generated_at": now_str,
        "scope": {
            "facility_id": facility_id,
            "facility_name": fac.get("name", "GEC Smart Campus"),
            "facility_type": fac.get("facility_type", "engineering_college"),
            "zone_id": zone_id or "All Campus Zones",
            "metric_type": metric_type or "All Configured Metrics",
            "start_time": start_time or kpi_res["period"]["start"],
            "end_time": end_time or kpi_res["period"]["end"]
        },
        "kpis": kpi_res["kpis"],
        "data_quality": kpi_res["data_quality"],
        "provenance_labels": kpi_res["provenance_breakdown"],
        "model_performance": {
            "algorithm": forecast_data.get("algorithm"),
            "status": forecast_data.get("model_status"),
            "metrics": forecast_data.get("metrics")
        },
        "alerts_summary": {
            "total_alerts": len(alerts),
            "critical_count": sum(1 for a in alerts if a.get("severity") == "CRITICAL"),
            "high_count": sum(1 for a in alerts if a.get("severity") == "HIGH"),
            "open_count": sum(1 for a in alerts if a.get("status") == "OPEN"),
            "recent_alerts": alerts[:10]
        },
        "actions_summary": {
            "total_actions": len(scoped_actions),
            "recent_actions": scoped_actions[:10]
        },
        "assumptions": [
            "Campus baseline energy tariff: ₹9.50/kWh",
            "Diurnal load profiles and closed-hours water flow derived from historical observations",
            "Forecast and what-if numbers are analytical estimates for decision support"
        ],
        "limitations": [
            "Prototype operational indicator; not an official government sustainability certification or regulatory rating.",
            "Simulated readings and scenario deltas do not constitute verified contractual utility savings.",
            "SHAP and rule contributions indicate model feature associations and do not prove direct physical causality."
        ]
    }

def export_readings_csv(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db_path: Optional[Path] = None
) -> str:
    """Exports filtered readings to standard CSV formatted string."""
    readings, _ = query_readings(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time,
        limit=50000,
        db_path=db_path
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "facility_id", "zone_id", "asset_id", "metric_type", "timestamp", "value", "unit", "source_type", "quality_flag", "batch_id"])

    for r in readings:
        writer.writerow([
            r.get("id"),
            r.get("facility_id"),
            r.get("zone_id"),
            r.get("asset_id") or "",
            r.get("metric_type"),
            r.get("timestamp"),
            r.get("value"),
            r.get("unit"),
            r.get("source_type"),
            r.get("quality_flag"),
            r.get("batch_id")
        ])

    return output.getvalue()

def generate_printable_html_report(report_data: Dict[str, Any]) -> str:
    """Generates standalone print-ready HTML report with styling and disclaimers."""
    scope = report_data["scope"]
    kpis = report_data["kpis"]
    dq = report_data["data_quality"]
    alerts = report_data["alerts_summary"]["recent_alerts"]
    actions = report_data["actions_summary"]["recent_actions"]

    alerts_rows = "".join([
        f"<tr><td>{a.get('severity')}</td><td>{a.get('zone_id')}</td><td>{a.get('metric_type')}</td><td>{a.get('observed_value')}</td><td>{a.get('baseline_value')}</td><td>{a.get('status')}</td><td>{a.get('explanation')[:80]}...</td></tr>"
        for a in alerts[:8]
    ]) if alerts else "<tr><td colspan='7'>No active alerts in this scope.</td></tr>"

    actions_rows = "".join([
        f"<tr><td>{act.get('id')}</td><td>{act.get('owner_id')}</td><td>{act.get('status')}</td><td>{act.get('due_at') or 'N/A'}</td><td>{act.get('notes') or ''}</td></tr>"
        for act in actions[:8]
    ]) if actions else "<tr><td colspan='5'>No recorded actions in this scope.</td></tr>"

    prov_badges = " ".join([f"<span class='badge'>{src}: {cnt}</span>" for src, cnt in report_data.get("provenance_labels", {}).items()])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EstateIQ Executive Facility Report - {scope['facility_name']}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; background: #fff; }}
  h1 {{ color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 8px; margin-bottom: 4px; }}
  .header {{ margin-bottom: 24px; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
  .meta-item {{ font-size: 0.85rem; }}
  .meta-item b {{ display: block; color: #64748b; font-size: 0.75rem; text-transform: uppercase; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }}
  .kpi-card {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px; text-align: center; }}
  .kpi-val {{ font-size: 1.4rem; font-weight: bold; color: #15803d; }}
  .kpi-lbl {{ font-size: 0.75rem; color: #166534; text-transform: uppercase; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 0.85rem; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
  th {{ background: #f1f5f9; color: #334155; }}
  .badge {{ background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; display: inline-block; margin-right: 4px; }}
  .disclaimer {{ background: #fffbeb; border: 1px solid #fde68a; color: #92400e; padding: 14px; border-radius: 8px; font-size: 0.8rem; margin-top: 24px; }}
  @media print {{
    body {{ margin: 15mm; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div class="no-print" style="float: right;">
    <button onclick="window.print()" style="background:#0f766e; color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:600;">Print / Save as PDF</button>
  </div>
  <h1>EstateIQ Sustainable Facility Executive Summary</h1>
  <p style="color: #64748b; margin: 0;">Scope-Specific Operational & Decision Intelligence Report | Generated: {report_data['generated_at'][:19]} UTC</p>
</div>

<div class="meta-grid">
  <div class="meta-item"><b>Facility</b>{scope['facility_name']} ({scope['facility_id']})</div>
  <div class="meta-item"><b>Zone / Building</b>{scope['zone_id']}</div>
  <div class="meta-item"><b>Date Scope</b>{str(scope['start_time'])[:16]} to {str(scope['end_time'])[:16]}</div>
  <div class="meta-item"><b>Data Freshness</b>{dq['freshness_sec']}s ({dq['valid_pct']}% Valid)</div>
</div>

<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-val">{kpis['total_energy_kwh']:,.1f}</div><div class="kpi-lbl">Total Energy (kWh)</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['peak_power_kw']:,.1f}</div><div class="kpi-lbl">Peak Load (kW)</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['total_water_litres']:,.0f}</div><div class="kpi-lbl">Total Water (L)</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['avg_pm25_ug_m3']:.1f}</div><div class="kpi-lbl">Avg PM2.5 (µg/m³)</div></div>
  <div class="kpi-card"><div class="kpi-val">{kpis['avg_waste_fill_pct']:.1f}%</div><div class="kpi-lbl">Waste Fill Avg</div></div>
</div>

<p><b>Data Provenance:</b> {prov_badges or 'Synthetic campus demo data'}</p>

<h3>Recent Evidence-Backed Anomaly Alerts</h3>
<table>
  <thead>
    <tr><th>Severity</th><th>Zone</th><th>Metric</th><th>Observed</th><th>Baseline</th><th>Status</th><th>Explanation</th></tr>
  </thead>
  <tbody>
    {alerts_rows}
  </tbody>
</table>

<h3>Operational Intervention & Action History</h3>
<table>
  <thead>
    <tr><th>Action ID</th><th>Owner</th><th>Status</th><th>Due Date</th><th>Notes</th></tr>
  </thead>
  <tbody>
    {actions_rows}
  </tbody>
</table>

<div class="disclaimer">
  <b>Important Operational Disclaimers & Assumptions:</b>
  <ul style="margin: 6px 0 0 16px; padding: 0;">
    <li><b>Prototype Indicator:</b> Operational indicator for campus decision-support; not an official government sustainability certification or regulatory rating.</li>
    <li><b>Estimate, Not Verified Savings:</b> Baseline, scenario, and forecast values are analytical estimates. Field measurement and verification (M&V) is required before claiming verified operational savings.</li>
    <li><b>No Direct Control:</b> Recommendations require human authorization; no automatic control of high-voltage HVAC, pumps, or valves is executed.</li>
  </ul>
</div>
</body>
</html>"""
    return html
