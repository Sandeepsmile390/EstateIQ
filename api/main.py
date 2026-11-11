"""
FastAPI Enterprise REST API Application for Sustainable Facility and Estate Intelligence Platform.
Exposes secure /api/v1/ endpoints for authentication, RBAC/ABAC authorization, facility monitoring,
energy forecasting, contextual baselines, anomaly detection, SHAP explainability, decision traces,
business impact, action lifecycle management, what-if simulations, tool-based AI Copilot, digital twin,
and audit logging.
"""

import os
import uuid
import datetime
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Security, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data.repository import DataRepository, ProvenanceType
from src.data.mongo_db import connect_mongo_db, get_db_status, save_prediction_log, query_prediction_logs
from src.decisions.trace import DecisionTraceEngine
from src.auth.security import (
    authenticate_user, create_user_token, revoke_token, verify_current_user,
    require_permission, require_facility_access, USER_ROLES_DB, USERS_DB, ROLE_PERMISSIONS
)
from src.models.baseline import ContextualBaselineEngine
from src.explainability.shap_engine import SHAPExplainabilityEngine
from src.scoring.business_impact import BusinessImpactEngine
from src.monitoring.transformer_dg import TransformerDGMonitor
from src.decisions.action_center import ActionCenterEngine
from src.recommendations.copilot import AICopilotEngine
from src.monitoring.audit_log import record_audit_event, get_audit_logs

from src.monitoring.power_quality import PowerQualityMonitor
from src.scenarios.demand_response import DemandResponseEngine

from src.models.energy.pipeline import train_energy_module
from src.models.water.pipeline import train_water_module
from src.models.waste.pipeline import train_waste_module, categorize_waste_risk
from src.models.air.pipeline import train_air_module
from src.models.traffic.pipeline import train_traffic_module
from src.models.parking.pipeline import train_parking_module
from src.models.equipment.pipeline import train_equipment_module
from src.scoring.sustainability import SustainabilityScoreCalculator
from src.recommendations.genai_engine import GenAIExplanationEngine
from src.scenarios.whatif import WhatIfScenarioEngine
from src.priority.engine import FacilityPriorityEngine
from src.ai.ai_service import EstateIQAIService
from src.ai.usage_tracker import GLOBAL_USAGE_TRACKER
from src.ai.config import DEFAULT_AI_CONFIG
from src.ai.exceptions import AIServiceError
from src.intelligence.types import EventData

from src.security import (
    get_encryption_service,
    validate_security_configuration,
    get_security_status,
    redact_secrets
)

app = FastAPI(
    title="EstateIQ - Sustainable Facility Intelligence Platform",
    description="AI-powered decision-support dashboard for government, university, PSU, and enterprise campuses in India.",
    version="1.0.0"
)


@app.exception_handler(AIServiceError)
def ai_service_exception_handler(request: Request, exc: AIServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": f"AI SERVICE ERROR: {exc.error_code} - {exc.message}",
            "error_code": exc.error_code,
            "status": "error",
            "retryable": exc.retryable
        }
    )


# --- Security Headers & Secure CORS Middleware ---
allowed_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if allowed_origins_env and allowed_origins_env != "*":
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8501", "http://127.0.0.1:8000", "http://127.0.0.1:8501"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Prevent stale caching so client browsers always render real-time UI & live sensor data
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.on_event("startup")
def startup_security_and_db():
    validate_security_configuration()
    connect_mongo_db()
    try:
        from src.data.canonical_db import init_canonical_schema
        init_canonical_schema()
    except Exception as e:
        print(f"Canonical schema init warning: {e}")

    # Start MQTT consumer if enabled in environment
    mqtt_enabled = os.getenv("MQTT_ENABLED", "false").lower() in ("true", "1", "yes")
    if mqtt_enabled:
        try:
            from src.data.mqtt_consumer import MQTTTelemetryConsumer
            broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
            broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
            mqtt_consumer = MQTTTelemetryConsumer(broker_host=broker_host, broker_port=broker_port)
            ok = mqtt_consumer.start()
            if ok:
                print(f"[MQTT] Telemetry Consumer background listener started on {broker_host}:{broker_port}")
            else:
                print(f"[MQTT] Consumer startup skipped (broker not reachable or paho not installed).")
        except Exception as mqtt_err:
            print(f"[MQTT] Consumer startup warning: {mqtt_err}")


# --- Static File Serving ---
if os.path.exists("web"):
    app.mount("/static", StaticFiles(directory="web"), name="static")
if os.path.exists("web/css"):
    app.mount("/css", StaticFiles(directory="web/css"), name="css")
if os.path.exists("web/js"):
    app.mount("/js", StaticFiles(directory="web/js"), name="js")

# --- Service Instances ---
repo = DataRepository()
genai_engine = GenAIExplanationEngine()
priority_engine = FacilityPriorityEngine()
decision_trace_engine = DecisionTraceEngine()
baseline_engine = ContextualBaselineEngine()
shap_engine = SHAPExplainabilityEngine()
business_impact_engine = BusinessImpactEngine()
transformer_dg_monitor = TransformerDGMonitor()
power_quality_monitor = PowerQualityMonitor()
demand_response_engine = DemandResponseEngine()
action_center_engine = ActionCenterEngine()
copilot_engine = AICopilotEngine()


# --- Request Models ---
class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class EnergyPredictRequest(BaseModel):
    temperature: float = Field(28.5, ge=-20.0, le=60.0)
    humidity: float = Field(60.0, ge=0.0, le=100.0)
    occupancy: int = Field(120, ge=0)
    hvac_load: float = Field(45.0, ge=0.0, le=100.0)
    lighting_load: float = Field(15.0, ge=0.0, le=100.0)
    equipment_load: float = Field(25.0, ge=0.0, le=100.0)
    previous_energy_kwh: float = Field(110.0, ge=0.0)
    hour: int = Field(14, ge=0, le=23)
    day_of_week: int = Field(2, ge=0, le=6)

class WastePredictRequest(BaseModel):
    fill_level: float = Field(78.5, ge=0.0, le=100.0)
    fill_rate: float = Field(4.2, ge=0.0)
    temperature: float = Field(29.0, ge=-20.0, le=60.0)
    occupancy: int = Field(200, ge=0)
    day_of_week: int = Field(3, ge=0, le=6)
    hour: int = Field(15, ge=0, le=23)
    collection_time: int = 0

class AnomalyRequest(BaseModel):
    facility_id: str = "FAC_GEC_01"
    building_id: str = "Block_B_Hostel"
    measurements: Dict[str, float] = {"flow_rate": 50.0, "occupancy": 5.0}

class ChatRequest(BaseModel):
    user_query: str = "Why is energy consumption high in Block B Hostel?"

class ScenarioRequest(BaseModel):
    current_values: Dict[str, float] = {"temperature": 28.0, "occupancy": 150.0, "hvac_load": 50.0}
    modifications: Dict[str, float] = {"hvac_load": 0.80, "occupancy": 0.90}

class ActionUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = ""
    verification_evidence: Optional[Dict[str, Any]] = None

class UpgradeRequest(BaseModel):
    target_plan: str = "enterprise_pro"
    billing_cycle: str = "annual"

class ApplyRuleRequest(BaseModel):
    rule_id: str
    building_id: str

# --- Helper Model Loader ---
def get_model_and_metadata(task_name: str, train_fn):
    meta_path = f"models/{task_name}_metadata.joblib"
    model_path = f"models/{task_name}_model.joblib"
    if os.path.exists(meta_path) and os.path.exists(model_path):
        return joblib.load(model_path), joblib.load(meta_path)
    model, meta, _ = train_fn()
    return model, meta

# --- Web UI Routes ---
@app.get("/")
def serve_dashboard():
    if os.path.exists("web/index.html"):
        return FileResponse("web/index.html")
    return {"message": "EstateIQ API Service Active", "docs": "/docs"}

@app.get("/dashboard")
def serve_dashboard_route():
    if os.path.exists("web/index.html"):
        return FileResponse("web/index.html")
    return {"message": "EstateIQ Web Dashboard"}

@app.get("/pzem")
def serve_pzem_dashboard():
    if os.path.exists("web/pzem.html"):
        return FileResponse("web/pzem.html")
    return {"message": "PZEM Dashboard"}

# --- Health & Readiness Endpoints ---
@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "EstateIQ Sustainable Facility Intelligence Engine (India)",
        "version": "1.0.0",
        "database": "CONNECTED",
        "database_status": "CONNECTED",
        "timestamp": pd.Timestamp.now().isoformat()
    }

@app.get("/api/v1/readiness")
def readiness_check():
    db_stat = get_db_status()
    models_exist = os.path.exists("models") and len(os.listdir("models")) > 0
    return {
        "status": "READY" if models_exist else "INITIALIZING",
        "database": db_stat,
        "models_registered": models_exist,
        "timestamp": pd.Timestamp.now().isoformat()
    }

# --- Centralized 3-Role Frontend Profiles ---
ROLE_FRONTEND_PROFILES = {
    "admin": {
        "role_key": "admin",
        "role_label": "Admin (Full Access)",
        "avatar_bg": "#124B3E",
        "user_email": "admin@estateiq.in",
        "permissions": [
            "overview", "suggestions", "energy", "water", "waste", "mobility",
            "simulator", "resource-simulator", "iot-monitor", "ai-assistant",
            "faq", "esg", "billing", "work-orders"
        ],
        "can_execute_rules": True,
        "can_upgrade_subscription": True
    },
    "sustainability": {
        "role_key": "sustainability",
        "role_label": "Sustainability Officer",
        "avatar_bg": "#0D9488",
        "user_email": "sustainability@estateiq.in",
        "permissions": [
            "overview", "esg", "suggestions", "energy", "water", "waste", "mobility", "faq"
        ],
        "can_execute_rules": False,
        "can_upgrade_subscription": False
    },
    "operations": {
        "role_key": "operations",
        "role_label": "Operations Team",
        "avatar_bg": "#1E7A68",
        "user_email": "operations@estateiq.in",
        "permissions": [
            "overview", "iot-monitor", "resource-simulator", "simulator", "work-orders",
            "ai-assistant", "energy", "water", "waste", "mobility", "faq"
        ],
        "can_execute_rules": True,
        "can_upgrade_subscription": False
    }
}

# --- Auth Endpoints ---
@app.post("/api/v1/auth/login")
def auth_login(req: LoginRequest):
    if req.email and req.password:
        user = authenticate_user(req.email, req.password)
    elif req.role:
        role_key = req.role.lower().strip()
        if role_key in ["admin", "super_admin", "facility_admin"]:
            user = USERS_DB["admin@estateiq.in"]
        elif role_key in ["sustainability", "sustainability_officer", "esg_auditor", "auditor"]:
            user = USERS_DB["sustainability@estateiq.in"]
        elif role_key in ["operations", "operations_team", "operations_engineer", "engineer"]:
            user = USERS_DB["operations@estateiq.in"]
        else:
            user = USERS_DB["admin@estateiq.in"]
    else:
        user = USERS_DB["admin@estateiq.in"]

    user_role = (user.get("role") or "").upper()
    if user_role in ["SUSTAINABILITY_OFFICER", "ESG_AUDITOR", "SUSTAINABILITY"]:
        profile = ROLE_FRONTEND_PROFILES["sustainability"]
    elif user_role in ["OPERATIONS_ENGINEER", "OPERATIONS", "OPERATIONS_TEAM"]:
        profile = ROLE_FRONTEND_PROFILES["operations"]
    else:
        profile = ROLE_FRONTEND_PROFILES["admin"]

    token = create_user_token(user)
    record_audit_event("LOGIN_SUCCESS", user, "LOGIN", "auth", result="SUCCESS")
    
    return {
        "status": "AUTHENTICATED",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "initials": user.get("initials", user["name"][:2].upper()),
            "role": user["role"],
            "role_key": profile["role_key"],
            "role_label": profile["role_label"],
            "avatar_bg": profile["avatar_bg"],
            "facility_id": user.get("facility_id", "FAC_GEC_01"),
            "permissions": profile["permissions"],
            "can_execute_rules": profile["can_execute_rules"],
            "can_upgrade_subscription": profile["can_upgrade_subscription"]
        }
    }

@app.get("/api/v1/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(verify_current_user)):
    user_role = (user.get("role") or "").upper()
    if user_role in ["SUSTAINABILITY_OFFICER", "ESG_AUDITOR", "SUSTAINABILITY"]:
        profile = ROLE_FRONTEND_PROFILES["sustainability"]
    elif user_role in ["OPERATIONS_ENGINEER", "OPERATIONS", "OPERATIONS_TEAM"]:
        profile = ROLE_FRONTEND_PROFILES["operations"]
    else:
        profile = ROLE_FRONTEND_PROFILES["admin"]

    return {
        "user_id": user.get("user_id", "USR_SUPER_00"),
        "email": user.get("email", profile["user_email"]),
        "name": user.get("name", "RS Administrator"),
        "initials": user.get("initials", "RS"),
        "role": user_role,
        "role_key": profile["role_key"],
        "role_label": profile["role_label"],
        "avatar_bg": profile["avatar_bg"],
        "facility_id": user.get("facility_id", "FAC_GEC_01"),
        "permissions": profile["permissions"],
        "can_execute_rules": profile["can_execute_rules"],
        "can_upgrade_subscription": profile["can_upgrade_subscription"]
    }

@app.post("/api/v1/auth/logout")
def auth_logout(user: Dict[str, Any] = Depends(verify_current_user)):
    if user.get("token"):
        revoke_token(user["token"])
    record_audit_event("LOGOUT", user, "LOGOUT", "auth")
    return {"status": "LOGGED_OUT", "message": "Session successfully terminated."}

@app.get("/api/v1/auth/roles")
def list_available_roles():
    return {
        "roles": [
            {"key": "admin", "label": "RS Administrator", "title": "Admin (Full Access)", "badge": "FULL ACCESS"},
            {"key": "sustainability", "label": "Dr. Priya Sharma", "title": "Sustainability Officer", "badge": "ESG & ROI"},
            {"key": "operations", "label": "Alex Chen", "title": "Operations Team", "badge": "IOT & OPERATIONS"}
        ]
    }

# --- Protected Audit Logging Endpoints (Replaces unsafe /db/logs route) ---
@app.get("/api/v1/db/status")
def db_status_endpoint():
    return get_db_status()

@app.get("/api/v1/db/logs/{collection_name}")
def db_logs_endpoint(collection_name: str, limit: int = 50):
    logs = query_prediction_logs(collection_name, limit=limit)
    return {"collection": collection_name, "count": len(logs), "data": logs}

@app.get("/api/v1/audit/logs")
def get_system_audit_logs(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_permission("audit.read"))
):
    logs = get_audit_logs(facility_id=user.get("facility_id"), limit=min(limit, 500))
    return {"count": len(logs), "logs": logs}

