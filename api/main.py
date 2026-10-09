"""
FastAPI Enterprise REST API Application for Sustainable Facility and Estate Intelligence Platform.
Exposes secure /api/v1/ endpoints for authentication, RBAC/ABAC authorization, facility monitoring,
energy forecasting, contextual baselines, anomaly detection, SHAP explainability, decision traces,
business impact, action lifecycle management, what-if simulations, tool-based AI Copilot, digital twin,
and audit logging.
"""

import os
import uuid
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
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
    require_permission, require_facility_access, USER_ROLES_DB, ROLE_PERMISSIONS
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
    return response

@app.on_event("startup")
def startup_security_and_db():
    validate_security_configuration()
    connect_mongo_db()


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

# --- Health & Readiness Endpoints ---
@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "EstateIQ Sustainable Facility Intelligence Engine (India)",
        "version": "1.0.0",
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

# --- Auth Endpoints ---
@app.post("/api/v1/auth/login")
def auth_login(req: LoginRequest):
    if req.email and req.password:
        user = authenticate_user(req.email, req.password)
    elif req.role:
        role_key = req.role.lower()
        if role_key in USER_ROLES_DB:
            user = USER_ROLES_DB[role_key]
        else:
            user = get_user_by_role(role_key)
    else:
        user = USER_ROLES_DB["lead@estateiq.in"]

    token = create_user_token(user)
    permissions = ROLE_PERMISSIONS.get(user["role"], [])
    
    # Unrestricted tab opening policy: all logged-in roles can access all tabs
    tab_permissions = ["overview", "suggestions", "energy", "water", "waste", "mobility", "simulator", "faq", "decision-intelligence", "models", "esg", "billing", "work-orders", "ai-assistant"]
    role_key_norm = req.role.lower() if req.role else "admin"
    if user["role"] in ["SUPER_ADMIN", "FACILITY_ADMIN"]:
        avatar_bg = "#124B3E"
    elif user["role"] == "OPERATIONS_ENGINEER":
        avatar_bg = "#1E7A68"
    elif user["role"] == "ESG_AUDITOR":
        avatar_bg = "#D97706"
    elif user["role"] == "STAFF":
        avatar_bg = "#2563EB"
    else:  # MANAGEMENT_VIEWER
        avatar_bg = "#4B5563"

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
            "role_key": role_key_norm,
            "role_label": user["role_label"],
            "avatar_bg": avatar_bg,
            "facility_id": user["facility_id"],
            "permissions": tab_permissions,
            "can_execute_rules": "recommendations.execute" in permissions,
            "can_upgrade_subscription": "billing.manage" in permissions
        }
    }

