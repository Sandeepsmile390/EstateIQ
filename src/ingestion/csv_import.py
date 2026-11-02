"""
EstateIQ CSV Import Engine (src/ingestion/csv_import.py).
Handles:
- Downloadable canonical CSV template generation.
- First 20 rows preview and column mapping detection.
- Detailed row-by-row validation with explicit row numbers and rejection reasons.
- Duplicate detection within batch and against database history.
- Batch tracking and rollback support.
- Audit event generation.
"""

import io
import csv
import json
import uuid
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

from src.data.canonical_db import (
    get_db_connection, insert_readings_batch, rollback_batch,
    list_facilities, list_zones, SourceType, QualityFlag
)
from src.ingestion.validation import (
    map_column_names, validate_timestamp, validate_metric_and_value, VALID_METRICS
)

CSV_TEMPLATE_HEADER = "timestamp,facility_id,zone_id,asset_id,metric_type,value,unit,source_type\n"
CSV_TEMPLATE_SAMPLES = (
    "2026-11-01T08:00:00Z,COLLEGE_01,BLOCK_A,METER_A1,energy_kwh,45.2,kWh,csv\n"
    "2026-11-01T09:00:00Z,COLLEGE_01,BLOCK_A,METER_A1,energy_kwh,58.7,kWh,csv\n"
    "2026-11-01T08:00:00Z,COLLEGE_01,BLOCK_B,FLOW_B1,water_litre,85.0,L,csv\n"
    "2026-11-01T08:00:00Z,COLLEGE_01,BLOCK_A,AQ_A1,pm25_ug_m3,32.4,µg/m³,csv\n"
    "2026-11-01T08:00:00Z,COLLEGE_01,CANTEEN,BIN_C1,waste_fill_pct,45.0,%,csv\n"
)

def get_csv_template() -> str:
    """Returns downloadable CSV template string."""
    return CSV_TEMPLATE_HEADER + CSV_TEMPLATE_SAMPLES

def preview_csv_content(csv_text_or_bytes: Union[str, bytes], limit: int = 20) -> Dict[str, Any]:
    """Previews up to first `limit` rows (default 20) and infers canonical column mapping."""
    if isinstance(csv_text_or_bytes, bytes):
        text = csv_text_or_bytes.decode("utf-8", errors="replace")
    else:
        text = csv_text_or_bytes

    f = io.StringIO(text.strip())
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        return {"error": "Empty CSV file", "columns": [], "rows": [], "detected_mapping": {}}

    detected_mapping = map_column_names(header)
    rows = []
    for i, r in enumerate(reader):
        if i >= limit:
            break
        row_dict = {}
        for idx, col_name in enumerate(header):
            row_dict[col_name] = r[idx] if idx < len(r) else ""
        rows.append(row_dict)

    return {
        "columns": header,
        "preview_rows": rows,
        "row_count_previewed": len(rows),
        "detected_mapping": detected_mapping,
        "required_fields": ["timestamp", "facility_id", "zone_id", "metric_type", "value", "unit"]
    }