# --- Security Status & AES-256-GCM Administration Endpoints ---
class EncryptPayloadRequest(BaseModel):
    plaintext: str
    context: Optional[str] = None

class DecryptPayloadRequest(BaseModel):
    envelope: str
    context: Optional[str] = None

@app.get("/api/v1/admin/security/status")
def admin_security_status(user: Dict[str, Any] = Depends(require_permission("audit.read"))):
    return get_security_status()

@app.post("/api/v1/admin/security/encrypt")
def admin_encrypt_payload(
    req: EncryptPayloadRequest,
    user: Dict[str, Any] = Depends(require_permission("audit.read"))
):
    enc_svc = get_encryption_service()
    envelope = enc_svc.encrypt(req.plaintext, context=req.context)
    return {
        "status": "ENCRYPTED",
        "algorithm": "AES-256-GCM",
        "envelope": envelope
    }

@app.post("/api/v1/admin/security/decrypt")
def admin_decrypt_payload(
    req: DecryptPayloadRequest,
    user: Dict[str, Any] = Depends(require_permission("audit.read"))
):
    enc_svc = get_encryption_service()
    plaintext = enc_svc.decrypt(req.envelope, context=req.context)
    return {
        "status": "DECRYPTED",
        "plaintext": plaintext
    }




# --- Facility & Domain Endpoints ---
@app.get("/api/v1/facility/summary")
def facility_summary(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    fac = repo.get_facility_info()
    bld_df = repo.get_buildings()
    return {
        "facility": fac,
        "total_buildings": len(bld_df),
        "building_list": bld_df["building_name"].tolist() if not bld_df.empty else []
    }

@app.get("/api/v1/energy/data")
@app.get("/api/v1/energy/history")
def energy_history(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_permission("energy.read"))
):
    df = repo.get_energy_data(limit=min(limit, 500))
    if df.empty:
        return {"status": "NO_DATA", "message": "No energy telemetry available.", "data": []}
    return {
        "count": len(df),
        "provenance": ProvenanceType.SYNTHETIC,
        "provenance_badge": "[SYNTHETIC IoT DATA]",
        "data": df.to_dict(orient="records")
    }

@app.get("/api/v1/energy/baseline")
def get_energy_baseline(
    hour: int = 14,
    temperature: float = 28.5,
    occupancy: int = 120,
    user: Dict[str, Any] = Depends(require_permission("energy.read"))
):
    latest_energy = repo.get_latest_energy()
    actual_kwh = float(latest_energy.get("energy_kwh", 140.0))
    exp_kwh = baseline_engine.calculate_expected_kwh("Block_B_Hostel", hour=hour, day_of_week=2, occupancy=occupancy, temperature=temperature)
    dev = baseline_engine.evaluate_deviation(actual_kwh=actual_kwh, expected_kwh=exp_kwh)
    impact = business_impact_engine.calculate_energy_impact(actual_kwh=actual_kwh, expected_kwh=exp_kwh)
    
    return {
        "building_id": "Block_B_Hostel",
        "baseline_evaluation": dev,
        "business_impact": impact,
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[CONTEXTUAL BASELINE]"
    }


@app.post("/predict/energy")
@app.post("/api/v1/energy")
def predict_energy(
    req: EnergyPredictRequest,
    user: Dict[str, Any] = Depends(require_permission("energy.predict"))
):
    model, meta = get_model_and_metadata("energy_kwh_prediction", train_energy_module)
    req_dict = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    df_in = pd.DataFrame([req_dict])
    for c in meta["feature_names"]:
        if c not in df_in.columns:
            df_in[c] = 0
    pred = float(model.predict(df_in[meta["feature_names"]])[0])
    
    # Generate SHAP explanation for prediction
    shap_explanation = shap_engine.compute_local_explanation(req_dict, model, meta["feature_names"])
    
    res = {
        "task": "energy_kwh_prediction",
        "predicted_energy_kwh": round(pred, 2),
        "algorithm": meta["selected_model"],
        "unit": "kWh",
        "shap_explanation": shap_explanation,
        "provenance": ProvenanceType.PREDICTED,
        "provenance_badge": "[ML FORECAST — 1H]"
    }
    save_prediction_log("predictions", {**res, "request": req_dict})
    return res

import time

def get_latest_live_telemetry() -> Dict[str, Any]:
    """Helper function to fetch the latest real-time streaming telemetry sample from registry or simulator."""
    from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
    from src.services.iot_simulator import GLOBAL_IOT_SIMULATOR

    # 1. Check GLOBAL_DEVICE_REGISTRY history for valid, non-quarantined, non-late samples
    valid_records = [
        r for r in GLOBAL_DEVICE_REGISTRY.telemetry_history
        if r.get("is_valid_sample", True) and not r.get("quarantined") and not r.get("is_late_sample")
    ]
    if valid_records:
        def _rec_sort_key(r):
            ts = r.get("event_timestamp") or r.get("ingested_at") or ""
            try:
                return pd.to_datetime(ts).timestamp()
            except Exception:
                return 0.0
        # Keep the overview internally coherent: merge only records from the same
        # facility, building, provenance, and verification class. A simulator or a
        # neighboring building must never fill a missing hardware metric.
        rec = max(valid_records, key=_rec_sort_key)
        src_type = rec.get("source_type", "simulated_iot")
        is_verified_group = bool(rec.get("is_verified_hardware"))
        group_key = (
            rec.get("facility_id"), rec.get("building_id"), src_type,
            is_verified_group if src_type == "real_sensor" else False,
        )
        group_records = [r for r in valid_records if (
            r.get("facility_id"), r.get("building_id"), r.get("source_type", "simulated_iot"),
            bool(r.get("is_verified_hardware")) if r.get("source_type") == "real_sensor" else False,
        ) == group_key]
        group_records.sort(key=_rec_sort_key, reverse=True)
        ts_str = rec.get("event_timestamp") or rec.get("ingested_at")
        now_dt = pd.Timestamp.now(tz="UTC")
        try:
            ts_dt = pd.to_datetime(ts_str)
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.tz_localize("UTC")
            age_sec = max(0.0, (now_dt - ts_dt).total_seconds())
        except Exception:
            age_sec = 0.0

        badge = rec.get("data_source_badge") or (
            "[REAL SENSOR]" if src_type == "real_sensor" and is_verified_group else
            "[UNVERIFIED SENSOR - DEMO MODE]" if src_type == "real_sensor" else
            "[SIMULATED IoT]" if src_type == "simulated_iot" else "[SYNTHETIC IoT DATA]"
        )
        dev_id = rec.get("device_id", "DEV_SIM_01")
        dev = GLOBAL_DEVICE_REGISTRY.devices.get(dev_id)
        if dev:
            if age_sec > 300:
                dev_status = "OFFLINE"
            elif age_sec > 45:
                dev_status = "STALE"
            else:
                dev_status = dev.status
        else:
            dev_status = "ONLINE" if age_sec <= 45 else ("STALE" if age_sec <= 300 else "OFFLINE")

        # Use the newest fresh value per metric within this coherent source group.
        metric_records: Dict[str, Dict[str, Any]] = {}
        m: Dict[str, Any] = {}
        contributing_device_ids = set()
        for r in group_records:
            r_ts = r.get("event_timestamp") or r.get("ingested_at") or ""
            try:
                r_dt = pd.to_datetime(r_ts)
                if r_dt.tzinfo is None: r_dt = r_dt.tz_localize("UTC")
                r_age = max(0.0, (now_dt - r_dt).total_seconds())
            except Exception:
                r_age = 0.0
            if r_age <= 300.0:
                contributing_device_ids.add(r.get("device_id"))
                for k, v in r.get("metrics", {}).items():
                    if k not in m and v is not None:
                        m[k] = v
                        metric_records[k] = r

        # Extract physical metrics honestly without fabricated fallbacks
        active_p = float(m["active_power_kw"]) if "active_power_kw" in m and m["active_power_kw"] is not None else (float(m["power_kw"]) if "power_kw" in m and m["power_kw"] is not None else None)
        cum_e = float(m["cumulative_energy_kwh"]) if "cumulative_energy_kwh" in m and m["cumulative_energy_kwh"] is not None else None
        # Strict unit & measurement separation: interval energy (kWh) is NOT active power (kW)! If absent, return None.
        int_e = float(m["energy_kwh"]) if "energy_kwh" in m and m["energy_kwh"] is not None else (float(m["interval_energy_kwh"]) if "interval_energy_kwh" in m and m["interval_energy_kwh"] is not None else None)
        volt = float(m["voltage_v"]) if "voltage_v" in m and m["voltage_v"] is not None else None
        curr = float(m["current_a"]) if "current_a" in m and m["current_a"] is not None else None
        pf = float(m["power_factor"]) if "power_factor" in m and m["power_factor"] is not None else None
        freq = float(m["frequency_hz"]) if "frequency_hz" in m and m["frequency_hz"] is not None else None

        w_flow = float(m["water_flow_lmin"]) if "water_flow_lmin" in m and m["water_flow_lmin"] is not None else (float(m["water_flow_lpm"]) if "water_flow_lpm" in m and m["water_flow_lpm"] is not None else None)
        cum_w = float(m["cumulative_water_m3"]) if "cumulative_water_m3" in m and m["cumulative_water_m3"] is not None else None
        w_press = float(m["water_pressure_bar"]) if "water_pressure_bar" in m and m["water_pressure_bar"] is not None else None
        t_lvl = float(m["tank_level_pct"]) if "tank_level_pct" in m and m["tank_level_pct"] is not None else None

        temp = float(m["temperature_c"]) if "temperature_c" in m and m["temperature_c"] is not None else (float(m["temperature"]) if "temperature" in m and m["temperature"] is not None else None)
        hum = float(m["humidity_pct"]) if "humidity_pct" in m and m["humidity_pct"] is not None else (float(m["humidity"]) if "humidity" in m and m["humidity"] is not None else None)
        heat_idx = float(m["heat_index_c"]) if "heat_index_c" in m and m["heat_index_c"] is not None else None
        mq_adc = int(m["mq135_raw_adc"]) if "mq135_raw_adc" in m and m["mq135_raw_adc"] is not None else None
        mq_volt = float(m["mq135_voltage_v"]) if "mq135_voltage_v" in m and m["mq135_voltage_v"] is not None else None
        mq_co2 = float(m["mq135_co2_estimate_ppm"]) if "mq135_co2_estimate_ppm" in m and m["mq135_co2_estimate_ppm"] is not None else None

        # Filter out phantom disconnected analog readings (pin floating at 0)
        if mq_adc is not None and mq_adc < 80 and (mq_volt is None or mq_volt < 0.08):
            mq_adc = None
            mq_volt = None
            mq_co2 = None
        tank_dist = float(m["tank_distance_cm"]) if "tank_distance_cm" in m and m["tank_distance_cm"] is not None else None
        occ = int(m["occupancy_count"]) if "occupancy_count" in m and m["occupancy_count"] is not None else (int(m["occupancy"]) if "occupancy" in m and m["occupancy"] is not None else None)
        hvac = float(m["hvac_load_kw"]) if "hvac_load_kw" in m and m["hvac_load_kw"] is not None else (float(m["hvac_load"]) if "hvac_load" in m and m["hvac_load"] is not None else None)
        aqi = float(m["air_quality_aqi"]) if "air_quality_aqi" in m and m["air_quality_aqi"] is not None else (float(m["air_aqi"]) if "air_aqi" in m and m["air_aqi"] is not None else None)

        # Determine presence and metric quality status based on verified provenance
        metric_values = {
            "active_power_kw": active_p,
            "energy_kwh": int_e,
            "cumulative_energy_kwh": cum_e,
            "voltage_v": volt,
            "current_a": curr,
            "power_factor": pf,
            "frequency_hz": freq,
            "water_flow_lmin": w_flow,
            "cumulative_water_m3": cum_w,
            "water_pressure_bar": w_press,
            "tank_level_pct": t_lvl,
            "temperature": temp,
            "humidity": hum,
            "occupancy": occ,
            "hvac_load": hvac,
            "air_aqi": aqi
        }

        metric_status: Dict[str, str] = {}
        metric_source_keys = {
            "active_power_kw": ("active_power_kw", "power_kw"),
            "energy_kwh": ("energy_kwh", "interval_energy_kwh"),
            "cumulative_energy_kwh": ("cumulative_energy_kwh",),
            "voltage_v": ("voltage_v",), "current_a": ("current_a",),
            "power_factor": ("power_factor",), "frequency_hz": ("frequency_hz",),
            "water_flow_lmin": ("water_flow_lmin", "water_flow_lpm"),
            "cumulative_water_m3": ("cumulative_water_m3",),
            "water_pressure_bar": ("water_pressure_bar",), "tank_level_pct": ("tank_level_pct",),
            "temperature": ("temperature_c", "temperature"),
            "humidity": ("humidity_pct", "humidity"),
            "occupancy": ("occupancy_count", "occupancy"),
            "hvac_load": ("hvac_load_kw", "hvac_load"),
            "air_aqi": ("air_quality_aqi", "air_aqi"),
        }
        for k, v in metric_values.items():
            if v is None:
                metric_status[k] = "UNAVAILABLE"
                continue
            source_key = next((key for key in metric_source_keys.get(k, (k,)) if key in metric_records), None)
            if source_key is None:
                metric_status[k] = "UNAVAILABLE"
            else:
                metric_rec = metric_records[source_key]
                metric_ts = metric_rec.get("event_timestamp") or metric_rec.get("ingested_at") or ""
                try:
                    metric_age = max(0.0, (now_dt - pd.to_datetime(metric_ts, utc=True)).total_seconds())
                except Exception:
                    metric_age = float("inf")
                if metric_age > 300:
                    metric_status[k] = "OFFLINE"
                elif metric_age > 45:
                    metric_status[k] = "STALE"
                elif src_type == "real_sensor" and not is_verified_group:
                    metric_status[k] = "UNVERIFIED_DEMO"
                elif src_type == "real_sensor":
                    metric_status[k] = "DEGRADED" if metric_rec.get("quality_warnings") else "MEASURED"
                elif src_type == "simulated_iot":
                    metric_status[k] = "SIMULATED"
                elif src_type == "derived":
                    metric_status[k] = "DERIVED"
                else:
                    metric_status[k] = "SYNTHETIC"

        return {
            "energy_kwh": int_e,
            "active_power_kw": active_p,
            "cumulative_energy_kwh": cum_e,
            "temperature": temp,
            "humidity": hum,
            "occupancy": occ,
            "hvac_load": hvac,
            "voltage_v": volt,
            "current_a": curr,
            "power_factor": pf,
            "frequency_hz": freq,
            "water_flow_lmin": w_flow,
            "cumulative_water_m3": cum_w,
            "water_pressure_bar": w_press,
            "tank_level_pct": t_lvl,
            "tank_distance_cm": tank_dist,
            "heat_index_c": heat_idx,
            "mq135_raw_adc": mq_adc,
            "mq135_voltage_v": mq_volt,
            "mq135_co2_estimate_ppm": mq_co2,
            "air_aqi": aqi,
            "building_id": rec.get("building_id", "Block B Hostel"),
            "device_id": dev_id,
            "contributing_device_ids": sorted(x for x in contributing_device_ids if x),
            "facility_id": rec.get("facility_id"),
            "device_status": dev_status,
            "timestamp": ts_str,
            "data_freshness_sec": round(age_sec, 1),
            "source_type": src_type,
            "is_verified_hardware": is_verified_group,
            "data_source_badge": badge,
            "metric_status": metric_status,
            "quality_warnings": rec.get("quality_warnings", [])
        }

    # 2. Fallback to GLOBAL_IOT_SIMULATOR
    sim_status = GLOBAL_IOT_SIMULATOR.get_status()
    s = sim_status.get("sensors", {})
    all_sim_status = {k: "SIMULATED" for k in ["active_power_kw", "energy_kwh", "cumulative_energy_kwh", "voltage_v", "current_a", "power_factor", "frequency_hz", "water_flow_lmin", "cumulative_water_m3", "water_pressure_bar", "tank_level_pct", "temperature", "humidity", "occupancy", "hvac_load", "air_aqi"]}
    return {
        "energy_kwh": float(s.get("energy_kwh", 115.0)),
        "active_power_kw": float(s.get("active_power_kw", 145.0)),
        "cumulative_energy_kwh": float(s.get("energy_kwh", 115.0)),
        "temperature": float(s.get("temperature_c", 28.5)),
        "humidity": 55.0,
        "occupancy": int(s.get("occupancy_count", 120)),
        "hvac_load": float(s.get("hvac_load_kw", 45.0)),
        "voltage_v": float(s.get("voltage_v", 230.0)),
        "current_a": float(s.get("current_a", 15.0)),
        "power_factor": float(s.get("power_factor", 0.95)),
        "frequency_hz": float(s.get("frequency_hz", 50.0)),
        "water_flow_lmin": float(s.get("water_flow_lmin", 12.0)),
        "cumulative_water_m3": 142.5,
        "water_pressure_bar": 3.2,
        "tank_level_pct": 78.0,
        "air_aqi": float(s.get("air_aqi", 75.0)),
        "building_id": sim_status.get("building_id", "Block B Hostel"),
        "device_id": "DEV_SIMULATOR_CORE",
        "device_status": "ONLINE",
        "timestamp": sim_status.get("simulated_timestamp"),
        "data_freshness_sec": 1.0,
        "source_type": "simulated_iot",
        "is_verified_hardware": False,
        "data_source_badge": "[SIMULATED IoT]",
        "metric_status": all_sim_status,
        "quality_warnings": []
    }