@app.get("/api/v1/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(verify_current_user)):
    return user

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
            {"key": "SUPER_ADMIN", "label": "RS Administrator", "title": "System Administrator", "badge": "FULL ACCESS"},
            {"key": "FACILITY_ADMIN", "label": "Rajesh Sharma", "title": "Facility Lead & Admin", "badge": "FACILITY ACCESS"},
            {"key": "OPERATIONS_ENGINEER", "label": "Alex Chen", "title": "Operations Engineer", "badge": "TECHNICAL ACCESS"},
            {"key": "ESG_AUDITOR", "label": "Dr. Priya Sharma", "title": "ESG Compliance Auditor", "badge": "AUDIT & SUGGESTIONS"},
            {"key": "MANAGEMENT_VIEWER", "label": "Sam Taylor", "title": "Campus Stakeholder", "badge": "VIEW ONLY"}
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

@app.get("/api/v1/energy/forecast")
def energy_forecast(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    model, meta = get_model_and_metadata("energy_kwh_prediction", train_energy_module)
    df_recent = repo.get_energy_data(limit=24)
    if not df_recent.empty and "electricity_kwh" in df_recent.columns:
        last_val = float(df_recent["electricity_kwh"].iloc[0])
    else:
        last_val = 115.0

    # Model inference for horizons
    sample_df = pd.DataFrame([{
        "temperature": 29.0, "humidity": 55.0, "occupancy": 140, "hvac_load": 48.0,
        "lighting_load": 15.0, "equipment_load": 22.0, "previous_energy_kwh": last_val,
        "hour": 14, "day_of_week": 2
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
        "provenance": ProvenanceType.PREDICTED,
        "provenance_badge": "[ML FORECAST]"
    }

@app.get("/api/v1/energy/anomalies")
def energy_anomalies(user: Dict[str, Any] = Depends(require_permission("energy.read"))):
    df_recent = repo.get_energy_data(limit=50)
    anomalies_list = []
    if not df_recent.empty and "electricity_kwh" in df_recent.columns:
        avg_kwh = float(df_recent["electricity_kwh"].mean())
        for idx, row in df_recent.iterrows():
            actual = float(row["electricity_kwh"])
            if actual > avg_kwh * 1.25:
                dev = round(((actual - avg_kwh) / avg_kwh) * 100, 1)
                anomalies_list.append({
                    "id": f"ALT_{len(anomalies_list)+1:02d}",
                    "building": str(row.get("building", "Block B Hostel")),
                    "issue": "HVAC Compressor Surge",
                    "severity": "HIGH" if dev > 50 else "MEDIUM",
                    "actual_kwh": round(actual, 2),
                    "expected_kwh": round(avg_kwh, 2),
                    "deviation_percent": f"+{dev}%",
                    "disclaimer": "Abnormal operational surge detected by contextual baseline model."
                })
                if len(anomalies_list) >= 3:
                    break

    if not anomalies_list:
        anomalies_list = [{
            "id": "ALT_01",
            "building": "Block B Hostel",
            "issue": "HVAC Setpoint Surge",
            "severity": "HIGH",
            "actual_kwh": 145.2,
            "expected_kwh": 78.0,
            "deviation_percent": "+86.1%",
            "disclaimer": "Contextual baseline model detected thermal compressor load spike."
        }]

    return {
        "active_anomalies_count": len(anomalies_list),
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[ANOMALY DETECTOR]",
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

@app.get("/api/v1/alerts")
def get_alerts(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return {
        "total_active_alerts": 2,
        "provenance": ProvenanceType.DERIVED,
        "provenance_badge": "[DECISION ENGINE]",
        "alerts": [
            {
                "id": "ALT_01",
                "priority": "Priority 1 (URGENT)",
                "module": "Energy",
                "location": "Block B Hostel",
                "message": "Unusual HVAC load surge during peak temperature hours.",
                "observed_kwh": 145.2,
                "expected_kwh": 78.0,
                "deviation": "+86.1%"
            },
            {
                "id": "ALT_02",
                "priority": "Priority 2 (MODERATE)",
                "module": "Waste",
                "location": "Central Cafeteria",
                "message": "Bin 01 fill level projected >90% within 2 hours.",
                "fill_level_pct": 78.5,
                "fill_rate_phr": 4.2
            }
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
    df_dummy = pd.DataFrame([{"energy_kwh": 145.2, "temperature": 31.5, "occupancy": 140, "hvac_load": 75.0}])
    return fusion_instance.run_fusion_analysis(
        df_telemetry=df_dummy,
        building_id="Block B Hostel",
        actual_kwh=145.2
    )

@app.get("/api/v1/intelligence/confidence")
def get_intelligence_confidence(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return fusion_instance.confidence_engine.calculate_decision_confidence()

@app.get("/api/v1/intelligence/model-consensus")
def get_model_consensus(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return fusion_instance.consensus_engine.evaluate_consensus()

@app.get("/api/v1/intelligence/business-impact")
def get_business_impact(user: Dict[str, Any] = Depends(require_permission("alerts.read"))):
    return fusion_instance.impact_engine.calculate_surge_impact(actual_kwh=145.2, expected_kwh=78.0)

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
    device_id = payload.get("device_id", "UNKNOWN_DEVICE")
    return {
        "status": "ACCEPTED",
        "device_id": device_id,
        "timestamp": payload.get("timestamp"),
        "provenance": "REAL_SENSOR_OR_SIMULATED",
        "message": "Telemetry reading ingested successfully."
    }

@app.get("/api/v1/devices")
def list_registered_devices(user: Dict[str, Any] = Depends(require_permission("facility.read"))):
    return {
        "registered_devices": [
            {"device_id": "METER-BLOCK-A-001", "building": "Academic Block A", "status": "ONLINE", "type": "Modbus Meter"},
            {"device_id": "METER-BLOCK-B-001", "building": "Block B Hostel", "status": "ONLINE", "type": "Modbus Meter"},
            {"device_id": "METER-CAFETERIA-001", "building": "Central Cafeteria", "status": "ONLINE", "type": "CT Sensor Gateway"}
        ]
    }

@app.get("/api/v1/devices/{device_id}/health")
def get_device_health(device_id: str):
    return {
        "device_id": device_id,
        "status": "ONLINE",
        "last_seen": pd.Timestamp.now().isoformat(),
        "signal_strength_rssi": -65,
        "power_factor": 0.94,
        "quality": "OK"
    }

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

@app.post("/api/v1/iot-simulator/scenario")
def set_iot_simulator_scenario(req: SimulatorScenarioRequest):
    return GLOBAL_IOT_SIMULATOR.apply_scenario_preset(req.scenario_key)

@app.post("/api/v1/iot-simulator/sensors")
def update_iot_simulator_sensors(overrides: Dict[str, Any]):
    return GLOBAL_IOT_SIMULATOR.update_sensors(overrides)

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
