"""
EstateIQ Canonical Database Module (src/data/canonical_db.py).
Implements the final-round canonical schema and data access methods specified in EstateIQ_Final_Round_Implementation_Report.pdf:
- facilities (id, name, facility_type, timezone, config_json, active)
- zones (id, facility_id, name, zone_type, latitude, longitude)
- users (id, username, password_hash, role, facility_id, active)
- readings (id, facility_id, zone_id, asset_id, metric_type, timestamp, value, unit, source_type, quality_flag, batch_id)
- analysis_runs (id, facility_id, started_at, completed_at, status, model_versions, summary_json)
- alerts (id, run_id, facility_id, zone_id, metric_type, severity, observed_value, baseline_value, explanation, status, assignee, due_date, notes, created_at)
- scenarios (id, user_id, facility_id, inputs_json, baseline_json, scenario_json, assumptions, created_at)
- actions (id, alert_id, owner_id, status, due_at, notes, updated_at, created_at)
- audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
"""

import os
import json
import uuid
import sqlite3
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "facility_dataset" / "facility.db"

class SourceType:
    SYNTHETIC = "synthetic"
    SIMULATED_IOT = "simulated_iot"
    CSV = "csv"
    UNVERIFIED_HARDWARE = "unverified_hardware"
    SENSOR = "sensor"
    OPEN_DATASET = "open_dataset"

class QualityFlag:
    VALID = "valid"
    SUSPECT = "suspect"
    MISSING = "missing"
    STALE = "stale"
    REJECTED = "rejected"