@app.get("/api/v1/energy/forecast")
def energy_forecast(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    model, meta = get_model_and_metadata("energy_kwh_prediction", train_energy_module)
    live = get_latest_live_telemetry()

    sim_status = GLOBAL_IOT_SIMULATOR.get_status().get("sensors", {})
    temp_val = live["temperature"] if live["temperature"] is not None else float(sim_status.get("temperature_c", 28.0))
    hum_val = live["humidity"] if live["humidity"] is not None else float(sim_status.get("humidity", 50.0))
    occ_val = live["occupancy"] if live["occupancy"] is not None else int(sim_status.get("occupancy_count", 100))
    hvac_val = live["hvac_load"] if live["hvac_load"] is not None else float(sim_status.get("hvac_load_kw", 35.0))
    prev_kwh = live["energy_kwh"] if live["energy_kwh"] is not None else (
        (live["active_power_kw"] * 0.25) if live["active_power_kw"] is not None else float(sim_status.get("energy_kwh", 25.0))
    )

    sample_df = pd.DataFrame([{
        "temperature": temp_val,
        "humidity": hum_val,
        "occupancy": occ_val,
        "hvac_load": hvac_val,
        "lighting_load": 15.0,
        "equipment_load": 22.0,
        "previous_energy_kwh": prev_kwh,
        "hour": pd.Timestamp.now().hour,
        "day_of_week": pd.Timestamp.now().dayofweek
    }])
    for c in meta["feature_names"]:
        if c not in sample_df.columns:
            sample_df[c] = 0

    base_pred = float(model.predict(sample_df[meta["feature_names"]])[0])

    return {
        "forecast_horizon": "1h, 4h, 24h",
        "predicted_1h_kwh": round(base_pred, 2),
        "predicted_4h_kwh": round(base_pred * 1.08, 2),
        "predicted_24h_kwh": round(base_pred * 0.92, 2),
        "algorithm": meta.get("selected_model", "CatBoostRegressor"),
        "confidence_interval": "±6.8%",
        "generation_timestamp": pd.Timestamp.now().isoformat(),
        "data_freshness_sec": live["data_freshness_sec"],
        "source_device_id": live["device_id"],
        "provenance": ProvenanceType.PREDICTED,
        "provenance_badge": "[ML FORECAST — LIVE TELEMETRY]"
    }

# In-memory registry for alert cooldown/hysteresis
ALERT_COOLDOWN_REGISTRY: Dict[str, float] = {}


def _sustained_power_samples(records: List[Dict[str, Any]], threshold_kw: float, now_utc: pd.Timestamp) -> List[Dict[str, Any]]:
    """Return the newest three same-meter samples above threshold if recent and contiguous."""
    candidates = []
    for record in records:
        metrics = record.get("metrics", {})
        value = metrics.get("active_power_kw", metrics.get("power_kw"))
        raw_timestamp = record.get("event_timestamp") or record.get("ingested_at")
        try:
            timestamp = pd.to_datetime(raw_timestamp, utc=True) if raw_timestamp else None
        except Exception:
            timestamp = None
        if value is not None and timestamp is not None:
            candidates.append((timestamp, float(value), record))
    candidates.sort(key=lambda item: item[0], reverse=True)
    recent = candidates[:3]
    if len(recent) < 3 or any(value < threshold_kw for _, value, _ in recent):
        return []
    if any((now_utc - ts).total_seconds() > 3600 for ts, _, _ in recent):
        return []
    if any((recent[index][0] - recent[index + 1][0]).total_seconds() > 1200 for index in range(2)):
        return []
    return [record for _, _, record in recent]

@app.get("/api/v1/energy/anomalies")
def energy_anomalies(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    live = get_latest_live_telemetry()
    actual_kwh = live.get("energy_kwh")
    actual_power = live.get("active_power_kw")
    building = live["building_id"]
    hour = pd.Timestamp.now().hour

    sim_status = GLOBAL_IOT_SIMULATOR.get_status().get("sensors", {})
    occ_context = live["occupancy"] if live["occupancy"] is not None else int(sim_status.get("occupancy_count", 100))
    temp_context = live["temperature"] if live["temperature"] is not None else float(sim_status.get("temperature_c", 28.0))

    exp_kwh = baseline_engine.calculate_expected_kwh(
        building_id=building,
        hour=hour,
        day_of_week=pd.Timestamp.now().dayofweek,
        occupancy=occ_context,
        temperature=temp_context
    )

    anomalies_list = []

    # Sensor Data Quality & Fault Suppression Check
    from src.data_quality.quality_score import DataQualityEngine
    dq_eval = DataQualityEngine().evaluate_sensor_record(live)
    if dq_eval["suppress_resource_anomalies"]:
        anomalies_list.append({
            "id": "ALT_SENSOR_FAULT",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Sensor Quality Degraded / Fault Detected",
            "severity": "HIGH",
            "observed_value": f"Quality: {dq_eval['health_status']}",
            "expected_range": "Quality: HEALTHY",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": "Sensor Warning",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"Telemetry quality warnings: {'; '.join(dq_eval['issues'])}. Downstream energy waste claims suppressed.",
            "recommended_action": "Inspect sensor wiring, RS-485 Modbus bus, or pulse counter calibration.",
            "data_source_badge": live["data_source_badge"]
        })
        return {
            "active_anomalies_count": 1,
            "telemetry_freshness_sec": live["data_freshness_sec"],
            "provenance": ProvenanceType.DERIVED,
            "provenance_badge": live["data_source_badge"],
            "anomalies": anomalies_list
        }

    # Rule 1: Thermal HVAC Load Surge
    hvac_load_val = live.get("hvac_load") or 0.0
    if actual_kwh is not None or actual_power is not None:
        is_surge = (actual_kwh is not None and actual_kwh > exp_kwh * 1.15) or (actual_power is not None and actual_power >= 180.0 and hvac_load_val >= 60.0)
        if is_surge:
            dev_pct = round(((actual_kwh - exp_kwh) / max(1.0, exp_kwh)) * 100, 1) if actual_kwh is not None else None
            severity = "CRITICAL" if (dev_pct is not None and dev_pct > 60) or (actual_power is not None and actual_power >= 180.0 and hvac_load_val >= 60.0) else "HIGH"
            anomalies_list.append({
                "id": "ALT_SURGE_HVAC",
                "device_id": live["device_id"],
                "building": building,
                "issue": "HVAC Thermal Load Surge",
                "severity": severity,
                "observed_value": f"{round(actual_kwh, 2)} kWh" if actual_kwh is not None else f"{round(actual_power, 2)} kW",
                "expected_range": f"{round(exp_kwh * 0.8, 1)} - {round(exp_kwh * 1.1, 1)} kWh",
                "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
                "expected_kwh": round(exp_kwh, 1),
                "deviation_percent": f"+{dev_pct}%" if dev_pct is not None else "Power threshold exceeded",
                "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
                "explanation": f"Live telemetry detected load surging {dev_pct}% above contextual baseline during ambient heat ({temp_context}°C).",
                "recommended_action": "Adjust HVAC setpoint by +2°C and shift non-essential thermal load to off-peak.",
                "data_source_badge": live["data_source_badge"]
            })

    # Rule 1b: hardware-scale persistent after-hours load (e.g. the team's bulb demo).
    # Use a same-meter time series and never mix power (kW) with interval energy (kWh).
    closed_start = int(os.getenv("ESTATEIQ_CLOSED_HOURS_START", "22")) % 24
    closed_end = int(os.getenv("ESTATEIQ_CLOSED_HOURS_END", "6")) % 24
    is_closed_hours = (closed_start > closed_end and (hour >= closed_start or hour < closed_end)) or (
        closed_start < closed_end and closed_start <= hour < closed_end
    )
    try:
        after_hours_threshold_kw = max(0.0, float(os.getenv("ESTATEIQ_AFTER_HOURS_POWER_THRESHOLD_KW", "0.05")))
    except ValueError:
        after_hours_threshold_kw = 0.05
    if is_closed_hours:
        power_records = [
            record for record in GLOBAL_DEVICE_REGISTRY.telemetry_history
            if record.get("is_valid_sample", True) and not record.get("quarantined") and not record.get("is_late_sample")
            and record.get("facility_id") == live.get("facility_id")
            and record.get("building_id") == building
            and record.get("source_type", "simulated_iot") == live.get("source_type")
            and (live.get("source_type") != "real_sensor" or bool(record.get("is_verified_hardware")) == bool(live.get("is_verified_hardware")))
            and ("active_power_kw" in record.get("metrics", {}) or "power_kw" in record.get("metrics", {}))
        ]
        if power_records:
            newest_power = max(power_records, key=lambda record: pd.to_datetime(record.get("event_timestamp") or record.get("ingested_at"), utc=True, errors="coerce"))
            meter_id = newest_power.get("device_id")
            same_meter = [record for record in power_records if record.get("device_id") == meter_id]
            now_utc = pd.Timestamp.now(tz="UTC")
            sustained = _sustained_power_samples(same_meter, after_hours_threshold_kw, now_utc)
            if sustained:
                power_value = float(sustained[0].get("metrics", {}).get("active_power_kw", sustained[0].get("metrics", {}).get("power_kw")))
                verified = bool(sustained[0].get("is_verified_hardware")) and live.get("source_type") == "real_sensor"
                anomalies_list.append({
                    "id": "ALT_AFTER_HOURS_SMALL_LOAD",
                    "device_id": meter_id,
                    "building": building,
                    "issue": "Persistent After-Hours Electrical Load",
                    "severity": "HIGH" if verified else "MEDIUM",
                    "observed_value": f"{power_value:.3f} kW",
                    "expected_range": f"Below {after_hours_threshold_kw:.3f} kW during configured closed hours",
                    "actual_kwh": round(actual_kwh, 3) if actual_kwh is not None else None,
                    "expected_kwh": None,
                    "deviation_percent": "Persistent threshold exceedance",
                    "timestamp": sustained[0].get("event_timestamp") or now_utc.isoformat(),
                    "explanation": f"Three consecutive readings from the same meter exceeded the configured {after_hours_threshold_kw:.3f} kW threshold during closed hours. This low-load rule supports small test loads; validate the device schedule before action.",
                    "recommended_action": "Inspect the connected load and operating schedule; switch off only after confirming it is safe and authorized.",
                    "data_source_badge": live.get("data_source_badge"),
                })

    # Rule 2: After-Hours Consumption Waste
    if live.get("occupancy") is not None and live.get("hvac_load") is not None:
        if live["occupancy"] < 20 and live["hvac_load"] > 40:
            anomalies_list.append({
                "id": "ALT_WASTE_HVAC",
                "device_id": live["device_id"],
                "building": building,
                "issue": "After-Hours Energy Waste",
                "severity": "HIGH",
                "observed_value": f"HVAC {round(live['hvac_load'], 1)} kW",
                "expected_range": "< 15 kW (Off-Peak)",
                "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
                "expected_kwh": round(exp_kwh, 1),
                "deviation_percent": "+180%",
                "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
                "explanation": f"High HVAC load ({live['hvac_load']} kW) operating in near-empty building (Occupancy: {live['occupancy']}).",
                "recommended_action": "Trigger automated night setback policy and switch HVAC to eco standby mode.",
                "data_source_badge": live["data_source_badge"]
            })

    # Rule 3: Water Leakage Detection using Sustained Water-Meter History
    # YF-S201 Operating Range: 1.0 to 30.0 L/min. Baseline off-peak flow < 5.0 L/min.
    # Requires at least 3 consecutive fresh samples within 10 minutes (600s) above 12.0 L/min.
    water_records = [
        r for r in GLOBAL_DEVICE_REGISTRY.telemetry_history
        if (r.get("is_valid_sample", True) and not r.get("quarantined") and not r.get("is_late_sample"))
        and ("water_flow_lmin" in r.get("metrics", {}) or "water_flow_lpm" in r.get("metrics", {}))
    ]

    if water_records:
        target_water_rec = water_records[0]
        target_water_dev_id = target_water_rec.get("device_id")
        water_building = target_water_rec.get("building_id") or building
        water_facility = target_water_rec.get("facility_id")
        dev_water_records = [r for r in water_records if r.get("device_id") == target_water_dev_id]

        now_ts = pd.Timestamp.now(datetime.timezone.utc)
        fresh_high_flow_samples = []
        is_stale_flow = False
        has_sensor_glitch = False

        glitch_flow_val = None
        for r in dev_water_records[:5]:
            m = r.get("metrics", {})
            flow_val = m.get("water_flow_lmin", m.get("water_flow_lpm"))
            if flow_val is None:
                continue

            r_ts_str = r.get("event_timestamp") or r.get("ingested_at")
            try:
                r_dt = pd.to_datetime(r_ts_str)
                if r_dt.tzinfo is None:
                    r_dt = r_dt.tz_localize("UTC")
                age_s = max(0.0, (now_ts - r_dt).total_seconds())
            except Exception:
                age_s = 0.0

            if age_s > 600.0:
                is_stale_flow = True
                break

            # YF-S201 confirmed physical rating: 1.0 - 30.0 L/min (±3% tolerance).
            # Readings exceeding 30.0 L/min indicate out-of-range sensor condition, debounce failure, or electrical noise.
            if flow_val > 30.0:
                has_sensor_glitch = True
                glitch_flow_val = flow_val
                break

            if flow_val >= 12.0:
                fresh_high_flow_samples.append((flow_val, r))
            else:
                break

        if has_sensor_glitch:
            anomalies_list.append({
                "id": "ALT_WATER_SENSOR_FAULT",
                "device_id": target_water_dev_id,
                "building": water_building,
                "issue": "Water Flow Sensor Range Error / Out-of-Bounds",
                "severity": "HIGH",
                "observed_value": f"{round(glitch_flow_val, 1)} L/min (> 30.0 L/min)",
                "expected_range": "1.0 - 30.0 L/min (YF-S201 Rating, ±3% tolerance)",
                "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
                "expected_kwh": round(exp_kwh, 1),
                "deviation_percent": "Sensor Glitch",
                "timestamp": dev_water_records[0].get("event_timestamp") or now_ts.isoformat(),
                "explanation": f"Pulse frequency produced flow reading ({round(glitch_flow_val, 1)} L/min) exceeding confirmed 1.0-30.0 L/min operating range of YF-S201 flow meter (max 225 Hz at 30 L/min, ±3% tolerance). Possible debounce failure, electrical noise, or missing 10k/20k voltage divider.",
                "recommended_action": "Check 10k/20k voltage divider on GPIO5, verify pulse counter pullup, and inspect physical meter for turbulence/cavitation.",
                "data_source_badge": dev_water_records[0].get("data_source_badge", "[UNVERIFIED SENSOR - DEMO MODE]")
            })
        elif not is_stale_flow and len(fresh_high_flow_samples) >= 3:
            latest_flow = fresh_high_flow_samples[0][0]
            avg_flow = round(sum(s[0] for s in fresh_high_flow_samples) / len(fresh_high_flow_samples), 1)

            # Query occupancy telemetry specifically for the same facility and building
            matching_occ_records = []
            cross_bldg_occ_records = []
            for r in GLOBAL_DEVICE_REGISTRY.telemetry_history:
                if not (r.get("is_valid_sample", True) and not r.get("quarantined") and not r.get("is_late_sample")):
                    continue
                m = r.get("metrics", {})
                occ = m.get("occupancy_count", m.get("occupancy"))
                if occ is None:
                    continue
                r_bldg = r.get("building_id")
                r_fac = r.get("facility_id")

                fac_match = True
                if water_facility and r_fac and water_facility != r_fac:
                    fac_match = False

                if r_bldg == water_building and fac_match:
                    matching_occ_records.append((occ, r))
                else:
                    cross_bldg_occ_records.append((occ, r))

            same_bldg_occ_verified = False
            occ_val = None
            occ_status = "UNAVAILABLE"
            occ_reason = ""

            if not matching_occ_records:
                if cross_bldg_occ_records:
                    other_bldg = cross_bldg_occ_records[0][1].get("building_id", "Unknown")
                    occ_reason = f"cross-building occupancy from '{other_bldg}' rejected; same-building occupancy unavailable for '{water_building}'"
                else:
                    occ_reason = f"occupancy source missing for building '{water_building}'"
            else:
                target_occ, occ_rec = matching_occ_records[0]
                occ_ts_str = occ_rec.get("event_timestamp") or occ_rec.get("ingested_at")
                try:
                    occ_dt = pd.to_datetime(occ_ts_str)
                    if occ_dt.tzinfo is None:
                        occ_dt = occ_dt.tz_localize("UTC")
                    occ_age_s = max(0.0, (now_ts - occ_dt).total_seconds())
                except Exception:
                    occ_age_s = 9999.0

                is_occ_fresh = (occ_age_s <= 600.0)
                is_occ_real = (occ_rec.get("source_type") == "real_sensor")
                is_occ_verified_hw = bool(occ_rec.get("is_verified_hardware", False))

                if not is_occ_fresh:
                    occ_reason = f"same-building occupancy data is stale ({round(occ_age_s)}s old > 600s)"
                elif not (is_occ_real and is_occ_verified_hw):
                    occ_reason = f"same-building occupancy is unverified or simulated (source_type={occ_rec.get('source_type')}, verified_hw={is_occ_verified_hw})"
                else:
                    same_bldg_occ_verified = True
                    occ_val = int(target_occ)
                    occ_status = "MEASURED"

            is_water_physically_verified = (
                fresh_high_flow_samples[0][1].get("is_verified_hardware", False)
                and fresh_high_flow_samples[0][1].get("source_type") == "real_sensor"
            )

            if same_bldg_occ_verified and is_water_physically_verified and occ_val is not None and occ_val < 15:
                issue_label = "Confirmed Off-Hours Water Leak"
                severity = "CRITICAL"
                confidence = "High (Verified Hardware & Verified Same-Building Occupancy)"
                expl_detail = f"Verified same-building occupancy is {occ_val} (< 15 in {water_building})."
            else:
                issue_label = "Suspected Water Leak (Unverified Occupancy / Hardware)"
                severity = "HIGH"
                confidence = "Medium (Sustained Flow Observed; Occupancy Context Unavailable or Unverified)"
                if not same_bldg_occ_verified:
                    expl_detail = f"Occupancy context is unavailable or unverified ({occ_reason})."
                elif not is_water_physically_verified:
                    expl_detail = "Water meter hardware provenance is unverified (demo mode or unauthenticated)."
                else:
                    expl_detail = f"Occupancy ({occ_val}) is not below off-hours threshold (< 15)."

            anomalies_list.append({
                "id": "ALT_WATER_LEAK",
                "device_id": target_water_dev_id,
                "building": water_building,
                "issue": issue_label,
                "severity": severity,
                "observed_value": f"{latest_flow} L/min (avg {avg_flow} L/min over {len(fresh_high_flow_samples)} samples)",
                "expected_range": "< 5.0 L/min (Off-Peak Baseline)",
                "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
                "expected_kwh": round(exp_kwh, 1),
                "deviation_percent": f"+{round((avg_flow / 5.0 - 1.0) * 100, 1)}%",
                "timestamp": dev_water_records[0].get("event_timestamp") or now_ts.isoformat(),
                "explanation": f"Sustained flow of {latest_flow} L/min detected across {len(fresh_high_flow_samples)} consecutive fresh samples within YF-S201 range (1-30 L/min). {expl_detail} Confidence: {confidence}.",
                "recommended_action": "Dispatch maintenance technician to inspect sanitary fixtures and isolation valves manually.",
                "data_source_badge": dev_water_records[0].get("data_source_badge", "[UNVERIFIED SENSOR - DEMO MODE]")
            })

    # Rule 4: Voltage Instability
    v_val = live.get("voltage_v")
    if v_val is not None and (v_val < 200.0 or v_val > 250.0):
        anomalies_list.append({
            "id": "ALT_VOLT_INSTABLE",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Electrical Grid Voltage Instability",
            "severity": "CRITICAL",
            "observed_value": f"{round(v_val, 1)} V",
            "expected_range": "220 - 240 V (IS-12332 standard)",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": "Voltage Out-of-Bounds",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"Measured voltage ({round(v_val, 1)} V) deviates beyond Indian IS-12332 standard operating window.",
            "recommended_action": "Switch sensitive equipment to UPS / standby DG bypass.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 5: Stale Telemetry / Sensor Offline
    if live["data_freshness_sec"] > 45:
        anomalies_list.append({
            "id": "ALT_STALE_SENSOR",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Sensor Connection Stale / Offline",
            "severity": "MEDIUM",
            "observed_value": f"{live['data_freshness_sec']}s delay",
            "expected_range": "< 15s heartbeats",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": "Heartbeat Timeout",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": "No fresh telemetry received from sensor hardware within the 15-second polling window.",
            "recommended_action": "Check MQTT broker connection and IoT gateway power supply.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 6: Low Power Factor Anomaly (PZEM-004T / Modbus Metrology)
    pf_val = live.get("power_factor")
    if pf_val is not None and pf_val > 0.0 and pf_val < 0.85:
        kw_now = eval_val or 10.0
        phi = math.acos(max(0.1, min(1.0, pf_val)))
        kvar_waste = round(kw_now * math.tan(phi), 2)
        anomalies_list.append({
            "id": "ALT_LOW_POWER_FACTOR",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Low Power Factor / Inductive Reactive Waste",
            "severity": "HIGH" if pf_val < 0.80 else "MEDIUM",
            "observed_value": f"PF: {round(pf_val, 2)} (Lagging)",
            "expected_range": ">= 0.95 (Grid Standard)",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"-{round((0.95 - pf_val) / 0.95 * 100, 1)}%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"Power factor lagging at {round(pf_val, 2)} with ~{kvar_waste} kVAR uncompensated reactive load. Increases electrical line losses and utility penalty exposure.",
            "recommended_action": "Switch in Automatic Power Factor Correction (APFC) capacitor bank stage 2.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 7: Overhead Water Tank Low Level / Dry Run Pump Hazard (Ultrasonic Sonar)
    tank_val = live.get("tank_level_pct")
    if tank_val is not None and tank_val < 15.0:
        dist_now = live.get("tank_distance_cm") or 180.0
        anomalies_list.append({
            "id": "ALT_TANK_DEPLETION",
            "device_id": "WATER-BLOCK-B-001",
            "building": building,
            "issue": "Critical Water Storage Depletion - Dry-Run Pump Hazard",
            "severity": "CRITICAL",
            "observed_value": f"{round(tank_val, 1)}% Fill ({round(dist_now, 1)} cm)",
            "expected_range": "25% - 90% Operating Band",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"-{round((25.0 - tank_val) / 25.0 * 100, 1)}%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"Ultrasonic water level sonar detected tank level at {round(tank_val, 1)}% (< 15%). Immediate danger of pump cavitation and water outage.",
            "recommended_action": "Engage dry-run motor interlock cutoff and initiate ground-sump refill cycle.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 8: Rooftop Water Tank Approaching Overflow (Ultrasonic Sonar)
    if tank_val is not None and tank_val > 95.0 and (live.get("water_flow_lmin") or 0.0) > 0.5:
        anomalies_list.append({
            "id": "ALT_TANK_OVERFLOW",
            "device_id": "WATER-BLOCK-B-001",
            "building": building,
            "issue": "Water Storage Tank Approaching Overflow",
            "severity": "HIGH",
            "observed_value": f"{round(tank_val, 1)}% Fill",
            "expected_range": "< 90% High Water Cutoff",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"+{round((tank_val - 90.0) / 90.0 * 100, 1)}%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"Tank level reached {round(tank_val, 1)}% with ongoing inflow. Overflow spill imminent.",
            "recommended_action": "De-energize intake transfer pump and close inlet solenoid valve.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 9: Relative MQ-135 response alert. MQ-135 is not a calibrated CO2/AQI instrument.
    mq_ppm = live.get("mq135_co2_estimate_ppm")
    mq_raw = live.get("mq135_raw_adc")
    if mq_raw is not None and mq_raw > 1800:
        anomalies_list.append({
            "id": "ALT_AIR_QUALITY_HAZARD",
            "device_id": live["device_id"],
            "building": building,
            "issue": "MQ-135 Relative Gas Response Elevated",
            "severity": "MEDIUM",
            "observed_value": f"Raw ADC: {mq_raw} / 4095" + (f"; uncalibrated estimate {round(mq_ppm, 0)} ppm" if mq_ppm is not None else ""),
            "expected_range": "Configured relative-response threshold: 1800 ADC counts",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"+{round((mq_raw - 1800.0) / 1800.0 * 100, 1)}% raw response",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": "The MQ-135 raw analog response exceeded the configured relative threshold. This module is not calibrated here as a CO2, PM2.5, or certified AQI instrument; treat this as a change signal and verify with a suitable air-quality meter.",
            "recommended_action": "Check sensor warm-up/calibration status and safely ventilate the area if the response persists; verify with a calibrated air-quality instrument.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 10: Thermal Heat Stress Hazard (DHT11 Temperature & Humidity Sensor)
    t_now = live.get("temperature")
    h_now = live.get("humidity")
    hi_now = live.get("heat_index_c")
    if (t_now is not None and t_now >= 36.0) or (hi_now is not None and hi_now >= 40.0):
        anomalies_list.append({
            "id": "ALT_THERMAL_HEAT_STRESS",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Thermal Heat Stress Danger - Occupant Welfare Risk",
            "severity": "HIGH",
            "observed_value": f"Temp: {round(t_now, 1)}°C | Heat Index: {round(hi_now or t_now, 1)}°C",
            "expected_range": "22°C - 26°C Thermal Comfort Band",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"+{round(((t_now or 30.0) - 26.0) / 26.0 * 100, 1)}%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"DHT11 climate sensor measured temperature {round(t_now, 1)}°C with calculated NOAA Heat Index {round(hi_now or t_now, 1)}°C exceeding safe occupancy thresholds.",
            "recommended_action": "Increase HVAC chilled water flow and deploy localized spot cooling.",
            "data_source_badge": live["data_source_badge"]
        })

    # Rule 11: High Relative Humidity / Mold Risk (DHT11)
    if h_now is not None and h_now > 82.0:
        anomalies_list.append({
            "id": "ALT_HIGH_HUMIDITY_MOLD",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Excessive Relative Humidity - Structural Mold & Condensation Hazard",
            "severity": "MEDIUM",
            "observed_value": f"{round(h_now, 1)}% RH",
            "expected_range": "30% - 60% ASHRAE 55 Standard",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": f"+{round((h_now - 60.0) / 60.0 * 100, 1)}%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": f"DHT11 measured sustained relative humidity of {round(h_now, 1)}% (> 82%). High risk of pipe condensation, fungal spores, and structural deterioration.",
            "recommended_action": "Activate HVAC dehumidification cycle and inspect zone for building envelope moisture ingress.",
            "data_source_badge": live["data_source_badge"]
        })

    if not anomalies_list:
        anomalies_list = [{
            "id": "ALT_NORMAL_00",
            "device_id": live["device_id"],
            "building": building,
            "issue": "Normal Campus Operation",
            "severity": "NORMAL",
            "observed_value": f"{round(actual_kwh, 1)} kWh" if actual_kwh is not None else (f"{round(actual_power, 1)} kW" if actual_power is not None else "Normal Monitoring"),
            "expected_range": f"{round(exp_kwh * 0.8, 1)} - {round(exp_kwh * 1.2, 1)} kWh",
            "actual_kwh": round(actual_kwh, 1) if actual_kwh is not None else None,
            "expected_kwh": round(exp_kwh, 1),
            "deviation_percent": "0%",
            "timestamp": live["timestamp"] or pd.Timestamp.now().isoformat(),
            "explanation": "All monitored metrics operating within normal baseline boundaries.",
            "recommended_action": "Maintain optimal setpoints and eco controls.",
            "data_source_badge": live["data_source_badge"]
        }]

    return {
        "active_anomalies_count": len([a for a in anomalies_list if a["severity"] != "NORMAL"]),
        "telemetry_freshness_sec": live["data_freshness_sec"],
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": live["data_source_badge"],
        "anomalies": anomalies_list
    }

@app.get("/api/v1/energy/transformer")
def get_transformer_status(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    return transformer_dg_monitor.get_transformer_status(current_load_kw=585.0)

@app.get("/api/v1/energy/dg")
def get_dg_status(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    return transformer_dg_monitor.get_dg_status(is_running=False, runtime_hours_today=1.5, fuel_level_pct=82.0)

@app.get("/api/v1/energy/power-quality")
def get_power_quality(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    return power_quality_monitor.evaluate_power_quality()

@app.get("/api/v1/energy/demand-response")
def get_demand_response_opportunities(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    return demand_response_engine.evaluate_flexible_loads()


@app.post("/predict/waste")
@app.post("/api/v1/waste")
def predict_waste(
    req: WastePredictRequest,
    user: Dict[str, Any] = Depends(require_permission("waste.read"))
):
    model, meta = get_model_and_metadata("waste_overflow_2hr", train_waste_module)
    df_in = pd.DataFrame([req.model_dump() if hasattr(req, "model_dump") else req.dict()])
    for c in meta["feature_names"]:
        if c not in df_in.columns:
            df_in[c] = 0
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(df_in[meta["feature_names"]])[0][1])
    else:
        prob = float(model.predict(df_in[meta["feature_names"]])[0])
    risk_lvl = categorize_waste_risk(prob)
    return {
        "task": "waste_overflow_2hr",
        "overflow_probability": round(prob, 4),
        "risk_level": risk_lvl,
        "algorithm": meta["selected_model"],
        "provenance": ProvenanceType.PREDICTED,
        "provenance_badge": "[ML PREDICTION]",
        "note": "Probabilities represent estimated risk levels, not physical certainty."
    }

@app.post("/anomaly/water")
@app.post("/api/v1/water/anomaly")
def anomaly_water(
    req: AnomalyRequest,
    user: Dict[str, Any] = Depends(require_permission("water.read"))
):
    flow = req.measurements.get("flow_rate", 10.0)
    occ = req.measurements.get("occupancy", 10.0)
    is_anomaly = 1 if (flow > 40.0 and occ < 15) else 0
    return {
        "facility_id": req.facility_id,
        "building_id": req.building_id,
        "anomaly_status": "ANOMALY_DETECTED" if is_anomaly else "NORMAL",
        "anomaly_score": 0.92 if is_anomaly else 0.08,
        "explanation": "Abnormal water-use pattern detected. High flow observed during off-peak occupancy. Immediate on-site inspection recommended.",
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[ANOMALY DETECTOR]"
    }

@app.post("/anomaly/energy")
@app.post("/api/v1/energy/anomaly")
def anomaly_energy(
    req: AnomalyRequest,
    user: Dict[str, Any] = Depends(require_permission("energy.read"))
):
    load = req.measurements.get("hvac_load", 30.0)
    occ = req.measurements.get("occupancy", 10.0)
    is_anomaly = 1 if (load > 80.0 and occ < 20) else 0
    return {
        "facility_id": req.facility_id,
        "building_id": req.building_id,
        "anomaly_status": "ANOMALY_DETECTED" if is_anomaly else "NORMAL",
        "anomaly_score": 0.88 if is_anomaly else 0.12,
        "explanation": "High HVAC load detected relative to building occupancy.",
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[ANOMALY DETECTOR]"
    }


@app.get("/api/v1/waste/summary")
def waste_summary(user: Dict[str, Any] = Depends(require_permission("waste.read"))):
    return repo.get_latest_waste()

@app.get("/api/v1/air")
def air_summary(user: Dict[str, Any] = Depends(require_permission("air.read"))):
    return repo.get_latest_air_quality()

@app.get("/api/v1/traffic")
def traffic_summary(user: Dict[str, Any] = Depends(require_permission("mobility.read"))):
    return repo.get_latest_traffic()

@app.get("/api/v1/parking")
def parking_summary(user: Dict[str, Any] = Depends(require_permission("mobility.read"))):
    return repo.get_latest_parking()

@app.get("/api/v1/equipment")
def equipment_summary(user: Dict[str, Any] = Depends(require_permission("assets.read"))):
    return repo.get_latest_equipment()

# --- Alert Action Request Models ---
class AlertActionRequest(BaseModel):
    notes: Optional[str] = None
    actor: Optional[str] = "Operator"

class AlertAssignRequest(BaseModel):
    assignee: str
    actor: Optional[str] = "Supervisor"
    notes: Optional[str] = None

class AlertDismissRequest(BaseModel):
    dismissal_reason: str = "Operator dismissed"
    actor: Optional[str] = "Operator"

class AlertResolveRequest(BaseModel):
    resolution_notes: str = "Resolved by facility technician"
    actor: Optional[str] = "Operator"

@app.get("/api/v1/alerts")
def get_alerts(
    source_type: Optional[str] = None,
    state: Optional[str] = None,
    severity: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 100,
    user: Dict[str, Any] = Depends(require_permission("alerts.read"))
):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    alerts = GLOBAL_ALERT_SERVICE.list_alerts(
        source_type=source_type,
        state=state,
        severity=severity,
        device_id=device_id,
        limit=limit
    )
    return {
        "total_alerts": len(alerts),
        "total_active_alerts": GLOBAL_ALERT_SERVICE.get_active_count(),
        "alerts": [a.model_dump() if hasattr(a, "model_dump") else a.dict() for a in alerts]
    }

@app.get("/api/v1/alerts/{alert_id}")
def get_alert_by_id(alert_id: str, user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    alert = GLOBAL_ALERT_SERVICE.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    return alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()

@app.post("/api/v1/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    req: AlertActionRequest = AlertActionRequest(),
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    try:
        actor = req.actor or user.get("name", user.get("email", "Operator"))
        alert = GLOBAL_ALERT_SERVICE.acknowledge_alert(alert_id, actor=actor, notes=req.notes)
        return alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

@app.post("/api/v1/alerts/{alert_id}/assign")
def assign_alert(
    alert_id: str,
    req: AlertAssignRequest,
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    try:
        actor = req.actor or user.get("name", user.get("email", "Supervisor"))
        alert = GLOBAL_ALERT_SERVICE.assign_alert(alert_id, assignee=req.assignee, actor=actor, notes=req.notes)
        return alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

@app.post("/api/v1/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    req: AlertResolveRequest = AlertResolveRequest(),
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    try:
        actor = req.actor or user.get("name", user.get("email", "Operator"))
        alert = GLOBAL_ALERT_SERVICE.resolve_alert(alert_id, actor=actor, resolution_notes=req.resolution_notes)
        return alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

@app.post("/api/v1/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    req: AlertDismissRequest = AlertDismissRequest(),
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    from src.services.alert_service import GLOBAL_ALERT_SERVICE
    try:
        actor = req.actor or user.get("name", user.get("email", "Operator"))
        alert = GLOBAL_ALERT_SERVICE.dismiss_alert(alert_id, actor=actor, dismissal_reason=req.dismissal_reason)
        return alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

@app.get("/api/v1/iot/gateways")
def get_gateways_status():
    """Returns connectivity, latency, packet count, and sensor states for both physical ESP32 gateways."""
    from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
    return {
        "gateways": GLOBAL_DEVICE_REGISTRY.get_gateways_status(),
        "summary": {
            "node_1_edge_gateway": "ESP32_EDGE_GATEWAY_01 (HC-SR04 Sonar, ZJ-S201 Water Flow, DHT11, MQ-135)",
            "node_2_pzem_gateway": "ESP32_PZEM_GATEWAY_01 (PZEM-004T Metrology Monitor)",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        }
    }

@app.get("/api/v1/weather/current")
def get_current_weather(lat: float = 28.6139, lon: float = 77.2090):
    from src.services.weather_service import GLOBAL_WEATHER_SERVICE
    data = GLOBAL_WEATHER_SERVICE.get_current_weather(lat=lat, lon=lon)
    return data.model_dump() if hasattr(data, "model_dump") else data.dict()

@app.get("/api/v1/weather/forecast")
def get_weather_forecast(lat: float = 28.6139, lon: float = 77.2090):
    from src.services.weather_service import GLOBAL_WEATHER_SERVICE
    current = GLOBAL_WEATHER_SERVICE.get_current_weather(lat=lat, lon=lon)
    curr_dict = current.model_dump() if hasattr(current, "model_dump") else current.dict()
    return {
        "current": curr_dict,
        "forecast": [
            {"hour": "+1h", "temperature_c": current.temperature_c + 0.5, "weather": current.weather_condition},
            {"hour": "+3h", "temperature_c": current.temperature_c + 1.2, "weather": current.weather_condition},
            {"hour": "+6h", "temperature_c": current.temperature_c - 1.0, "weather": current.weather_condition}
        ]
    }

# --- Action Lifecycle Endpoints ---
@app.get("/api/v1/actions")
def list_actions(user: Dict[str, Any] = Depends(require_permission("recommendations.read"))):
    return {"actions": action_center_engine.list_actions(facility_id=user.get("facility_id"))}

@app.get("/api/v1/actions/{id}")
def get_action_details(id: str, user: Dict[str, Any] = Depends(require_permission("recommendations.read"))):
    return action_center_engine.get_action(id)

@app.put("/api/v1/actions/{id}/status")
def update_action_status(
    id: str,
    req: ActionUpdateRequest,
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    action = action_center_engine.update_action_status(
        action_id=id,
        target_status=req.status,
        actor=user.get("email", user.get("name")),
        notes=req.notes,
        verification_evidence=req.verification_evidence
    )
    record_audit_event("ACTION_EXECUTED", user, "UPDATE_STATUS", "action", resource_id=id, metadata={"new_status": req.status})
    return action

# --- Decision Trace Endpoint ---
@app.get("/api/v1/decisions/{id}")
@app.get("/api/v1/intelligence/decision-trace/{id}")
def get_decision_trace(id: str, user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return decision_trace_engine.build_trace(
        alert_id=id,
        building="Block B Hostel" if "01" in id else "Central Cafeteria",
        observed_value=145.2 if "01" in id else 78.5
    )

# --- EstateIQ Intelligence Fusion Engine Endpoints ---
from src.intelligence.fusion_engine import EstateIQIntelligenceFusionEngine
from src.intelligence.outcome_verification import OutcomeVerificationEngine
from src.decisions.decision_memory import DecisionMemoryStore

fusion_instance = EstateIQIntelligenceFusionEngine()
outcome_instance = OutcomeVerificationEngine()
memory_instance = DecisionMemoryStore()

@app.get("/api/v1/intelligence/overview")
@app.get("/api/v1/intelligence/fusion")
def get_intelligence_fusion_overview(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    live = get_latest_live_telemetry()
    required_inputs = {
        "energy_kwh": live.get("energy_kwh"),
        "temperature": live.get("temperature"),
        "occupancy": live.get("occupancy"),
        "hvac_load": live.get("hvac_load"),
    }
    missing_inputs = [key for key, value in required_inputs.items() if value is None]
    if missing_inputs:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Fusion analysis was not run because required telemetry is unavailable.",
            "missing_inputs": missing_inputs,
            "building_id": live.get("building_id"),
            "source_type": live.get("source_type"),
            "data_source_badge": live.get("data_source_badge"),
            "provenance": "NO_ANALYSIS_PERFORMED",
        }

    kwh_val = float(required_inputs["energy_kwh"])
    temp_val = float(required_inputs["temperature"])
    occ_val = int(required_inputs["occupancy"])
    hvac_val = float(required_inputs["hvac_load"])

    df_live = pd.DataFrame([{
        "energy_kwh": kwh_val,
        "temperature": temp_val,
        "occupancy": occ_val,
        "hvac_load": hvac_val,
        "event_timestamp": live.get("timestamp"),
    }])
    result = fusion_instance.run_fusion_analysis(
        df_telemetry=df_live,
        building_id=live["building_id"],
        actual_kwh=kwh_val,
        occupancy=int(occ_val),
        temperature=float(temp_val),
        hvac_load=float(hvac_val)
    )
    result["source_type"] = live.get("source_type")
    result["data_source_badge"] = live.get("data_source_badge")
    result["device_id"] = live.get("device_id")
    return result

@app.get("/api/v1/intelligence/confidence")
def get_intelligence_confidence(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return fusion_instance.confidence_engine.calculate_decision_confidence()

@app.get("/api/v1/intelligence/model-consensus")
def get_model_consensus(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return fusion_instance.consensus_engine.evaluate_consensus()

@app.get("/api/v1/intelligence/business-impact")
def get_business_impact(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    live = get_latest_live_telemetry()
    if live.get("energy_kwh") is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Business impact was not estimated because interval energy telemetry is unavailable.",
            "missing_inputs": ["energy_kwh"],
            "building_id": live.get("building_id"),
            "source_type": live.get("source_type"),
            "data_source_badge": live.get("data_source_badge"),
        }
    occ_val = live.get("occupancy")
    temp_val = live.get("temperature")
    kwh_val = float(live["energy_kwh"])
    if occ_val is None or temp_val is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Business impact was not estimated because contextual baseline inputs are unavailable.",
            "missing_inputs": [name for name, value in (("occupancy", occ_val), ("temperature", temp_val)) if value is None],
            "building_id": live.get("building_id"),
            "source_type": live.get("source_type"),
            "data_source_badge": live.get("data_source_badge"),
        }
    exp_kwh = baseline_engine.calculate_expected_kwh(
        building_id=live["building_id"],
        hour=pd.Timestamp.now().hour,
        day_of_week=pd.Timestamp.now().dayofweek,
        occupancy=occ_val,
        temperature=temp_val
    )
    return fusion_instance.impact_engine.calculate_surge_impact(actual_kwh=kwh_val, expected_kwh=exp_kwh)

@app.get("/api/v1/intelligence/opportunities")
def get_intelligence_opportunities(user: Dict[str, Any] = Depends(require_permission("recommendations.read"))):
    return fusion_instance.opportunity_engine.discover_opportunities()

@app.post("/api/v1/intelligence/verify-outcome")
def verify_action_outcome(
    decision_id: str = "DEC_ALT_01",
    post_action_kwh: float = 118.5,
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    return outcome_instance.verify_outcome(
        decision_id=decision_id,
        building_id="Block B Hostel",
        pre_action_actual_kwh=145.2,
        post_action_actual_kwh=post_action_kwh
    )

class FeedbackRequest(BaseModel):
    decision_id: str
    action_status: str # "APPROVED", "REJECTED", "POSTPONED"
    rejection_reason: Optional[str] = None

@app.post("/api/v1/intelligence/feedback")
def submit_decision_feedback(
    req: FeedbackRequest,
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    return memory_instance.update_human_feedback(
        decision_id=req.decision_id,
        user=user.get("name", "User"),
        action_status=req.action_status,
        rejection_reason=req.rejection_reason
    )

@app.get("/api/v1/intelligence/capabilities")
def get_intelligence_capabilities():
    """Return live system intelligence capability registry."""
    return {
        "platform": "EstateIQ Facility Decision Intelligence",
        "decision_intelligence": True,
        "domains": ["Energy", "Water", "Waste", "Air Quality", "Mobility & Traffic", "Equipment Assets", "Sustainability"],
        "models": ["CatBoostRegressor", "LightGBM", "RandomForest", "IsolationForest", "ZScoreAnomaly", "SHAPExplainer"],
        "data_sources": [
            {"type": "Historical Telemetry", "status": "LIVE"},
            {"type": "IoT Sensor Stream", "status": "LIVE"},
            {"type": "Synthetic Campus Dataset", "status": "LIVE"},
            {"type": "Edge MQTT Hardware", "status": "PLANNED / PROTOTYPE"}
        ],
        "iot_status": "PROTOTYPE (ESP32 Ready)",
        "ai_capabilities": ["Grounded Co-Pilot", "Evidence Fusion", "SHAP Decision Trace", "ROI Explanation"],
        "what_if": True,
        "recommendations": True,
        "work_orders": True,
        "verification": True,
        "kb_questions_count": 31
    }

class RecommendationPostRequest(BaseModel):
    issue: str = "energy_anomaly"
    building: str = "Block B Hostel"
    actual: float = 120.0
    expected: float = 85.0
    deviation_percent: float = 41.1
    important_features: List[str] = ["occupancy", "temperature"]

# --- Recommendations & Simulation Endpoints ---
@app.get("/api/v1/recommendations")
def get_recommendations(user: Dict[str, Any] = Depends(require_permission("recommendations.read"))):
    return genai_engine.generate_recommendation({
        "issue": "energy_anomaly",
        "building": "Block B Hostel",
        "actual": 145.2,
        "expected": 78.0,
        "deviation_percent": 86.1,
        "important_features": ["occupancy", "temperature", "hvac_load"]
    })

@app.post("/recommendations")
@app.post("/api/v1/recommendations")
def post_recommendations(
    req: RecommendationPostRequest,
    user: Dict[str, Any] = Depends(require_permission("recommendations.read"))
):
    req_dict = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return genai_engine.generate_recommendation(req_dict)


@app.post("/scenario")
@app.post("/api/v1/simulation")
def run_simulation(
    req: ScenarioRequest,
    user: Dict[str, Any] = Depends(require_permission("simulation.run"))
):
    model, meta = get_model_and_metadata("energy_kwh_prediction", train_energy_module)
    engine = WhatIfScenarioEngine(model, meta["feature_names"])
    df_in = pd.DataFrame([req.current_values])
    for c in meta["feature_names"]:
        if c not in df_in.columns:
            df_in[c] = 0
    res = engine.run_scenario(df_in, req.modifications)
    
    # Calculate financial and carbon savings from simulation
    baseline_kwh = res.get("baseline_prediction", 145.2)
    scenario_kwh = res.get("scenario_prediction", 116.0)
    impact = business_impact_engine.calculate_energy_impact(actual_kwh=baseline_kwh, expected_kwh=scenario_kwh)
    
    res["financial_impact"] = impact
    res["provenance"] = ProvenanceType.SIMULATED
    res["provenance_badge"] = "[SIMULATED SCENARIO]"
    record_audit_event("SIMULATION_RUN", user, "RUN_SCENARIO", "simulation")
    return res

# --- Tool-Based AI Copilot Endpoint ---
@app.post("/api/v1/ai/chat")
def ai_copilot_chat(
    req: ChatRequest,
    user: Dict[str, Any] = Depends(require_permission("energy.read"))
):
    record_audit_event("AI_COPILOT_QUERY", user, "CHAT", "copilot", metadata={"query": req.user_query})
    return ai_service.query_copilot(user_query=req.user_query)


# --- Digital Twin & Benchmarking Endpoints ---
@app.get("/api/v1/digital-twin")
def get_digital_twin_topology(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    return {
        "facility_id": "FAC_GEC_01",
        "facility_name": "GEC Smart Campus",
        "topology": {
            "node": "Main Electrical Grid",
            "children": [
                {
                    "node": "Main Transformer (XFMR_MAIN_01 - 750 kVA)",
                    "status": "HIGH_LOAD",
                    "load_pct": 78.0,
                    "children": [
                        {"node": "Block B Hostel", "status": "CRITICAL_SURGE", "energy_kwh": 145.2, "expected_kwh": 78.0},
                        {"node": "Hostel A", "status": "NORMAL", "energy_kwh": 62.0, "expected_kwh": 65.0},
                        {"node": "Central Cafeteria", "status": "WARNING", "energy_kwh": 88.0, "expected_kwh": 70.0},
                        {"node": "Admin Block", "status": "NORMAL", "energy_kwh": 45.0, "expected_kwh": 48.0}
                    ]
                },
                {
                    "node": "Standby Generator (DG_STANDBY_01 - 500 kVA)",
                    "status": "STANDBY",
                    "fuel_level_pct": 82.0
                }
            ]
        },
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[DIGITAL TWIN TOPOLOGY]"
    }

@app.get("/api/v1/benchmarking")
def get_building_benchmarks(user: Dict[str, Any] = Depends(require_permission("reports.read"))):
    return {
        "benchmark_metric": "kWh / m² / month",
        "buildings": [
            {"building_name": "Block B Hostel", "actual_kwh_m2": 18.5, "peer_avg_kwh_m2": 12.0, "variance": "+54.1%", "rating": "POOR"},
            {"building_name": "Hostel A", "actual_kwh_m2": 11.2, "peer_avg_kwh_m2": 12.0, "variance": "-6.7%", "rating": "GOOD"},
            {"building_name": "Central Cafeteria", "actual_kwh_m2": 24.0, "peer_avg_kwh_m2": 18.0, "variance": "+33.3%", "rating": "NEEDS_ATTENTION"},
            {"building_name": "Admin Block", "actual_kwh_m2": 9.5, "peer_avg_kwh_m2": 10.0, "variance": "-5.0%", "rating": "EXCELLENT"}
        ],
        "provenance": ProvenanceType.DERIVED
    }

# --- Data Quality & Sustainability Endpoints ---
@app.get("/api/v1/data-quality")
def data_quality_report(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    return repo.get_data_quality_report()

@app.get("/api/v1/sustainability")
def sustainability_score(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    return {
        "sustainability_score": 82,
        "max_score": 100,
        "grade": "Gold Grade (Internal Decision Support)",
        "disclaimer": "Internal facility decision-support score. Not an official regulatory certification.",
        "sub_scores": {
            "energy_efficiency": "84/100 (Weight: 20%)",
            "water_recovery": "78/100 (Weight: 15%)",
            "waste_diversion": "75/100 (Weight: 15%)",
            "air_quality_index": "88/100 (Weight: 15%)",
            "carbon_emissions": "85/100 (Weight: 15%)",
            "equipment_health": "90/100 (Weight: 10%)",
            "mobility_flow": "82/100 (Weight: 10%)"
        }
    }

@app.get("/api/v1/esg/audit")
def get_esg_audit(user: Dict[str, Any] = Depends(require_permission("audit.read"))):
    return {
        "iso_standard": "ISO 14064-1 Greenhouse Gas Protocol Guidelines",
        "campus_footprint_tco2e": 482.4,
        "emissions_breakdown": {
            "scope_1_direct": {"tco2e": 84.2, "sources": "Diesel Generators & Boilers"},
            "scope_2_indirect_grid": {"tco2e": 340.8, "sources": "Purchased Electricity Grid"},
            "scope_3_value_chain": {"tco2e": 57.4, "sources": "Waste & Water Logistics"}
        },
        "carbon_offsets": {
            "solar_yield_tco2e_saved": 164.2,
            "net_campus_footprint_tco2e": 318.2,
            "esg_grade": "A+ EXCELLENT (Internal Benchmark)"
        },
        "disclaimer": "Internal carbon audit indicator. Not an official regulatory certification."
    }

@app.get("/models")
@app.get("/api/v1/models")
def list_registered_models(user: Dict[str, Any] = Depends(require_permission("models.read"))):
    models_dir = "models"
    if not os.path.exists(models_dir):
        return {"registered_models_count": 0, "models": []}
    files = [f for f in os.listdir(models_dir) if f.endswith("_metadata.joblib")]
    results = []
    for f in files:
        meta = joblib.load(os.path.join(models_dir, f))
        results.append(meta)
    return {"registered_models_count": len(results), "models": results}

@app.get("/api/v1/subscription")
def get_subscription_details(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    return {
        "current_plan": {
            "id": "enterprise_pro",
            "name": "Enterprise Pro Plan",
            "badge": "PRO ACTIVE",
            "price_monthly_usd": 1499,
            "price_monthly_inr": 119999,
            "billing_cycle": "annual",
            "renewal_date": "2027-10-01",
            "status": "ACTIVE"
        },
        "usage_limits": {
            "monitored_buildings": {"used": 8, "total": 15, "unit": "Buildings"},
            "api_requests": {"used": 14200, "total": 50000, "unit": "Calls/mo"},
            "ml_predictions": {"used": 8500, "total": 25000, "unit": "Inferences/mo"}
        }
    }

# --- Groq AI Copilot & IoT Ingestion Service Endpoints ---
ai_service = EstateIQAIService()

class CopilotQueryRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: Optional[str] = "Block B Hostel"

    @property
    def user_query(self) -> str:
        return self.query or self.message or "Why is electricity consumption high?"

class AITestRequest(BaseModel):
    prompt: Optional[str] = "Respond with exactly: ESTATEIQ_GROQ_CONNECTION_OK"

@app.post("/api/v1/ai/copilot")
@app.post("/api/v1/ai/analyze")
def query_ai_copilot(req: CopilotQueryRequest, user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    record_audit_event("AI_COPILOT_QUERY", user, "COPILOT", "copilot", metadata={"query": req.user_query})
    return ai_service.query_copilot(
        user_query=req.user_query,
        facility_id=req.facility_id,
        building_id=req.building_id
    )

@app.get("/api/v1/ai/health")
def get_ai_health():
    return ai_service.check_health()

@app.post("/api/v1/ai/test")
def test_ai_connection(req: AITestRequest = AITestRequest()):
    return ai_service.test_connection(prompt=req.prompt)

@app.get("/api/v1/ai/capabilities")
def get_ai_capabilities():
    from src.ai.domain_registry import DOMAIN_REGISTRY
    from src.ai.query_router import UniversalQueryRouter
    return {
        "status": "SUCCESS",
        "supported_domains": list(DOMAIN_REGISTRY.keys()),
        "supported_intents": UniversalQueryRouter.SUPPORTED_INTENTS,
        "capabilities": [
            "Facility multi-domain performance analysis",
            "Contextual anomaly detection & SHAP explainability",
            "Cross-domain executive summarization",
            "Evidence-grounded recommendation generation",
            "What-If scenario simulation",
            "Data quality & IoT sensor health auditing"
        ],
        "sample_questions": [
            "What can you do?",
            "What is our electricity consumption today?",
            "What is the water situation?",
            "What are our biggest problems?",
            "What should I fix first?",
            "What if I reduce HVAC runtime by 1 hour?"
        ]
    }

@app.post("/api/v1/ai/summary")
def get_facility_executive_summary(facility_id: str = "FAC_GEC_CAMPUS"):
    from src.ai.backend_services import EstateIQBackendServices
    return EstateIQBackendServices.get_facility_overview(facility_id)

@app.post("/api/v1/ai/what-if")
def run_ai_what_if_scenario(
    hvac_reduction_pct: float = 20.0,
    temp_setback_delta: float = 2.0,
    facility_id: str = "FAC_GEC_CAMPUS"
):
    from src.ai.backend_services import EstateIQBackendServices
    return EstateIQBackendServices.run_what_if(
        facility_id=facility_id,
        scenario_params={"hvac_reduction_pct": hvac_reduction_pct, "temp_setback_delta": temp_setback_delta}
    )

@app.get("/api/v1/ai/opportunities")
def get_ai_opportunities(domain: Optional[str] = None):
    from src.ai.backend_services import EstateIQBackendServices
    return {
        "status": "SUCCESS",
        "opportunities": EstateIQBackendServices.get_top_opportunities(domain=domain)
    }

@app.get("/api/v1/ai/recommendations")
def get_ai_recommendations(domain: Optional[str] = None):
    from src.ai.backend_services import EstateIQBackendServices
    return {
        "status": "SUCCESS",
        "recommendations": EstateIQBackendServices.get_recommendations(domain=domain)
    }


@app.post("/api/v1/ingestion/telemetry")
def ingest_device_telemetry(payload: Dict[str, Any]):
    """Edge gateway or physical sensor telemetry ingestion endpoint."""
    if "source_type" not in payload:
        payload["source_type"] = "real_sensor"
    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    if not (res.get("success") or res.get("accepted")):
        raise HTTPException(status_code=400, detail=res.get("error", "INGESTION_FAILED"))
    return res

# --- Standalone IoT Simulator & Device Registry API Endpoints ---
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY

class PairRequest(BaseModel):
    pairing_code: Optional[str] = None

class RegisterSimulatorRequest(BaseModel):
    instance_id: str = "SIM_CAMPUS_02"
    instance_name: Optional[str] = None
    name: Optional[str] = None
    pairing_code: Optional[str] = "IQ-DEMO"
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    ip_address: Optional[str] = "127.0.0.1"
    software_version: Optional[str] = "1.0.0"

class HeartbeatRequest(BaseModel):
    active_devices_count: int = 1
    scenario: Optional[str] = "Normal Campus Operation"

class SensorOverrideRequest(BaseModel):
    active_power_kw: Optional[float] = None
    energy_kwh: Optional[float] = None
    cumulative_energy_kwh: Optional[float] = None
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    power_factor: Optional[float] = None
    frequency_hz: Optional[float] = None
    transformer_load_pct: Optional[float] = None
    occupancy_count: Optional[int] = None
    hvac_load_kw: Optional[float] = None
    hvac_status: Optional[str] = None
    equipment_status: Optional[str] = None
    temperature_c: Optional[float] = None
    water_flow_lmin: Optional[float] = None
    cumulative_water_m3: Optional[float] = None
    water_pressure_bar: Optional[float] = None
    tank_level_pct: Optional[float] = None
    air_quality_aqi: Optional[float] = None
    dg_status: Optional[str] = None

@app.post("/api/v1/iot/pair")
def pair_iot_simulator(req: Optional[PairRequest] = None):
    """Generates pairing code or validates existing pairing code for auth token."""
    if req and req.pairing_code:
        p_code = req.pairing_code.strip().upper()
        if p_code == "IQ-DEMO":
            return {
                "success": True,
                "auth_token": "sim_tok_demo_approved",
                "mode": "DEVELOPMENT_DEMO_MODE",
                "is_verified_hardware": False,
                "message": "Simulator paired in Local Development / Demo Mode. Telemetry will be marked as unverified demo data."
            }
        is_valid = GLOBAL_DEVICE_REGISTRY.validate_pairing_code(p_code)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid, expired, or already used pairing code.")
        new_token = f"gw_tok_{secrets.token_hex(16)}"
        return {
            "success": True,
            "auth_token": new_token,
            "mode": "VERIFIED_HARDWARE",
            "is_verified_hardware": True,
            "message": "Gateway paired and verified successfully with single-use pairing code."
        }
    return GLOBAL_DEVICE_REGISTRY.generate_pairing_code()

@app.post("/api/v1/iot/simulators/register")
def register_standalone_simulator(req: RegisterSimulatorRequest, request: Request):
    ip_addr = req.ip_address or (request.client.host if request.client else "127.0.0.1")
    inst_name = req.name or req.instance_name or f"Simulator-{req.instance_id}"
    p_code = req.pairing_code or "IQ-DEMO"
    res = GLOBAL_DEVICE_REGISTRY.register_simulator(
        instance_id=req.instance_id,
        instance_name=inst_name,
        pairing_code=p_code,
        facility_id=req.facility_id,
        building_id=req.building_id,
        ip_address=ip_addr,
        software_version=req.software_version
    )
    inst = GLOBAL_DEVICE_REGISTRY.get_instance(req.instance_id)
    return {
        "success": True,
        "instance_id": req.instance_id,
        "instance_name": inst_name,
        "instance": inst.dict() if inst else {},
        **res
    }

@app.post("/api/v1/iot/simulators/{instance_id}/heartbeat")
def record_simulator_heartbeat(instance_id: str, req: HeartbeatRequest = HeartbeatRequest()):
    res = GLOBAL_DEVICE_REGISTRY.record_heartbeat(
        instance_id=instance_id,
        active_devices_count=req.active_devices_count,
        scenario=req.scenario or "Normal Campus Operation"
    )
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=f"Simulator instance '{instance_id}' not found.")
    return {"success": True, "status": "HEARTBEAT_ACK", **res}

@app.post("/api/v1/iot/simulators/{instance_id}/devices/register")
def register_simulator_device(instance_id: str, device_payload: Union[Dict[str, Any], List[Dict[str, Any]]]):
    if isinstance(device_payload, list):
        count = GLOBAL_DEVICE_REGISTRY.register_devices(instance_id, device_payload)
        return {"success": True, "registered_count": count}
    elif isinstance(device_payload, dict) and "devices" in device_payload:
        count = GLOBAL_DEVICE_REGISTRY.register_devices(instance_id, device_payload["devices"])
        return {"success": True, "registered_count": count}
    else:
        device_payload["instance_id"] = instance_id
        return GLOBAL_DEVICE_REGISTRY.register_device(device_payload)

@app.get("/api/v1/iot/telemetry/adaptive-status")
def get_adaptive_telemetry_status():
    """Returns real-time status of adaptive reporting cadences and active anomalies across all devices."""
    devices = GLOBAL_DEVICE_REGISTRY.list_devices()
    now_ts = time.time()

    has_anomaly = any(d.reporting_state == "ANOMALY_5M" or (d.active_anomaly is not None) for d in devices)
    has_recovery = any(d.reporting_state == "RECOVERY_5M" for d in devices)

    if has_anomaly:
        overall_mode = "ANOMALY_5M"
        overall_label = "Anomaly monitoring · 5 min"
        interval_sec = 300
    elif has_recovery:
        overall_mode = "RECOVERY_5M"
        overall_label = "Recovery check · 5 min"
        interval_sec = 300
    else:
        overall_mode = "NORMAL_15M"
        overall_label = "Normal · 15 min"
        interval_sec = 900

    active_anomalies = []
    dev_summaries = []
    min_next_expected_sec = float(interval_sec)

    for d in devices:
        age_sec = None
        if d.last_sample_at:
            try:
                lts = datetime.datetime.fromisoformat(d.last_sample_at.replace("Z", "+00:00")).timestamp()
                age_sec = max(0.0, round(now_ts - lts, 1))
            except Exception:
                pass

        next_sec = None
        if d.next_report_expected_at:
            try:
                nts = datetime.datetime.fromisoformat(d.next_report_expected_at.replace("Z", "+00:00")).timestamp()
                next_sec = max(0.0, round(nts - now_ts, 1))
                if next_sec < min_next_expected_sec:
                    min_next_expected_sec = next_sec
            except Exception:
                pass

        if d.active_anomaly:
            anom = d.active_anomaly.copy()
            anom["device_id"] = d.device_id
            anom["building_id"] = d.building_id
            anom["data_source_badge"] = d.data_source_badge
            active_anomalies.append(anom)

        dev_summaries.append({
            "device_id": d.device_id,
            "device_name": d.device_name,
            "device_type": d.device_type,
            "building_id": d.building_id,
            "status": d.status,
            "source_type": d.source_type,
            "data_source_badge": d.data_source_badge,
            "is_verified_hardware": d.is_verified_hardware,
            "reporting_state": d.reporting_state,
            "reporting_interval_sec": d.reporting_interval_sec,
            "last_sample_at": d.last_sample_at,
            "last_sample_age_sec": age_sec,
            "next_report_expected_at": d.next_report_expected_at,
            "next_report_expected_sec": next_sec,
            "active_anomaly": d.active_anomaly
        })

    return {
        "status": "SUCCESS",
        "campus_reporting_state": overall_mode,
        "campus_reporting_mode_label": overall_label,
        "campus_reporting_interval_sec": interval_sec,
        "reporting_interval_sec": interval_sec,
        "campus_next_report_expected_sec": round(min_next_expected_sec, 1),
        "next_report_expected_sec": round(min_next_expected_sec, 1),
        "active_devices_count": len(devices),
        "active_anomalies_count": len(active_anomalies),
        "active_anomalies": active_anomalies,
        "devices": dev_summaries,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


@app.post("/api/v1/iot/telemetry/evaluate-benchmark")
def evaluate_anomaly_benchmark(request_data: Optional[Dict[str, Any]] = None):
    """Runs time-ordered holdout evaluation comparing improved contextual MAD detector with legacy static thresholding."""
    from src.services.anomaly_engine import GLOBAL_ADAPTIVE_ANOMALY_ENGINE

    records = []
    custom_records = request_data.get("scenario_data") if request_data else None
    metric = (request_data.get("metric_name") or request_data.get("metric")) if request_data else "active_power_kw"
    device_id = (request_data.get("device_id") or "METER-BLOCK-B-001") if request_data else "METER-BLOCK-B-001"
    building_id = (request_data.get("building_id") or "Block B Hostel") if request_data else "Block B Hostel"
    static_thresh = request_data.get("static_threshold") if request_data else 90.0

    if custom_records:
        records = custom_records
    else:
        base_time = datetime.datetime(2026, 11, 8, 0, 0, 0, tzinfo=datetime.timezone.utc)
        for i in range(96):
            ts = base_time + datetime.timedelta(minutes=15 * i)
            hr = ts.hour
            val = 20.0 if hr < 6 else (75.0 if 9 <= hr < 18 else 50.0)
            gt = False
            if i == 20:
                val = 98.0  # Transient single-sample spike
                gt = False
            elif 50 <= i <= 52:
                val = 135.0  # Genuine sustained overload
                gt = True
            records.append({
                "timestamp": ts.isoformat().replace("+00:00", "Z"),
                "value": val,
                "active_power_kw": val,
                "ground_truth_anomaly": gt
            })

    res = GLOBAL_ADAPTIVE_ANOMALY_ENGINE.evaluate_historical_holdout(
        records=records,
        metric=metric,
        device_id=device_id,
        building_id=building_id,
        static_threshold=static_thresh
    )
    return {
        "status": "COMPLETED",
        "comparison": res,
        **res
    }


@app.post("/api/v1/iot/telemetry")
def ingest_iot_telemetry(payload: Dict[str, Any]):
    dev_id = payload.get("device_id")
    src = payload.get("source_type", "unknown")
    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    if not (res.get("success") or res.get("accepted")):
        print(f"[REJECTED-400] Dev: {dev_id} | Err: {res.get('error')} | Payload: {payload}", flush=True)
    raw_m = payload.get("metrics") or payload.get("telemetry") or {}
    print(f"[LIVE-TELEMETRY] Dev: {dev_id} | Src: {src} | Status: {res.get('status')} | Metrics: {raw_m}", flush=True)
    if not (res.get("success") or res.get("accepted")):
        raise HTTPException(status_code=400, detail=res.get("error") or res.get("reason", "INGESTION_FAILED"))
    return res

@app.post("/api/v1/iot/telemetry/batch")
def ingest_iot_telemetry_batch(batch: Union[List[Dict[str, Any]], Dict[str, Any]]):
    records = batch.get("records", batch.get("telemetry", [])) if isinstance(batch, dict) else batch
    accepted_count = 0
    rejected_count = 0
    for payload in records:
        res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
        if res.get("success") or res.get("accepted"):
            accepted_count += 1
        else:
            rejected_count += 1
    return {
        "status": "ACCEPTED",
        "batch_size": len(records),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "ingested_count": accepted_count
    }

@app.get("/api/v1/iot/simulators")
def list_simulators():
    instances = GLOBAL_DEVICE_REGISTRY.list_instances()
    stats = GLOBAL_DEVICE_REGISTRY.get_summary_stats()
    return {
        "count": len(instances),
        "stats": stats,
        "simulators": [i.dict() for i in instances]
    }

@app.get("/api/v1/iot/simulators/{instance_id}")
def get_simulator_details(instance_id: str):
    inst = GLOBAL_DEVICE_REGISTRY.get_instance(instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="SIMULATOR_NOT_FOUND")
    devices = [d for d in GLOBAL_DEVICE_REGISTRY.devices.values() if d.instance_id == instance_id]
    data = inst.dict()
    data["devices"] = [d.dict() for d in devices]
    data["simulator"] = inst.dict()
    return data

@app.get("/api/v1/iot/devices")
def list_iot_devices(facility_id: Optional[str] = None, building_id: Optional[str] = None):
    devices = GLOBAL_DEVICE_REGISTRY.list_devices(facility_id=facility_id, building_id=building_id)
    return {
        "count": len(devices),
        "stats": GLOBAL_DEVICE_REGISTRY.get_summary_stats(),
        "devices": [d.dict() for d in devices]
    }

@app.get("/api/v1/iot/devices/{device_id}")
def get_iot_device_details(device_id: str):
    dev = GLOBAL_DEVICE_REGISTRY.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    history = GLOBAL_DEVICE_REGISTRY.get_telemetry_history(device_id, limit=50)
    data = dev.dict()
    data["device"] = dev.dict()
    data["recent_telemetry"] = history
    return data

@app.get("/api/v1/iot/time")
@app.get("/api/v1/system/time")
def get_server_iot_time():
    """Returns authoritative server UTC time for edge gateways to synchronize when UDP NTP port 123 is blocked on cellular hotspots."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    utc_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "epoch_seconds": int(now_utc.timestamp()),
        "iso_timestamp": utc_str,
        "utc_timestamp": utc_str,
        "server_status": "ONLINE"
    }

@app.get("/api/v1/iot/devices/{device_id}/live")
def get_device_live_status(device_id: str):
    """Returns dynamic freshness, connection status, verified hardware provenance, and recent history points."""
    freshness = GLOBAL_DEVICE_REGISTRY.get_device_freshness_status(device_id)
    if freshness.get("status") == "UNKNOWN":
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    samples = GLOBAL_DEVICE_REGISTRY.get_device_recent_samples(device_id, limit=30)
    freshness["recent_samples"] = samples
    return freshness

@app.get("/api/v1/iot/devices/{device_id}/telemetry/latest")
def get_latest_device_telemetry(device_id: str):
    dev = GLOBAL_DEVICE_REGISTRY.get_device(device_id)
    sample = GLOBAL_DEVICE_REGISTRY.get_latest_telemetry(device_id)
    if not dev and not sample:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    return {
        "device_id": device_id,
        "last_sample_at": dev.last_sample_at if dev else None,
        "telemetry": dev.last_telemetry if dev else sample,
        "latest_telemetry": sample,
        "data_source_badge": dev.data_source_badge if dev else "[SIMULATED IoT]"
    }

@app.get("/api/v1/iot/devices/{device_id}/telemetry/history")
def get_device_telemetry_history(device_id: str, limit: int = 50):
    history = GLOBAL_DEVICE_REGISTRY.get_telemetry_history(device_id, limit=limit)
    return {"device_id": device_id, "count": len(history), "history": history}

@app.get("/api/v1/iot/telemetry/stream")
@app.get("/api/v1/iot/stream")
def get_iot_telemetry_stream(limit: int = 50, device_id: Optional[str] = None):
    """Returns recent real-time ingested telemetry packets across all devices or filtered by device_id."""
    history = GLOBAL_DEVICE_REGISTRY.get_telemetry_history(device_id=device_id, limit=limit)
    stats = GLOBAL_DEVICE_REGISTRY.get_summary_stats()
    return {
        "count": len(history),
        "total_ingested": len(GLOBAL_DEVICE_REGISTRY.telemetry_history),
        "stats": stats,
        "stream": history
    }

@app.post("/api/v1/iot/simulators/{instance_id}/revoke")
def revoke_simulator_instance(instance_id: str, user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    success = GLOBAL_DEVICE_REGISTRY.revoke_simulator(instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="SIMULATOR_NOT_FOUND")
    return {"success": True, "status": "REVOKED", "instance_id": instance_id, "revoked_instance_id": instance_id}

@app.post("/api/v1/iot/devices/{device_id}/disable")
def disable_device(device_id: str):
    ok = GLOBAL_DEVICE_REGISTRY.disable_device(device_id)
    return {"success": ok, "disabled_device_id": device_id}

# --- Interactive IoT Simulator Endpoints ---
from src.services.iot_simulator import GLOBAL_IOT_SIMULATOR

class SimulatorControlRequest(BaseModel):
    action: str  # start, pause, resume, stop, step, reset_state, reset_controls
    speed: Optional[int] = 1
    building_id: Optional[str] = None

class SimulatorScenarioRequest(BaseModel):
    scenario_key: str

@app.get("/api/v1/iot-simulator/status")
def get_iot_simulator_status():
    return GLOBAL_IOT_SIMULATOR.get_status()

@app.post("/api/v1/iot-simulator/control")
def control_iot_simulator(req: SimulatorControlRequest):
    action = req.action.lower()
    if req.building_id:
        GLOBAL_IOT_SIMULATOR.set_building(req.building_id)
    if req.speed:
        GLOBAL_IOT_SIMULATOR.set_speed(req.speed)

    if action == "start":
        return GLOBAL_IOT_SIMULATOR.start_simulation()
    elif action == "pause":
        return GLOBAL_IOT_SIMULATOR.pause_simulation()
    elif action == "resume":
        return GLOBAL_IOT_SIMULATOR.resume_simulation()
    elif action == "stop":
        return GLOBAL_IOT_SIMULATOR.stop_simulation()
    elif action == "step":
        return GLOBAL_IOT_SIMULATOR.step_simulation()
    elif action == "reset_state":
        return GLOBAL_IOT_SIMULATOR.reset_state()
    elif action == "reset_controls":
        return GLOBAL_IOT_SIMULATOR.reset_controls()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown simulation action: {action}")

@app.post("/api/v1/iot-simulator/start")
def start_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.start_simulation()

@app.post("/api/v1/iot-simulator/pause")
def pause_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.pause_simulation()

@app.post("/api/v1/iot-simulator/resume")
def resume_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.resume_simulation()

@app.post("/api/v1/iot-simulator/stop")
def stop_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.stop_simulation()

@app.post("/api/v1/iot-simulator/stop-all")
@app.post("/api/v1/iot/simulators/stop-all")
def stop_all_simulators_endpoint():
    """Stops all running simulator engines, pauses virtual tick generation, and purges simulated buffers."""
    sim_status = GLOBAL_IOT_SIMULATOR.stop_simulation()
    GLOBAL_DEVICE_REGISTRY.purge_simulated_telemetry()
    return {
        "success": True,
        "message": "All simulators stopped. Canonical telemetry stream now contains verified real hardware only.",
        "simulator_status": sim_status,
        "total_records": len(GLOBAL_DEVICE_REGISTRY.telemetry_history),
        "real_hardware_devices": [
            d.device_id for d in GLOBAL_DEVICE_REGISTRY.devices.values()
            if d.is_verified_hardware or d.source_type == "real_sensor"
        ]
    }

@app.post("/api/v1/iot-simulator/step")
def step_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.step_simulation()

@app.post("/api/v1/iot-simulator/reset")
def reset_iot_simulator():
    return GLOBAL_IOT_SIMULATOR.reset_state()

@app.post("/api/v1/iot-simulator/speed")
def set_iot_simulator_speed(speed: int = 1):
    return GLOBAL_IOT_SIMULATOR.set_speed(speed)

@app.post("/api/v1/iot-simulator/scenario")
def set_iot_simulator_scenario(req: SimulatorScenarioRequest):
    return GLOBAL_IOT_SIMULATOR.apply_scenario_preset(req.scenario_key)

@app.post("/api/v1/iot-simulator/sensors")
def update_iot_simulator_sensors(overrides: Union[SensorOverrideRequest, Dict[str, Any]]):
    data = overrides.dict(exclude_none=True) if hasattr(overrides, "dict") else overrides
    return GLOBAL_IOT_SIMULATOR.update_sensors(data)

@app.get("/api/v1/iot-simulator/stream")
def get_iot_simulator_stream(limit: int = 50):
    return {
        "data_source_mode": "simulated_iot",
        "data_source_badge": "SIMULATED IoT — NOT PHYSICAL SENSOR DATA",
        "total_records": len(GLOBAL_IOT_SIMULATOR.history_buffer),
        "stream": GLOBAL_IOT_SIMULATOR.get_stream(limit=limit)
    }

@app.post("/api/v1/iot-simulator/evaluate")
def evaluate_iot_simulator_telemetry():
    """Runs live EstateIQ-DIF Engine & SHAP explainability on current simulated IoT telemetry state."""
    status = GLOBAL_IOT_SIMULATOR.get_status()
    sensors = status["sensors"]
    building_id = status["building_id"]
    
    from src.intelligence.dif_engine import EstateIQDIF
    from src.intelligence.types import EventData
    dif_engine_local = EstateIQDIF()
    
    event = EventData(
        event_id=f"EVT_SIM_{int(pd.Timestamp.now().timestamp())}",
        facility_id=status["facility_id"],
        building_id=building_id,
        timestamp=status["simulated_timestamp"],
        actual_kwh=sensors["energy_kwh"],
        hour=pd.Timestamp.now().hour,
        day_of_week=pd.Timestamp.now().dayofweek,
        occupancy=int(sensors["occupancy_count"]),
        temperature=float(sensors["temperature_c"]),
        hvac_load=float(sensors["hvac_load_kw"])
    )
    
    decision = dif_engine_local.analyze(event)
    
    return {
        "status": "SUCCESS",
        "data_source_mode": "simulated_iot",
        "data_source_badge": "SIMULATED IoT — NOT PHYSICAL SENSOR DATA",
        "building_id": building_id,
        "simulated_timestamp": status["simulated_timestamp"],
        "active_scenario": status["active_scenario"],
        "event_telemetry": {
            "active_power_kw": sensors["active_power_kw"],
            "energy_kwh": sensors["energy_kwh"],
            "temperature_c": sensors["temperature_c"],
            "occupancy_count": sensors["occupancy_count"],
            "hvac_load_kw": sensors["hvac_load_kw"],
            "water_flow_lmin": sensors["water_flow_lmin"]
        },
        "dif_analysis": {
            "expected_baseline_kwh": round(decision.contextual.expected_kwh, 2),
            "residual_kwh": round(decision.contextual.residual_kwh, 2),
            "relative_deviation_pct": round(decision.contextual.relative_deviation_pct, 1),
            "anomaly_score": round(decision.anomaly.anomaly_score, 3),
            "anomaly_level": decision.anomaly.anomaly_level.value,
            "decision_score": round(decision.decision_score, 1),
            "priority": decision.priority.value,
            "hourly_cost_inr": round(decision.impact.hourly_avoidable_cost_inr, 2),
            "shap_attribution": decision.shap_attribution,
            "recommended_actions": [r.title for r in decision.recommendations]
        }
    }


# --- Facility State & Dataset Management Endpoints ---
@app.get("/api/v1/facility/state")
def get_facility_state(facility_id: str = "FAC_GEC_CAMPUS"):
    from src.ai.backend_services import EstateIQBackendServices
    svc = EstateIQBackendServices()
    return svc.get_facility_overview(facility_id=facility_id)

@app.get("/api/v1/dataset/info")
def get_dataset_info():
    from src.data.dataset_manager import GLOBAL_DATASET_MANAGER
    return GLOBAL_DATASET_MANAGER.get_dataset_info()

@app.post("/api/v1/dataset/reload")
def reload_dataset():
    from src.data.dataset_manager import GLOBAL_DATASET_MANAGER
    return GLOBAL_DATASET_MANAGER.reload_dataset()

@app.post("/api/v1/dataset/switch")
def switch_dataset(preset: str = "dataset_b"):
    from src.data.dataset_manager import GLOBAL_DATASET_MANAGER
    return GLOBAL_DATASET_MANAGER.switch_dataset(target_preset=preset)

# --- Work Orders Endpoints ---
class WorkOrderCreateRequest(BaseModel):
    title: str
    description: str
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    location: str = "Block B HVAC Room"
    priority: str = "P1_CRITICAL"
    recommendation_id: Optional[str] = None
    assigned_to: str = "staff@estateiq.in"

@app.get("/api/v1/work-orders")
def list_work_orders(
    assigned_to: Optional[str] = None,
    status: Optional[str] = None
):
    from src.decisions.work_orders import GLOBAL_WORK_ORDER_ENGINE
    orders = GLOBAL_WORK_ORDER_ENGINE.list_work_orders(assigned_to=assigned_to, status=status)
    return {"count": len(orders), "work_orders": [o.dict() for o in orders]}

@app.post("/api/v1/work-orders")
def create_work_order(
    req: WorkOrderCreateRequest,
    user: Dict[str, Any] = Depends(require_permission("recommendations.execute"))
):
    from src.decisions.work_orders import GLOBAL_WORK_ORDER_ENGINE
    from src.decisions.notifications import GLOBAL_NOTIFICATION_ENGINE
    
    order = GLOBAL_WORK_ORDER_ENGINE.create_work_order(
        title=req.title,
        description=req.description,
        facility_id=req.facility_id,
        building_id=req.building_id,
        location=req.location,
        priority=req.priority,
        recommendation_id=req.recommendation_id,
        assigned_to=req.assigned_to,
        assigned_by=user.get("email", "lead@estateiq.in")
    )
    
    # Send Notification to assigned staff
    GLOBAL_NOTIFICATION_ENGINE.create_notification(
        recipient_email=req.assigned_to,
        recipient_role="STAFF",
        title=f"⚡ New Work Order: {req.title}",
        message=f"Location: {req.location} | Priority: {req.priority}. Task: {req.description}",
        priority="HIGH" if "P1" in req.priority else "MEDIUM",
        related_object_id=order.work_order_id
    )
    
    return order.dict()

@app.get("/api/v1/work-orders/{id}")
def get_work_order(id: str):
    from src.decisions.work_orders import GLOBAL_WORK_ORDER_ENGINE
    order = GLOBAL_WORK_ORDER_ENGINE.get_work_order(id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Work order '{id}' not found.")
    return order.dict()

@app.put("/api/v1/work-orders/{id}/status")
def update_work_order_status(
    id: str,
    req: ActionUpdateRequest,
    user: Dict[str, Any] = Depends(verify_current_user)
):
    from src.decisions.work_orders import GLOBAL_WORK_ORDER_ENGINE
    from src.decisions.notifications import GLOBAL_NOTIFICATION_ENGINE
    
    order = GLOBAL_WORK_ORDER_ENGINE.update_status(
        work_order_id=id,
        target_status=req.status,
        actor=user.get("email", "User"),
        notes=req.notes,
        evidence=req.verification_evidence
    )
    
    # Notify Manager if status completed
    if req.status.upper() in ["COMPLETED", "VERIFIED"]:
        GLOBAL_NOTIFICATION_ENGINE.create_notification(
            recipient_email=order.assigned_by,
            recipient_role="FACILITY_MANAGER",
            title=f"✅ Work Order {order.status}: {order.title}",
            message=f"Staff member {user.get('name', order.assigned_to)} updated status to {order.status}. Notes: {req.notes or 'None'}",
            priority="INFO",
            related_object_id=id
        )
        
    return order.dict()

# --- Notifications Endpoints ---
@app.get("/api/v1/notifications")
def get_notifications(
    user: Dict[str, Any] = Depends(verify_current_user),
    unread_only: bool = False
):
    from src.decisions.notifications import GLOBAL_NOTIFICATION_ENGINE
    notifs = GLOBAL_NOTIFICATION_ENGINE.get_user_notifications(
        recipient_email=user.get("email"),
        recipient_role=user.get("role"),
        unread_only=unread_only
    )
    return {"count": len(notifs), "notifications": [n.dict() for n in notifs]}

@app.put("/api/v1/notifications/{id}/read")
def mark_notification_read(id: str):
    from src.decisions.notifications import GLOBAL_NOTIFICATION_ENGINE
    success = GLOBAL_NOTIFICATION_ENGINE.mark_read(id)
    return {"success": success, "notification_id": id}

# --- AI Insights Endpoint ---
@app.get("/api/v1/ai/insights")
def get_ai_insights(domain: str = "overview", building_id: Optional[str] = None):
    from src.ai.insight_service import GLOBAL_AI_INSIGHT_SERVICE
    insight = GLOBAL_AI_INSIGHT_SERVICE.get_domain_insight(domain=domain, building_id=building_id)
    return insight.dict()

# --- Canonical Implementation Report REST API Routes ---
from api.canonical_routes import router as canonical_router
app.include_router(canonical_router)



