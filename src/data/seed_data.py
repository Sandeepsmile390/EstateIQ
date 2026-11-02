"""
EstateIQ Deterministic Demo Seeder & Reset Engine (src/data/seed_data.py).
Creates a repeatable local campus dataset with known energy, water, air, and waste anomalies.
Works completely offline without external AI, cloud services, or physical hardware.
Labels all generated demo data with source_type: 'synthetic'.
"""

import os
import json
import uuid
import datetime
import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.data.canonical_db import (
    get_db_connection, init_canonical_schema, SourceType, QualityFlag
)
from src.security.password import hash_password

def seed_demo_dataset(db_path: Optional[Path] = None, seed: int = 42) -> Dict[str, Any]:
    """Seeds database with deterministic campus data, known anomalies, and initial workflow state."""
    init_canonical_schema(db_path)
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # 1. Seed Facilities
    campus_config = {
        "energy_tariff_inr_per_kwh": 9.50,
        "anomaly_baseline_days": 14,
        "energy_anomaly_percent": 25.0,
        "water_closed_hours": "00:00-05:00",
        "waste_collection_threshold_pct": 90.0,
        "air_metric_limits": {
            "pm25_ug_m3": 60.0,
            "pm10_ug_m3": 100.0
        },
        "operating_hours": "08:00-18:00"
    }
    config_json = json.dumps(campus_config)

    facilities_data = [
        ("COLLEGE_01", "GEC Smart Campus", "engineering_college", "Asia/Kolkata", config_json, 1),
        ("FAC_GEC_01", "GEC Smart Campus", "engineering_college", "Asia/Kolkata", config_json, 1)
    ]
    cur.execute("PRAGMA table_info(facilities)")
    fac_cols = [c["name"] for c in cur.fetchall()]
    for fid, name, ftype, tz, cfg, act in facilities_data:
        if "facility_id" in fac_cols:
            cur.execute("""
            INSERT OR REPLACE INTO facilities (id, facility_id, name, facility_name, facility_type, timezone, config_json, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fid, fid, name, name, ftype, tz, cfg, act))
        else:
            cur.execute("""
            INSERT OR REPLACE INTO facilities (id, name, facility_type, timezone, config_json, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (fid, name, ftype, tz, cfg, act))

    # 2. Seed Zones
    zones_data = [
        ("BLOCK_A", "COLLEGE_01", "Academic Block A", "Academic", 18.5204, 73.8567),
        ("BLOCK_B", "COLLEGE_01", "Block B Hostel", "Hostel", 18.5210, 73.8572),
        ("CS_BLOCK", "COLLEGE_01", "Computer Science Block", "Academic", 18.5215, 73.8560),
        ("ADMIN", "COLLEGE_01", "Administration Block", "Admin", 18.5198, 73.8555),
        ("LIBRARY", "COLLEGE_01", "Central Library", "Library", 18.5208, 73.8550),
        ("CANTEEN", "COLLEGE_01", "Central Cafeteria", "Canteen", 18.5212, 73.8580),
        ("UTILITY", "COLLEGE_01", "Central Utility Building", "Utility", 18.5220, 73.8590),
        # Alias zones for FAC_GEC_01
        ("BLOCK_A_FAC", "FAC_GEC_01", "Academic Block A", "Academic", 18.5204, 73.8567),
        ("BLOCK_B_FAC", "FAC_GEC_01", "Block B Hostel", "Hostel", 18.5210, 73.8572),
        ("BLD001", "COLLEGE_01", "Academic Block A", "Academic", 18.5204, 73.8567),
        ("BLD002", "COLLEGE_01", "Academic Block B", "Academic", 18.5210, 73.8570),
        ("BLD003", "COLLEGE_01", "Computer Science Block", "Academic", 18.5215, 73.8560),
        ("BLD006", "COLLEGE_01", "Block B Hostel", "Hostel", 18.5210, 73.8572),
        ("BLD008", "COLLEGE_01", "Central Cafeteria", "Canteen", 18.5212, 73.8580)
    ]
    for zid, fid, zname, ztype, lat, lon in zones_data:
        cur.execute("""
        INSERT OR REPLACE INTO zones (id, facility_id, name, zone_type, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (zid, fid, zname, ztype, lat, lon))

    # 3. Seed Users with Argon2id Password Hashes
    users_data = [
        ("USR_ADMIN_01", "admin", hash_password("Admin@123456"), "administrator", "COLLEGE_01", 1),
        ("USR_ADMIN_02", "admin@estateiq.in", hash_password("Admin@123456"), "administrator", "COLLEGE_01", 1),
        ("USR_LEAD_01", "lead@estateiq.in", hash_password("Lead@123456"), "administrator", "COLLEGE_01", 1),
        ("USR_OPS_01", "operations", hash_password("Engineer@123"), "operations", "COLLEGE_01", 1),
        ("USR_OPS_02", "alex.chen@estateiq.in", hash_password("Engineer@123"), "operations", "COLLEGE_01", 1),
        ("USR_SUST_01", "sustainability", hash_password("Auditor@123"), "sustainability", "COLLEGE_01", 1),
        ("USR_SUST_02", "priya.sharma@estateiq.in", hash_password("Auditor@123"), "sustainability", "COLLEGE_01", 1),
        ("USR_VIEW_01", "viewer", hash_password("Viewer@123"), "viewer", "COLLEGE_01", 1),
        ("USR_VIEW_02", "sam.taylor@estateiq.in", hash_password("Viewer@123"), "viewer", "COLLEGE_01", 1)
    ]
    for uid, uname, pwd_hash, urole, ufac, uact in users_data:
        cur.execute("""
        INSERT OR REPLACE INTO users (id, username, password_hash, role, facility_id, active)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (uid, uname, pwd_hash, urole, ufac, uact))

    # 4. Generate 14-Day Deterministic Hourly Readings
    np.random.seed(seed)
    base_time = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0) - datetime.timedelta(days=14)
    batch_id = "BATCH_SEED_INIT_001"

    # Clean existing seed readings
    cur.execute("DELETE FROM readings WHERE batch_id = ?", (batch_id,))

    readings_to_insert = []
    
    # Generate 14 days * 24 hours = 336 steps
    for step in range(336):
        current_dt = base_time + datetime.timedelta(hours=step)
        ts_str = current_dt.isoformat()
        hour = current_dt.hour
        is_weekend = current_dt.weekday() >= 5

        # Academic diurnal curve (peak 10:00 - 16:00)
        academic_profile = max(0.15, np.sin((hour - 6) * np.pi / 14)) if 7 <= hour <= 20 else 0.15
        if is_weekend:
            academic_profile *= 0.35

        # Hostel curve (morning peak 06:00 - 09:00, evening peak 18:00 - 23:00)
        hostel_profile = 0.70 if (6 <= hour <= 9 or 18 <= hour <= 23) else 0.30

        # BLOCK_A Energy
        e_a = round(float(45.0 + 80.0 * academic_profile + np.random.normal(0, 2.5)), 2)
        readings_to_insert.append((f"RD_E_A_{step}", "COLLEGE_01", "BLOCK_A", "METER_A", "energy_kwh", ts_str, max(5.0, e_a), "kWh", SourceType.SYNTHETIC, QualityFlag.VALID, batch_id))

        # BLOCK_B Energy (Hostel) - with known injected anomaly at 24 hours ago
        e_b = round(float(35.0 + 65.0 * hostel_profile + np.random.normal(0, 2.0)), 2)
        q_b = QualityFlag.VALID
        if step == 312:  # 24 hours ago: known critical energy spike
            e_b = 145.2  # Expected baseline ~78.0 kWh (+86.1%)
        readings_to_insert.append((f"RD_E_B_{step}", "COLLEGE_01", "BLOCK_B", "METER_B", "energy_kwh", ts_str, max(5.0, e_b), "kWh", SourceType.SYNTHETIC, q_b, batch_id))

        # BLOCK_B Water (Hostel) - with known overnight leak at 36 hours ago (02:00)
        w_b = round(float(80.0 + 250.0 * hostel_profile + np.random.normal(0, 10.0)), 1)
        if step == 302 and 2 <= hour <= 5:  # Overnight leak
            w_b = 380.0  # Normal overnight flow is ~25 L
        readings_to_insert.append((f"RD_W_B_{step}", "COLLEGE_01", "BLOCK_B", "FLOW_B", "water_litre", ts_str, max(5.0, w_b), "L", SourceType.SYNTHETIC, QualityFlag.VALID, batch_id))

        # CANTEEN Waste Fill Level
        fill_pct = min(100.0, round(float(30.0 + (step % 24) * 3.2 + np.random.normal(0, 1.5)), 1))
        if step >= 330:  # Recent hours near overflow
            fill_pct = 94.0
        readings_to_insert.append((f"RD_WST_C_{step}", "COLLEGE_01", "CANTEEN", "BIN_C01", "waste_fill_pct", ts_str, fill_pct, "%", SourceType.SYNTHETIC, QualityFlag.VALID, batch_id))

        # BLOCK_A PM2.5 Air Quality
        pm25 = round(float(35.0 + 15.0 * np.sin(hour * np.pi / 12) + np.random.normal(0, 3.0)), 1)
        if step == 332:  # High air pollution reading
            pm25 = 142.5
        readings_to_insert.append((f"RD_AIR_A_{step}", "COLLEGE_01", "BLOCK_A", "AQ_A01", "pm25_ug_m3", ts_str, max(5.0, pm25), "µg/m³", SourceType.SYNTHETIC, QualityFlag.VALID, batch_id))

    # Insert all readings in batch
    cur.executemany("""
    INSERT INTO readings (id, facility_id, zone_id, asset_id, metric_type, timestamp, value, unit, source_type, quality_flag, batch_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, readings_to_insert)

    # 5. Record Initial Analysis Run & Known Alerts
    run_id = "RUN_SEED_001"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
    INSERT OR REPLACE INTO analysis_runs (id, facility_id, started_at, completed_at, status, model_versions, summary_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        "COLLEGE_01",
        (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)).isoformat(),
        now_ts,
        "SUCCESS",
        json.dumps({"energy_model": "SeasonalMedian_MAD", "water_model": "ClosedHoursFlowRule", "waste_model": "FillRateProjection"}),
        json.dumps({"anomalies_detected": 4, "total_series_analyzed": 4})
    ))

    # Seed Initial Alerts
    alerts_data = [
        (
            "ALT_E01",
            run_id,
            "COLLEGE_01",
            "BLOCK_B",
            "energy_kwh",
            "CRITICAL",
            145.2,
            78.0,
            "Observed load 145.2 kWh exceeds same-hour contextual baseline (78.0 kWh) by +86.1%. Potential HVAC stuck on full cooling during off-peak hours.",
            "OPEN",
            "alex.chen@estateiq.in",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()[:10],
            "Investigate Block B chiller unit setpoint and air handling schedule.",
            now_ts
        ),
        (
            "ALT_W01",
            run_id,
            "COLLEGE_01",
            "BLOCK_B",
            "water_litre",
            "HIGH",
            380.0,
            25.0,
            "High overnight flow rate (380.0 L/hr) detected during closed hours (00:00-05:00). Expected baseline < 25 L/hr. Probable flush valve leak or pipe rupture.",
            "OPEN",
            "alex.chen@estateiq.in",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()[:10],
            "Inspect restroom block B second floor plumbing manifold.",
            now_ts
        ),
        (
            "ALT_WST01",
            run_id,
            "COLLEGE_01",
            "CANTEEN",
            "waste_fill_pct",
            "HIGH",
            94.0,
            90.0,
            "Bin fill level reached 94.0% with projection to 100% overflow within 45 minutes. Priority collection dispatch required.",
            "OPEN",
            "arjun.kumar@estateiq.in",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).isoformat()[:10],
            "Dispatch waste collection team to Central Cafeteria.",
            now_ts
        ),
        (
            "ALT_AIR01",
            run_id,
            "COLLEGE_01",
            "BLOCK_A",
            "pm25_ug_m3",
            "HIGH",
            142.5,
            60.0,
            "PM2.5 reading 142.5 µg/m³ exceeds facility threshold (60.0 µg/m³). Recommend indoor air filtering inspection.",
            "OPEN",
            "priya.sharma@estateiq.in",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)).isoformat()[:10],
            "Review ventilation dampers and filter condition in Block A.",
            now_ts
        )
    ]
    for aid, rid, fid, zid, mtype, sev, obs, base, expl, stt, asgn, due, notes, created in alerts_data:
        cur.execute("""
        INSERT OR REPLACE INTO alerts (id, run_id, facility_id, zone_id, metric_type, severity, observed_value, baseline_value, explanation, status, assignee, due_date, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (aid, rid, fid, zid, mtype, sev, obs, base, expl, stt, asgn, due, notes, created))

    # Seed Initial Actions linked to Alerts
    actions_data = [
        (
            "ACT_E01",
            "ALT_E01",
            "alex.chen@estateiq.in",
            "ASSIGNED",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()[:10],
            "Assigned to HVAC technician. Thermostat setpoint reset recommended.",
            now_ts,
            now_ts
        ),
        (
            "ACT_W01",
            "ALT_W01",
            "alex.chen@estateiq.in",
            "OPEN",
            (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()[:10],
            "Pending plumbing team dispatch.",
            now_ts,
            now_ts
        )
    ]
    for act_id, alt_id, owner, stt, due, notes, upd, crt in actions_data:
        cur.execute("""
        INSERT OR REPLACE INTO actions (id, alert_id, owner_id, status, due_at, notes, updated_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (act_id, alt_id, owner, stt, due, notes, upd, crt))

    # Seed Initial Audit Log
    cur.execute("""
    INSERT OR REPLACE INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "AUD_INIT_001",
        "admin",
        "system",
        "COLLEGE_01",
        "SEED_DEMO_DATASET",
        None,
        json.dumps({"facilities": len(facilities_data), "zones": len(zones_data), "readings": len(readings_to_insert), "alerts": len(alerts_data)}),
        now_ts
    ))

    conn.commit()
    conn.close()

    return {
        "status": "SEEDED",
        "facility_id": "COLLEGE_01",
        "facility_name": "GEC Smart Campus",
        "zones_seeded": len(zones_data),
        "readings_seeded": len(readings_to_insert),
        "alerts_seeded": len(alerts_data),
        "actions_seeded": len(actions_data),
        "batch_id": batch_id,
        "injected_anomalies": [
            "Energy Spike: BLOCK_B at 145.2 kWh (+86.1% over 78.0 kWh baseline)",
            "Water Overnight Leak: BLOCK_B at 380 L/hr during closed hours (00:00-05:00)",
            "Waste Overflow: CANTEEN at 94% fill with projection < 1h",
            "Air Quality Spike: BLOCK_A PM2.5 at 142.5 µg/m³"
        ]
    }

def reset_demo_dataset(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Resets the demo environment cleanly back to initial deterministic seeded state."""
    init_canonical_schema(db_path)
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # Clear dynamically modified operational data while retaining baseline structure
    cur.execute("DELETE FROM alerts;")
    cur.execute("DELETE FROM actions;")
    cur.execute("DELETE FROM audit_events;")
    cur.execute("DELETE FROM scenarios;")
    cur.execute("DELETE FROM analysis_runs;")
    cur.execute("DELETE FROM readings WHERE batch_id != 'BATCH_SEED_INIT_001';")
    cur.execute("DELETE FROM import_batches;")

    conn.commit()
    conn.close()

    # Re-seed deterministic baseline
    return seed_demo_dataset(db_path=db_path)
