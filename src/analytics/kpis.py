"""
EstateIQ KPI & Resource Aggregation Engine (src/analytics/kpis.py).
Computes scoped KPIs across Energy, Water, Air Quality, and Waste:
- Total and interval consumption
- Averages, peak periods, and current indicators
- Data freshness and quality metrics
- Scoped strictly by facility_id, zone_id, and date range.
"""

import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.data.canonical_db import get_db_connection, query_readings, SourceType, QualityFlag

def calculate_facility_kpis(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Calculates scoped KPIs for the selected facility, zone, and date range."""
    readings, total_count = query_readings(
        facility_id=facility_id,
        zone_id=zone_id,
        start_time=start_time,
        end_time=end_time,
        limit=10000,
        db_path=db_path
    )

    if not readings:
        return {
            "facility_id": facility_id,
            "zone_id": zone_id,
            "period": {"start": start_time, "end": end_time},
            "status": "NO_DATA",
            "message": "No readings recorded for the selected scope.",
            "kpis": {
                "total_energy_kwh": 0.0,
                "peak_power_kw": 0.0,
                "total_water_litres": 0.0,
                "avg_pm25_ug_m3": 0.0,
                "avg_waste_fill_pct": 0.0
            },
            "data_quality": {
                "total_readings": 0,
                "valid_pct": 0.0,
                "suspect_pct": 0.0,
                "freshness_sec": 0
            },
            "provenance_breakdown": {}
        }

    df = pd.DataFrame(readings)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["dt"] = pd.to_datetime(df["timestamp"])

    # Freshness
    now_utc = pd.Timestamp.now(datetime.timezone.utc)
    latest_ts = df["dt"].max()
    if latest_ts.tzinfo is None:
        latest_ts = latest_ts.tz_localize("UTC")
    freshness_sec = max(0.0, (now_utc - latest_ts).total_seconds())

    # Energy
    df_e = df[df["metric_type"] == "energy_kwh"]
    total_energy = round(float(df_e["value"].sum()), 2) if not df_e.empty else 0.0
    peak_energy = round(float(df_e["value"].max()), 2) if not df_e.empty else 0.0

    # Water
    df_w = df[df["metric_type"] == "water_litre"]
    total_water = round(float(df_w["value"].sum()), 1) if not df_w.empty else 0.0

    # Air Quality
    df_air = df[df["metric_type"].isin(["pm25_ug_m3", "pm25"])]
    avg_pm25 = round(float(df_air["value"].mean()), 1) if not df_air.empty else 0.0

    # Waste
    df_wst = df[df["metric_type"].isin(["waste_fill_pct", "fill_level"])]
    avg_waste = round(float(df_wst["value"].mean()), 1) if not df_wst.empty else 0.0

    # Quality breakdown
    quality_counts = df["quality_flag"].value_counts().to_dict()
    valid_count = quality_counts.get(QualityFlag.VALID, 0)
    suspect_count = quality_counts.get(QualityFlag.SUSPECT, 0) + quality_counts.get(QualityFlag.STALE, 0)
    valid_pct = round((valid_count / len(df)) * 100, 1) if len(df) > 0 else 0.0

    # Provenance Breakdown
    prov_counts = df["source_type"].value_counts().to_dict()

    return {
        "facility_id": facility_id,
        "zone_id": zone_id,
        "period": {
            "start": start_time or df["timestamp"].min(),
            "end": end_time or df["timestamp"].max()
        },
        "status": "VALID",
        "kpis": {
            "total_energy_kwh": total_energy,
            "peak_power_kw": peak_energy,
            "total_water_litres": total_water,
            "avg_pm25_ug_m3": avg_pm25,
            "avg_waste_fill_pct": avg_waste
        },
        "data_quality": {
            "total_readings": len(df),
            "valid_count": valid_count,
            "suspect_count": suspect_count,
            "valid_pct": valid_pct,
            "freshness_sec": round(freshness_sec, 1),
            "stale_warning": freshness_sec > 7200  # Stale if > 2 hours
        },
        "provenance_breakdown": prov_counts
    }