def import_csv_data(
    csv_text_or_bytes: Union[str, bytes],
    selected_facility_id: str = "COLLEGE_01",
    column_mapping: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
    user_id: str = "admin",
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Validates every row in the CSV, rejects invalid rows with row numbers and exact reasons,
    deduplicates against batch and DB, and stores valid records under a tracked batch_id.
    """
    if isinstance(csv_text_or_bytes, bytes):
        text = csv_text_or_bytes.decode("utf-8", errors="replace")
    else:
        text = csv_text_or_bytes

    f = io.StringIO(text.strip())
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        return {
            "status": "REJECTED",
            "batch_id": None,
            "total_rows": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "rejected_rows": [{"row": 0, "reason": "Empty CSV content"}]
        }

    # Determine field mapping: canonical -> csv_column
    inferred_mapping = map_column_names(header)
    if column_mapping:
        inferred_mapping.update(column_mapping)

    col_to_idx = {col: idx for idx, col in enumerate(header)}
    
    # Query valid facilities and zones for reference validation
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM facilities")
    valid_facs = {r["id"].upper() for r in cur.fetchall()}
    valid_facs.add("COLLEGE_01")
    valid_facs.add("FAC_GEC_01")

    cur.execute("SELECT id, name FROM zones")
    valid_zones = set()
    for r in cur.fetchall():
        valid_zones.add(r["id"].upper())
        valid_zones.add(r["name"].upper())
    # Add common alias zones
    for z in ["BLOCK_A", "BLOCK_B", "CS_BLOCK", "ADMIN", "LIBRARY", "CANTEEN", "UTILITY", "BLD001", "BLD002", "BLD003", "BLD006", "BLD008"]:
        valid_zones.add(z)
    conn.close()

    batch_id = f"BATCH_CSV_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    accepted_readings = []
    rejected_rows = []

    seen_keys: Set[Tuple[str, str, str, str]] = set()

    # Pre-fetch existing timestamps for duplicate checks
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    for row_idx, r in enumerate(reader, start=2): # Row 1 is header
        if not r or all(c.strip() == "" for c in r):
            continue

        def get_val(field: str) -> Optional[str]:
            mapped_col = inferred_mapping.get(field)
            if mapped_col and mapped_col in col_to_idx:
                idx = col_to_idx[mapped_col]
                return r[idx].strip() if idx < len(r) else None
            return None

        # 1. Facility Reference
        fac_val = get_val("facility_id") or selected_facility_id
        if not fac_val or fac_val.upper() not in valid_facs:
            rejected_rows.append({
                "row": row_idx,
                "field": "facility_id",
                "reason": f"Unknown facility_id '{fac_val}'. Must reference configured facility."
            })
            continue

        # 2. Zone Reference
        zone_val = get_val("zone_id")
        if not zone_val:
            rejected_rows.append({"row": row_idx, "field": "zone_id", "reason": "Missing required field 'zone_id'"})
            continue
        if zone_val.upper() not in valid_zones and not any(z in zone_val.upper() for z in ["BLOCK", "HOSTEL", "CANTEEN", "LIBRARY", "BLD"]):
            rejected_rows.append({
                "row": row_idx,
                "field": "zone_id",
                "reason": f"Unknown zone_id '{zone_val}'. Must match configured campus zone."
            })
            continue

        # 3. Timestamp Validation
        raw_ts = get_val("timestamp")
        is_ts_valid, iso_ts, ts_err = validate_timestamp(raw_ts)
        if not is_ts_valid:
            rejected_rows.append({"row": row_idx, "field": "timestamp", "reason": ts_err})
            continue

        # 4. Metric Type, Value, and Unit Validation
        mtype_val = get_val("metric_type")
        val_raw = get_val("value")
        unit_val = get_val("unit")

        if not mtype_val:
            rejected_rows.append({"row": row_idx, "field": "metric_type", "reason": "Missing required field 'metric_type'"})
            continue
        if val_raw is None or val_raw == "":
            rejected_rows.append({"row": row_idx, "field": "value", "reason": "Missing required numeric field 'value'"})
            continue
        if not unit_val:
            rejected_rows.append({"row": row_idx, "field": "unit", "reason": "Missing required field 'unit'"})
            continue

        is_metric_valid, val_float, canonical_unit, metric_err = validate_metric_and_value(mtype_val, val_raw, unit_val)
        if not is_metric_valid:
            rejected_rows.append({"row": row_idx, "field": "value_or_unit", "reason": metric_err})
            continue

        # 5. Duplicate Check
        dedup_key = (fac_val.upper(), zone_val.upper(), mtype_val.lower(), iso_ts)
        if dedup_key in seen_keys:
            rejected_rows.append({
                "row": row_idx,
                "field": "duplicate",
                "reason": f"Duplicate row in batch for {zone_val}/{mtype_val} at {iso_ts}"
            })
            continue
        seen_keys.add(dedup_key)

        cur.execute(
            "SELECT id FROM readings WHERE facility_id = ? AND zone_id = ? AND metric_type = ? AND timestamp = ? LIMIT 1",
            (fac_val, zone_val, mtype_val.lower(), iso_ts)
        )
        if cur.fetchone():
            rejected_rows.append({
                "row": row_idx,
                "field": "duplicate",
                "reason": f"Record already exists in database for {zone_val}/{mtype_val} at {iso_ts}"
            })
            continue

        asset_val = get_val("asset_id")
        src_val = get_val("source_type") or SourceType.CSV

        accepted_readings.append({
            "id": f"RD_CSV_{uuid.uuid4().hex[:12]}",
            "facility_id": fac_val,
            "zone_id": zone_val,
            "asset_id": asset_val,
            "timestamp": iso_ts,
            "metric_type": mtype_val.lower(),
            "value": val_float,
            "unit": canonical_unit,
            "source_type": src_val,
            "quality_flag": QualityFlag.VALID,
            "batch_id": batch_id
        })

    conn.close()

    total_rows = len(accepted_readings) + len(rejected_rows)

    # Insert accepted readings into database
    final_accepted_count = 0
    if accepted_readings:
        insert_res = insert_readings_batch(
            readings=accepted_readings,
            batch_id=batch_id,
            facility_id=selected_facility_id,
            filename=filename or "upload.csv",
            db_path=db_path
        )
        final_accepted_count = insert_res.get("accepted_count", 0)
        for r_err in insert_res.get("rejected_rows", []):
            rejected_rows.append({"row": r_err.get("row", 0), "field": "database", "reason": r_err.get("reason", "Insert error")})

    total_rows = final_accepted_count + len(rejected_rows)

    # Record Audit Event
    audit_payload = {
        "batch_id": batch_id,
        "facility_id": selected_facility_id,
        "filename": filename,
        "total_rows": total_rows,
        "accepted_count": final_accepted_count,
        "rejected_count": len(rejected_rows)
    }
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"AUD_{uuid.uuid4().hex[:10]}",
        user_id,
        "reading_batch",
        batch_id,
        "IMPORT_CSV_BATCH",
        None,
        json.dumps(audit_payload),
        datetime.datetime.now(datetime.timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

    return {
        "status": "COMPLETED" if final_accepted_count > 0 else "FAILED",
        "batch_id": batch_id,
        "total_rows": total_rows,
        "accepted_count": final_accepted_count,
        "rejected_count": len(rejected_rows),
        "rejected_rows": rejected_rows
    }
