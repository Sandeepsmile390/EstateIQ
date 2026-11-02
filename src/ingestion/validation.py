"""
EstateIQ Ingestion Validation Module (src/ingestion/validation.py).
Validates canonical telemetry readings and imported CSV rows:
- Checks required fields, timestamp formatting, units, numeric finite bounds, metric ranges.
- Checks facility and zone references against configured database.
- Detects duplicate records within batch and against database history.
- Distinguishes source types and quality flags.
- Never silently replaces missing values with zero.
"""

import math
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Set

VALID_METRICS = {
    "energy_kwh": {"units": ["kwh", "kwh"], "min": 0.0, "max": 100000.0, "canonical_unit": "kWh"},
    "power_kw": {"units": ["kw", "kw"], "min": 0.0, "max": 50000.0, "canonical_unit": "kW"},
    "water_litre": {"units": ["l", "liters", "litres", "litre"], "min": 0.0, "max": 1000000.0, "canonical_unit": "L"},
    "water_flow_lpm": {"units": ["lpm", "l/min", "lmin"], "min": 0.0, "max": 5000.0, "canonical_unit": "L/min"},
    "pm25_ug_m3": {"units": ["µg/m³", "ug/m3", "ug/m^3", "µg/m3"], "min": 0.0, "max": 1000.0, "canonical_unit": "µg/m³"},
    "pm10_ug_m3": {"units": ["µg/m³", "ug/m3", "ug/m^3", "µg/m3"], "min": 0.0, "max": 2000.0, "canonical_unit": "µg/m³"},
    "waste_fill_pct": {"units": ["%", "percent", "pct"], "min": 0.0, "max": 100.0, "canonical_unit": "%"}
}

CANONICAL_COLUMN_SYNONYMS = {
    "timestamp": ["timestamp", "time", "datetime", "date_time", "ts", "event_timestamp"],
    "facility_id": ["facility_id", "facility", "fac_id", "campus_id", "site_id"],
    "zone_id": ["zone_id", "zone", "building_id", "building", "location_id", "location"],
    "asset_id": ["asset_id", "asset", "meter_id", "meter", "device_id", "device"],
    "metric_type": ["metric_type", "metric", "type", "parameter", "signal", "variable"],
    "value": ["value", "reading", "val", "measurement", "amount"],
    "unit": ["unit", "uom", "units", "unit_of_measure"],
    "source_type": ["source_type", "source", "origin", "data_source"]
}

def map_column_names(columns: List[str]) -> Dict[str, str]:
    """Maps arbitrary incoming CSV header names to canonical schema fields."""
    mapping = {}
    lower_cols = {c.strip().lower(): c for c in columns}
    for canonical, synonyms in CANONICAL_COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if syn in lower_cols:
                mapping[canonical] = lower_cols[syn]
                break
    return mapping

def validate_timestamp(ts_val: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validates and normalizes timestamp to ISO 8601 UTC string."""
    if ts_val is None or pd.isna(ts_val):
        return False, None, "Missing timestamp value"
    ts_str = str(ts_val).strip()
    if not ts_str:
        return False, None, "Empty timestamp string"
    try:
        dt = pd.to_datetime(ts_str)
        if dt is pd.NaT:
            return False, None, f"Invalid date/time format '{ts_str}'"
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        else:
            dt = dt.tz_convert("UTC")
        return True, dt.isoformat(), None
    except Exception as e:
        return False, None, f"Cannot parse timestamp '{ts_str}': {str(e)}"

def validate_metric_and_value(metric_type: str, value: Any, unit: str) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
    """Validates metric type existence, numeric finiteness, unit conformity, and allowable range bounds."""
    m_clean = str(metric_type).strip().lower() if metric_type else ""
    if m_clean not in VALID_METRICS:
        return False, None, None, f"Unknown metric_type '{metric_type}'. Supported: {list(VALID_METRICS.keys())}"

    spec = VALID_METRICS[m_clean]
    u_clean = str(unit).strip().lower() if unit else ""
    if u_clean not in [u.lower() for u in spec["units"]]:
        return False, None, None, f"Invalid unit '{unit}' for metric '{metric_type}'. Expected one of: {spec['units']}"

    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return False, None, None, f"Value '{value}' is not a valid numeric value"

    if math.isnan(val_float) or math.isinf(val_float):
        return False, None, None, f"Value '{value}' must be finite (not NaN or Inf)"

    if val_float < spec["min"] or val_float > spec["max"]:
        return False, None, None, f"Value {val_float} out of permissible range [{spec['min']}, {spec['max']}] for {metric_type}"

    return True, val_float, spec["canonical_unit"], None
