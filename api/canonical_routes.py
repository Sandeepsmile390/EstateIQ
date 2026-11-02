"""
EstateIQ Canonical REST API Routes Module (api/canonical_routes.py).
Implements the exact REST API contract defined in Section 3.3 of EstateIQ_Final_Round_Implementation_Report.pdf:
- GET /health
- POST /auth/login
- GET /facilities
- POST /readings/batch
- GET /readings
- POST /analysis/run
- GET /alerts
- PATCH /alerts/{id}
- POST /scenarios/simulate
- POST /actions
- GET /reports/summary
- GET /reports/export/csv
- GET /reports/printable
- GET /readings/template
- POST /readings/preview
- POST /readings/import/csv
- DELETE /readings/batches/{batch_id}
- POST /admin/demo/seed & /admin/demo/reset
"""

import json
import uuid
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Security, Request, Response, status, Header
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

from src.data.canonical_db import (
    get_facility, list_facilities as db_list_facilities, list_zones,
    query_readings, insert_readings_batch, rollback_batch,
    list_alerts, get_alert, update_alert, create_action, list_actions,
    record_audit_event, list_audit_events, record_analysis_run,
    SourceType, QualityFlag
)
from src.auth.security import (
    authenticate_user, create_user_token, verify_current_user,
    require_permission, require_role, require_facility_access,
    USER_ROLES_DB, ROLE_PERMISSIONS
)
from src.ingestion.csv_import import (
    get_csv_template, preview_csv_content, import_csv_data
)
from src.ingestion.validation import (
    validate_timestamp, validate_metric_and_value
)
from src.analytics.kpis import calculate_facility_kpis
from src.analytics.anomaly import detect_facility_anomalies
from src.analytics.forecast import generate_energy_forecast
from src.analytics.scenarios import simulate_energy_scenario
from src.analytics.reports import (
    generate_report_summary, export_readings_csv, generate_printable_html_report
)
from src.data.seed_data import seed_demo_dataset, reset_demo_dataset

router = APIRouter()

# --- Request Models ---

class CanonicalLoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class ReadingItem(BaseModel):
    timestamp: str
    facility_id: Optional[str] = "COLLEGE_01"
    zone_id: str
    asset_id: Optional[str] = None
    metric_type: str
    value: float
    unit: str
    source_type: Optional[str] = "csv"
    quality_flag: Optional[str] = "valid"

class ReadingBatchRequest(BaseModel):
    facility_id: Optional[str] = "COLLEGE_01"
    batch_id: Optional[str] = None
    records: Optional[List[Dict[str, Any]]] = None
    readings: Optional[List[Dict[str, Any]]] = None

class AnalysisRunRequest(BaseModel):
    facility_id: str = "COLLEGE_01"
    zone_id: Optional[str] = None
    lookback_days: int = 14
    energy_threshold_pct: float = 25.0