def get_db_path() -> Path:
    env_path = os.environ.get("ESTATEIQ_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH

def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    target = Path(db_path) if db_path else get_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys=OFF;")
    return conn

def init_canonical_schema(db_path: Optional[Path] = None) -> None:
    """Ensures all canonical tables and indexes exist without dropping existing tables."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # 1. facilities - support existing legacy structure or create canonical
    cur.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        facility_type TEXT NOT NULL,
        timezone TEXT DEFAULT 'Asia/Kolkata',
        config_json TEXT,
        active INTEGER DEFAULT 1
    );
    """)
    # Check existing columns of facilities
    cur.execute("PRAGMA table_info(facilities)")
    fac_cols = [c["name"] for c in cur.fetchall()]
    if "id" not in fac_cols:
        cur.execute("ALTER TABLE facilities ADD COLUMN id TEXT;")
    if "name" not in fac_cols:
        cur.execute("ALTER TABLE facilities ADD COLUMN name TEXT;")
    if "timezone" not in fac_cols:
        cur.execute("ALTER TABLE facilities ADD COLUMN timezone TEXT DEFAULT 'Asia/Kolkata';")
    if "config_json" not in fac_cols:
        cur.execute("ALTER TABLE facilities ADD COLUMN config_json TEXT;")
    if "active" not in fac_cols:
        cur.execute("ALTER TABLE facilities ADD COLUMN active INTEGER DEFAULT 1;")
    if "facility_id" in fac_cols:
        cur.execute("UPDATE facilities SET id = facility_id WHERE id IS NULL;")
    if "facility_name" in fac_cols:
        cur.execute("UPDATE facilities SET name = facility_name WHERE name IS NULL;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        id TEXT PRIMARY KEY,
        facility_id TEXT NOT NULL,
        name TEXT NOT NULL,
        zone_type TEXT,
        latitude REAL,
        longitude REAL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        facility_id TEXT DEFAULT 'COLLEGE_01',
        active INTEGER DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id TEXT PRIMARY KEY,
        facility_id TEXT NOT NULL,
        zone_id TEXT NOT NULL,
        asset_id TEXT,
        timestamp TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        value REAL NOT NULL,
        unit TEXT NOT NULL,
        source_type TEXT NOT NULL,
        quality_flag TEXT NOT NULL,
        batch_id TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_fac_zone_metric ON readings(facility_id, zone_id, metric_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_batch ON readings(batch_id);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id TEXT PRIMARY KEY,
        facility_id TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT NOT NULL,
        model_versions TEXT,
        summary_json TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        run_id TEXT,
        facility_id TEXT NOT NULL,
        zone_id TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        observed_value REAL NOT NULL,
        baseline_value REAL NOT NULL,
        explanation TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        assignee TEXT,
        due_date TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_fac_status ON alerts(facility_id, status);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scenarios (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        facility_id TEXT NOT NULL,
        inputs_json TEXT NOT NULL,
        baseline_json TEXT NOT NULL,
        scenario_json TEXT NOT NULL,
        assumptions TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id TEXT PRIMARY KEY,
        alert_id TEXT,
        owner_id TEXT,
        status TEXT NOT NULL DEFAULT 'OPEN',
        due_at TEXT,
        notes TEXT,
        updated_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_actions_alert ON actions(alert_id);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        before_json TEXT,
        after_json TEXT,
        timestamp TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS import_batches (
        batch_id TEXT PRIMARY KEY,
        facility_id TEXT NOT NULL,
        filename TEXT,
        imported_at TEXT NOT NULL,
        total_rows INTEGER NOT NULL,
        accepted_count INTEGER NOT NULL,
        rejected_count INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

# Initialize immediately
init_canonical_schema()

# --- Repository Query Helpers ---

def get_facility(facility_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM facilities WHERE id = ? OR id = ? LIMIT 1", (facility_id, "COLLEGE_01" if facility_id == "FAC_GEC_01" else "FAC_GEC_01"))
    row = cur.fetchone()
    conn.close()
    if row:
        res = dict(row)
        if res.get("config_json"):
            try:
                res["config"] = json.loads(res["config_json"])
            except Exception:
                res["config"] = {}
        return res
    return None

def list_facilities(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM facilities WHERE active = 1")
    rows = cur.fetchall()
    facilities = []
    for r in rows:
        fac = dict(r)
        if fac.get("config_json"):
            try:
                fac["config"] = json.loads(fac["config_json"])
            except Exception:
                fac["config"] = {}
        cur.execute("SELECT * FROM zones WHERE facility_id = ? OR facility_id = ?", (fac["id"], "COLLEGE_01" if fac["id"] == "FAC_GEC_01" else "FAC_GEC_01"))
        fac["zones"] = [dict(z) for z in cur.fetchall()]
        facilities.append(fac)
    conn.close()
    return facilities

def list_zones(facility_id: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    if facility_id:
        cur.execute("SELECT * FROM zones WHERE facility_id = ? OR facility_id = ?", (facility_id, "COLLEGE_01" if facility_id == "FAC_GEC_01" else "FAC_GEC_01"))
    else:
        cur.execute("SELECT * FROM zones")
    zones = [dict(r) for r in cur.fetchall()]
    conn.close()
    return zones

def get_user_by_username(username: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE (username = ? OR id = ?) AND active = 1 LIMIT 1", (username, username))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def query_readings(
    facility_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    source_type: Optional[str] = None,
    quality_flag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[Path] = None
) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    conditions = []
    params: List[Any] = []

    if facility_id:
        conditions.append("(facility_id = ? OR facility_id = ?)")
        params.extend([facility_id, "COLLEGE_01" if facility_id == "FAC_GEC_01" else "FAC_GEC_01"])
    if zone_id:
        conditions.append("(zone_id = ? OR zone_id LIKE ?)")
        params.extend([zone_id, f"%{zone_id}%"])
    if metric_type:
        conditions.append("metric_type = ?")
        params.append(metric_type)
    if start_time:
        conditions.append("timestamp >= ?")
        params.append(start_time)
    if end_time:
        conditions.append("timestamp <= ?")
        params.append(end_time)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)
    if quality_flag:
        conditions.append("quality_flag = ?")
        params.append(quality_flag)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    cur.execute(f"SELECT COUNT(*) as total FROM readings{where_clause}", params)
    total_count = cur.fetchone()["total"]

    cur.execute(f"SELECT * FROM readings{where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?", params + [limit, offset])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows, total_count

def insert_readings_batch(
    readings: List[Dict[str, Any]],
    batch_id: str,
    facility_id: str,
    filename: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    accepted = 0
    rejected = []

    cur.execute("""
    INSERT INTO import_batches (batch_id, facility_id, filename, imported_at, total_rows, accepted_count, rejected_count, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, facility_id, filename or "batch_upload", datetime.datetime.now(datetime.timezone.utc).isoformat(), len(readings), 0, 0, "PROCESSING"))

    for idx, r in enumerate(readings, start=1):
        rid = r.get("id") or f"READ_{uuid.uuid4().hex[:12]}"
        ts = r.get("timestamp")
        mtype = r.get("metric_type")
        val = r.get("value")
        unit = r.get("unit")
        zid = r.get("zone_id")
        fid = r.get("facility_id") or facility_id
        src = r.get("source_type", SourceType.CSV)
        qflag = r.get("quality_flag", QualityFlag.VALID)
        asset_id = r.get("asset_id")

        if not ts or not mtype or val is None or not unit or not zid:
            rejected.append({"row": idx, "reason": "Missing required field (timestamp, metric_type, value, unit, zone_id)"})
            continue

        try:
            val_float = float(val)
        except (ValueError, TypeError):
            rejected.append({"row": idx, "reason": f"Value '{val}' is not a valid finite number"})
            continue

        # Check duplicate in same facility, zone, metric, timestamp
        cur.execute(
            "SELECT id FROM readings WHERE facility_id = ? AND zone_id = ? AND metric_type = ? AND timestamp = ? LIMIT 1",
            (fid, zid, mtype, ts)
        )
        if cur.fetchone():
            rejected.append({"row": idx, "reason": f"Duplicate reading for {fid}/{zid}/{mtype} at {ts}"})
            continue

        try:
            cur.execute("""
            INSERT INTO readings (id, facility_id, zone_id, asset_id, metric_type, timestamp, value, unit, source_type, quality_flag, batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rid, fid, zid, asset_id, mtype, ts, val_float, unit, src, qflag, batch_id))
            accepted += 1
        except Exception as e:
            rejected.append({"row": idx, "reason": f"DB insert error: {str(e)}"})

    cur.execute("""
    UPDATE import_batches
    SET accepted_count = ?, rejected_count = ?, status = ?
    WHERE batch_id = ?
    """, (accepted, len(rejected), "COMPLETED", batch_id))

    conn.commit()
    conn.close()

    return {
        "batch_id": batch_id,
        "total_rows": len(readings),
        "accepted_count": accepted,
        "rejected_count": len(rejected),
        "rejected_rows": rejected
    }

def rollback_batch(batch_id: str, user_id: str = "admin", db_path: Optional[Path] = None) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as cnt FROM readings WHERE batch_id = ?", (batch_id,))
    cnt = cur.fetchone()["cnt"]

    if cnt == 0:
        conn.close()
        return {"success": False, "deleted_count": 0, "message": f"Batch '{batch_id}' not found or already deleted."}

    cur.execute("DELETE FROM readings WHERE batch_id = ?", (batch_id,))
    cur.execute("UPDATE import_batches SET status = 'ROLLED_BACK' WHERE batch_id = ?", (batch_id,))

    # Record audit event
    audit_id = f"AUD_{uuid.uuid4().hex[:10]}"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (audit_id, user_id, "reading_batch", batch_id, "ROLLBACK_BATCH", json.dumps({"deleted_count": cnt}), json.dumps({"status": "ROLLED_BACK"}), now_ts))

    conn.commit()
    conn.close()
    return {"success": True, "batch_id": batch_id, "deleted_count": cnt, "message": f"Successfully rolled back batch {batch_id} ({cnt} rows removed)."}

def list_alerts(
    facility_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    metric_type: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    conditions = []
    params: List[Any] = []

    if facility_id:
        conditions.append("(facility_id = ? OR facility_id = ?)")
        params.extend([facility_id, "COLLEGE_01" if facility_id == "FAC_GEC_01" else "FAC_GEC_01"])
    if zone_id:
        conditions.append("(zone_id = ? OR zone_id LIKE ?)")
        params.extend([zone_id, f"%{zone_id}%"])
    if status:
        conditions.append("status = ?")
        params.append(status.upper())
    if severity:
        conditions.append("severity = ?")
        params.append(severity.upper())
    if metric_type:
        conditions.append("metric_type = ?")
        params.append(metric_type)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(f"SELECT * FROM alerts{where_clause} ORDER BY created_at DESC LIMIT ?", params + [limit])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_alert(alert_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts WHERE id = ? LIMIT 1", (alert_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_alert(alert_dict: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    aid = alert_dict.get("id") or f"ALT_{uuid.uuid4().hex[:10]}"
    now_ts = alert_dict.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur.execute("""
    INSERT INTO alerts (id, run_id, facility_id, zone_id, metric_type, severity, observed_value, baseline_value, explanation, status, assignee, due_date, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        aid,
        alert_dict.get("run_id"),
        alert_dict.get("facility_id", "COLLEGE_01"),
        alert_dict.get("zone_id", "BLOCK_B"),
        alert_dict.get("metric_type", "energy_kwh"),
        alert_dict.get("severity", "HIGH"),
        float(alert_dict.get("observed_value", 0.0)),
        float(alert_dict.get("baseline_value", 0.0)),
        alert_dict.get("explanation", ""),
        alert_dict.get("status", "OPEN").upper(),
        alert_dict.get("assignee"),
        alert_dict.get("due_date"),
        alert_dict.get("notes"),
        now_ts
    ))
    conn.commit()
    conn.close()
    alert_dict["id"] = aid
    alert_dict["created_at"] = now_ts
    return alert_dict

def update_alert(
    alert_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: str = "operator",
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts WHERE id = ? LIMIT 1", (alert_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    before_state = dict(row)
    updates = []
    params: List[Any] = []

    if status:
        updates.append("status = ?")
        params.append(status.upper())
    if assignee is not None:
        updates.append("assignee = ?")
        params.append(assignee)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    if updates:
        query = f"UPDATE alerts SET {', '.join(updates)} WHERE id = ?"
        params.append(alert_id)
        cur.execute(query, params)

    cur.execute("SELECT * FROM alerts WHERE id = ? LIMIT 1", (alert_id,))
    after_state = dict(cur.fetchone())

    # Record persistent audit event
    audit_id = f"AUD_{uuid.uuid4().hex[:10]}"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (audit_id, user_id, "alert", alert_id, "UPDATE_ALERT", json.dumps(before_state), json.dumps(after_state), now_ts))

    # Also sync into actions table if status is changed or action exists
    cur.execute("SELECT id FROM actions WHERE alert_id = ? LIMIT 1", (alert_id,))
    act_row = cur.fetchone()
    act_id = act_row["id"] if act_row else f"ACT_{uuid.uuid4().hex[:10]}"
    cur.execute("""
    INSERT OR REPLACE INTO actions (id, alert_id, owner_id, status, due_at, notes, updated_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM actions WHERE id = ?), ?))
    """, (
        act_id,
        alert_id,
        assignee or after_state.get("assignee") or user_id,
        after_state.get("status", "OPEN"),
        due_date or after_state.get("due_date"),
        notes or after_state.get("notes"),
        now_ts,
        act_id,
        now_ts
    ))

    conn.commit()
    conn.close()
    return after_state

def create_action(
    alert_id: str,
    owner_id: str,
    status: str = "OPEN",
    notes: Optional[str] = None,
    due_at: Optional[str] = None,
    user_id: str = "operator",
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    action_id = f"ACT_{uuid.uuid4().hex[:10]}"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur.execute("""
    INSERT INTO actions (id, alert_id, owner_id, status, due_at, notes, updated_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (action_id, alert_id, owner_id, status.upper(), due_at, notes or "", now_ts, now_ts))

    # Update associated alert status and assignee if applicable
    if alert_id:
        cur.execute("UPDATE alerts SET status = ?, assignee = ?, notes = COALESCE(?, notes) WHERE id = ?", (status.upper(), owner_id, notes, alert_id))

    # Record persistent audit event
    audit_id = f"AUD_{uuid.uuid4().hex[:10]}"
    cur.execute("""
    INSERT INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (audit_id, user_id, "action", action_id, "CREATE_ACTION", None, json.dumps({
        "action_id": action_id, "alert_id": alert_id, "owner_id": owner_id, "status": status.upper()
    }), now_ts))

    conn.commit()
    conn.close()

    return {
        "id": action_id,
        "action_id": action_id,
        "alert_id": alert_id,
        "owner_id": owner_id,
        "status": status.upper(),
        "due_at": due_at,
        "notes": notes,
        "created_at": now_ts,
        "updated_at": now_ts
    }

def list_actions(alert_id: Optional[str] = None, owner_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []

    if alert_id:
        conditions.append("alert_id = ?")
        params.append(alert_id)
    if owner_id:
        conditions.append("owner_id = ?")
        params.append(owner_id)
    if status:
        conditions.append("status = ?")
        params.append(status.upper())

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(f"SELECT * FROM actions{where_clause} ORDER BY updated_at DESC LIMIT ?", params + [limit])
    actions = [dict(r) for r in cur.fetchall()]
    conn.close()
    return actions

def record_audit_event(
    user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    before_json: Optional[Union[str, Dict]] = None,
    after_json: Optional[Union[str, Dict]] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    audit_id = f"AUD_{uuid.uuid4().hex[:10]}"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    b_str = json.dumps(before_json) if isinstance(before_json, dict) else before_json
    a_str = json.dumps(after_json) if isinstance(after_json, dict) else after_json

    cur.execute("""
    INSERT INTO audit_events (id, user_id, entity_type, entity_id, action, before_json, after_json, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (audit_id, user_id, entity_type, entity_id, action, b_str, a_str, now_ts))
    conn.commit()
    conn.close()

    return {
        "id": audit_id,
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "timestamp": now_ts
    }

def list_audit_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []

    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)
    if entity_id:
        conditions.append("entity_id = ?")
        params.append(entity_id)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(f"SELECT * FROM audit_events{where_clause} ORDER BY timestamp DESC LIMIT ?", params + [limit])
    events = [dict(r) for r in cur.fetchall()]
    conn.close()
    return events

def record_analysis_run(
    facility_id: str,
    status: str,
    model_versions: Dict[str, Any],
    summary: Dict[str, Any],
    started_at: str,
    completed_at: str,
    db_path: Optional[Path] = None
) -> str:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    run_id = f"RUN_{uuid.uuid4().hex[:10]}"
    cur.execute("""
    INSERT INTO analysis_runs (id, facility_id, started_at, completed_at, status, model_versions, summary_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (run_id, facility_id, started_at, completed_at, status, json.dumps(model_versions), json.dumps(summary)))
    conn.commit()
    conn.close()
    return run_id

def record_scenario(
    user_id: str,
    facility_id: str,
    inputs: Dict[str, Any],
    baseline: Dict[str, Any],
    scenario: Dict[str, Any],
    assumptions: List[str],
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    scen_id = f"SCEN_{uuid.uuid4().hex[:10]}"
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO scenarios (id, user_id, facility_id, inputs_json, baseline_json, scenario_json, assumptions, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (scen_id, user_id, facility_id, json.dumps(inputs), json.dumps(baseline), json.dumps(scenario), json.dumps(assumptions), now_ts))
    conn.commit()
    conn.close()
    return {
        "id": scen_id,
        "user_id": user_id,
        "facility_id": facility_id,
        "inputs": inputs,
        "baseline": baseline,
        "scenario": scenario,
        "assumptions": assumptions,
        "created_at": now_ts
    }