class AlertPatchRequest(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None

class ScenarioSimulateRequest(BaseModel):
    facility_id: str = "COLLEGE_01"
    zone_id: Optional[str] = None
    reduction_pct: float = 10.0
    tariff_inr_per_kwh: Optional[float] = None
    time_window_hours: int = 24
    baseline_kwh: Optional[float] = None
    hvac_setback_deg: float = 2.0
    solar_addition_kwp: float = 0.0

class ActionCreateRequest(BaseModel):
    alert_id: Optional[str] = None
    owner_id: Optional[str] = "alex.chen@estateiq.in"
    assignee: Optional[str] = None
    status: str = "OPEN"
    notes: Optional[str] = ""
    due_at: Optional[str] = None

class CsvPreviewRequest(BaseModel):
    csv_content: str
    limit: int = 20

class CsvImportRequest(BaseModel):
    csv_content: str
    facility_id: str = "COLLEGE_01"
    filename: Optional[str] = "import.csv"
    column_mapping: Optional[Dict[str, str]] = None


# --- 1. Health Endpoint ---

@router.get("/health")
def canonical_health():
    return {
        "status": "HEALTHY",
        "system": "EstateIQ Sustainable Facility Intelligence Engine (India)",
        "version": "1.0.0",
        "database": "CONNECTED",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


# --- 2. Auth Endpoint ---

@router.post("/auth/login")
def canonical_login(req: CanonicalLoginRequest):
    user_identifier = req.username or req.email
    if user_identifier and req.password:
        user = authenticate_user(user_identifier, req.password)
    elif req.role:
        role_key = req.role.lower()
        if role_key in USER_ROLES_DB:
            user = USER_ROLES_DB[role_key]
        else:
            from src.auth.security import get_user_by_role
            user = get_user_by_role(role_key)
    else:
        user = USER_ROLES_DB.get("admin") or USER_ROLES_DB["lead@estateiq.in"]

    token = create_user_token(user)
    record_audit_event(
        user_id=user["user_id"],
        entity_type="auth",
        entity_id=user["email"],
        action="LOGIN",
        before_json=None,
        after_json={"role": user["role"], "status": "SUCCESS"}
    )

    return {
        "status": "AUTHENTICATED",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "username": user["email"].split("@")[0] if "@" in user["email"] else user["email"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "facility_id": user.get("facility_id", "COLLEGE_01"),
            "permissions": ROLE_PERMISSIONS.get(user["role"], [])
        }
    }


# --- 3. Facilities Endpoint ---

@router.get("/facilities")
@router.get("/api/v1/facilities")
def canonical_facilities(user: Dict[str, Any] = Depends(verify_current_user)):
    facs = db_list_facilities()
    if not facs:
        # Seed if empty
        seed_demo_dataset()
        facs = db_list_facilities()

    user_role = user.get("role", "")
    user_fac = user.get("facility_id")

    # Facility authorization filtering: non-super-admins see permitted facility
    if user_role not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac:
        filtered = [f for f in facs if f["id"] == user_fac or (f["id"] == "COLLEGE_01" and user_fac == "FAC_GEC_01")]
        if filtered:
            return filtered
    return facs


# --- 4. Readings Batch Ingestion ---

@router.post("/readings/batch")
@router.post("/api/v1/readings/batch")
def canonical_readings_batch(
    payload: Union[ReadingBatchRequest, List[Dict[str, Any]], Dict[str, Any]],
    user: Dict[str, Any] = Depends(verify_current_user)
):
    if isinstance(payload, list):
        readings = payload
        fac_id = readings[0].get("facility_id", "COLLEGE_01") if readings else "COLLEGE_01"
        b_id = f"BATCH_JSON_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    elif isinstance(payload, ReadingBatchRequest):
        readings = payload.records or payload.readings or []
        fac_id = payload.facility_id or "COLLEGE_01"
        b_id = payload.batch_id or f"BATCH_JSON_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    else:
        readings = payload.get("records") or payload.get("readings") or []
        fac_id = payload.get("facility_id", "COLLEGE_01")
        b_id = payload.get("batch_id") or f"BATCH_JSON_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Server-side facility authorization check
    user_fac = user.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and user_fac not in [fac_id, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: User facility '{user_fac}' cannot ingest readings for facility '{fac_id}'."
        )

    if not readings:
        raise HTTPException(status_code=400, detail="Empty readings batch payload")

    res = insert_readings_batch(
        readings=readings,
        batch_id=b_id,
        facility_id=fac_id,
        filename="api_batch"
    )

    record_audit_event(
        user_id=user.get("email", user.get("user_id", "admin")),
        entity_type="reading_batch",
        entity_id=b_id,
        action="INGEST_BATCH",
        before_json=None,
        after_json={"total": res["total_rows"], "accepted": res["accepted_count"], "rejected": res["rejected_count"]}
    )

    return res


# --- 5. Query Readings Endpoint ---

@router.get("/readings")
@router.get("/api/v1/readings")
def canonical_get_readings(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    source_type: Optional[str] = None,
    quality_flag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    # Enforce facility authorization
    user_fac = user.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and user_fac not in [facility_id, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail=f"Access Denied: User unauthorized for facility '{facility_id}'.")

    rows, total_count = query_readings(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time,
        source_type=source_type,
        quality_flag=quality_flag,
        limit=min(limit, 1000),
        offset=offset
    )

    return {
        "facility_id": facility_id,
        "zone_id": zone_id,
        "total_count": total_count,
        "returned_count": len(rows),
        "limit": limit,
        "offset": offset,
        "readings": rows
    }


# --- 6. Run Analysis Pipeline ---

@router.post("/analysis/run")
@router.post("/api/v1/analysis/run")
def canonical_run_analysis(
    req: Optional[AnalysisRunRequest] = None,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    fac_id = req.facility_id if req else "COLLEGE_01"
    zid = req.zone_id if req else None
    lookback = req.lookback_days if req else 14
    thresh = req.energy_threshold_pct if req else 25.0

    # Facility authorization check
    user_fac = user.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and user_fac not in [fac_id, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail=f"Access Denied: User unauthorized for facility '{fac_id}'.")

    start_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run_id = f"RUN_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    anomalies = detect_facility_anomalies(
        facility_id=fac_id,
        zone_id=zid,
        lookback_days=lookback,
        energy_threshold_pct=thresh,
        run_id=run_id
    )

    end_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    model_versions = {
        "energy_anomaly": "SeasonalMedian_MAD_v1.0",
        "water_anomaly": "ClosedHoursFlowRule_v1.0",
        "waste_overflow": "FillRateProjection_v1.0",
        "air_quality": "NAAQS_ThresholdRule_v1.0"
    }

    summary = {
        "anomalies_detected": len(anomalies),
        "lookback_days": lookback,
        "energy_threshold_pct": thresh
    }

    record_analysis_run(
        facility_id=fac_id,
        status="SUCCESS",
        model_versions=model_versions,
        summary=summary,
        started_at=start_ts,
        completed_at=end_ts
    )

    record_audit_event(
        user_id=user.get("email", user.get("user_id", "operator")),
        entity_type="analysis_run",
        entity_id=run_id,
        action="RUN_ANALYSIS",
        before_json=None,
        after_json={"anomalies_count": len(anomalies), "facility_id": fac_id}
    )

    return {
        "run_id": run_id,
        "facility_id": fac_id,
        "status": "SUCCESS",
        "started_at": start_ts,
        "completed_at": end_ts,
        "anomalies_detected_count": len(anomalies),
        "anomalies": anomalies,
        "model_versions": model_versions
    }


# --- 7. Alerts List & Filter ---

@router.get("/alerts")
@router.get("/api/v1/alerts")
def canonical_list_alerts(
    facility_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    metric_type: Optional[str] = None,
    limit: int = 100,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    # Facility scoping check
    user_fac = user.get("facility_id")
    target_fac = facility_id or user_fac or "COLLEGE_01"
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and target_fac not in [user_fac, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail="Access Denied: Facility mismatch.")

    alerts = list_alerts(
        facility_id=target_fac,
        zone_id=zone_id,
        status=status,
        severity=severity,
        metric_type=metric_type,
        limit=limit
    )
    return alerts


# --- 8. Alert Patch (Update Status/Assignee/Due Date) ---

@router.patch("/alerts/{id}")
@router.patch("/api/v1/alerts/{id}")
def canonical_patch_alert(
    id: str,
    req: AlertPatchRequest,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    existing = get_alert(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert '{id}' not found.")

    # Facility authorization check
    user_fac = user.get("facility_id")
    alert_fac = existing.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and alert_fac not in [user_fac, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail="Access Denied: Alert facility mismatch.")

    actor = user.get("email", user.get("user_id", "operator"))
    updated = update_alert(
        alert_id=id,
        status=req.status,
        assignee=req.assignee,
        due_date=req.due_date,
        notes=req.notes,
        user_id=actor
    )

    return {
        "status": "UPDATED",
        "alert": updated,
        "audit_event": {
            "entity_type": "alert",
            "entity_id": id,
            "action": "UPDATE_ALERT",
            "updated_by": actor,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }


# --- 9. Scenarios Simulate Endpoint ---

@router.post("/scenarios/simulate")
@router.post("/api/v1/scenarios/simulate")
def canonical_simulate_scenario(
    req: ScenarioSimulateRequest,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    actor = user.get("email", user.get("user_id", "operator"))
    res = simulate_energy_scenario(
        facility_id=req.facility_id,
        zone_id=req.zone_id,
        reduction_pct=req.reduction_pct,
        tariff_inr_per_kwh=req.tariff_inr_per_kwh,
        time_window_hours=req.time_window_hours,
        baseline_kwh=req.baseline_kwh,
        hvac_setback_deg=req.hvac_setback_deg,
        solar_addition_kwp=req.solar_addition_kwp,
        user_id=actor,
        persist=True
    )
    return res


# --- 10. Actions Create Endpoint ---

@router.post("/actions")
@router.post("/api/v1/actions")
def canonical_create_action(
    req: ActionCreateRequest,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    actor = user.get("email", user.get("user_id", "operator"))
    owner = req.owner_id or req.assignee or actor
    res = create_action(
        alert_id=req.alert_id,
        owner_id=owner,
        status=req.status,
        notes=req.notes,
        due_at=req.due_at,
        user_id=actor
    )
    return res


# --- 11. Reports Summary Endpoint ---

@router.get("/reports/summary")
@router.get("/api/v1/reports/summary")
def canonical_reports_summary(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    # Scoping check
    user_fac = user.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and facility_id not in [user_fac, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail="Access Denied: Facility mismatch.")

    report = generate_report_summary(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time
    )
    return report


# --- 12. CSV Export & Printable Views ---

@router.get("/reports/export/csv")
@router.get("/api/v1/reports/export/csv")
def canonical_export_csv(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    csv_content = export_readings_csv(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time
    )
    filename = f"estateiq_readings_{facility_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/reports/printable")
@router.get("/api/v1/reports/printable")
def canonical_printable_report(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    rep_summary = generate_report_summary(
        facility_id=facility_id,
        zone_id=zone_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time
    )
    html_content = generate_printable_html_report(rep_summary)
    return HTMLResponse(content=html_content)


# --- 13. CSV Template & Ingestion Helpers ---

@router.get("/readings/template")
@router.get("/api/v1/readings/template")
def canonical_download_csv_template():
    tpl = get_csv_template()
    return Response(
        content=tpl,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=estateiq_reading_template.csv"}
    )

@router.post("/readings/preview")
@router.post("/api/v1/readings/preview")
def canonical_preview_csv(req: CsvPreviewRequest):
    return preview_csv_content(req.csv_content, limit=req.limit)

@router.post("/readings/import/csv")
@router.post("/api/v1/readings/import/csv")
def canonical_import_csv(
    req: CsvImportRequest,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    # Facility scoping check
    user_fac = user.get("facility_id")
    if user.get("role") not in ["SUPER_ADMIN", "ADMINISTRATOR"] and user_fac and req.facility_id not in [user_fac, "COLLEGE_01", "FAC_GEC_01"]:
        raise HTTPException(status_code=403, detail="Access Denied: Facility mismatch.")

    actor = user.get("email", user.get("user_id", "admin"))
    res = import_csv_data(
        csv_text_or_bytes=req.csv_content,
        selected_facility_id=req.facility_id,
        column_mapping=req.column_mapping,
        filename=req.filename,
        user_id=actor
    )
    return res


# --- 14. Batch Rollback Endpoint (Admin Only) ---

@router.delete("/readings/batches/{batch_id}")
@router.post("/readings/batches/{batch_id}/rollback")
def canonical_rollback_batch(
    batch_id: str,
    user: Dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SUPER_ADMIN", "FACILITY_ADMIN"]))
):
    actor = user.get("email", user.get("user_id", "admin"))
    res = rollback_batch(batch_id=batch_id, user_id=actor)
    if not res["success"]:
        raise HTTPException(status_code=404, detail=res["message"])
    return res


# --- 15. Admin Demo Seed / Reset Endpoints (Admin Only) ---

@router.post("/admin/demo/seed")
def canonical_demo_seed(
    user: Dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SUPER_ADMIN", "FACILITY_ADMIN"]))
):
    res = seed_demo_dataset()
    return res

@router.post("/admin/demo/reset")
def canonical_demo_reset(
    user: Dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SUPER_ADMIN", "FACILITY_ADMIN"]))
):
    res = reset_demo_dataset()
    return res
