"""
Integration Test Suite for EstateIQ Real-Time IoT-to-AI Intelligence Integration (tests/test_realtime_iot_integration.py).
Validates end-to-end data pipeline from simulator preset change to telemetry ingestion,
persistence, forecasting, anomaly detection, DIF fusion, and alert hysteresis.
"""

import time
import pytest
import datetime
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
from src.services.iot_simulator import GLOBAL_IOT_SIMULATOR

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_test_state():
    """Resets simulator and device registry state before each test."""
    GLOBAL_IOT_SIMULATOR.reset_state()
    GLOBAL_IOT_SIMULATOR.reset_controls()
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    yield

def test_01_preset_change_generates_different_telemetry():
    """Verify selecting a preset actually changes simulator telemetry output."""
    # 1. Normal Preset
    res_normal = GLOBAL_IOT_SIMULATOR.apply_scenario_preset("Normal Campus Operation")
    s_normal = res_normal["sensors"]
    
    # 2. Thermal Surge / High HVAC Preset
    res_surge = GLOBAL_IOT_SIMULATOR.apply_scenario_preset("High HVAC Consumption")
    s_surge = res_surge["sensors"]
    
    # Assert load & energy changed
    assert s_surge["hvac_load_kw"] > s_normal["hvac_load_kw"], "HVAC load must increase during High HVAC Consumption preset"
    assert s_surge["active_power_kw"] > s_normal["active_power_kw"], "Active power must increase during surge"

def test_02_authenticated_telemetry_ingestion_and_persistence():
    """Verify valid telemetry is ingested, tagged as simulated_iot, and stored in registry history."""
    payload = {
        "instance_id": "SIM_TEST_AUTH_01",
        "device_id": "DEV_TEST_METER_01",
        "building_id": "Block B Hostel",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"metric": "energy_kwh", "value": 158.4},
            {"metric": "active_power_kw", "value": 142.0},
            {"metric": "temperature_c", "value": 34.5},
            {"metric": "occupancy_count", "value": 180}
        ]
    }
    
    res = client.post("/api/v1/iot/telemetry", json=payload)
    assert res.status_code == 200, f"Ingestion failed with status {res.status_code}: {res.text}"
    data = res.json()
    assert data["accepted"] is True
    
    # Verify persistence in history
    assert len(GLOBAL_DEVICE_REGISTRY.telemetry_history) > 0
    latest = GLOBAL_DEVICE_REGISTRY.telemetry_history[0]
    assert latest["device_id"] == "DEV_TEST_METER_01"
    assert latest["source_type"] == "simulated_iot"
    assert latest["data_source_badge"] == "[SIMULATED IoT]"
    assert latest["metrics"]["energy_kwh"] == 158.4

def test_03_dashboard_values_match_persisted_telemetry():
    """Verify /api/v1/energy/forecast uses latest ingested telemetry."""
    # Ingest telemetry with specific high energy value
    payload = {
        "instance_id": "SIM_MATCH_01",
        "device_id": "DEV_MATCH_01",
        "building_id": "Block B Hostel",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"metric": "energy_kwh", "value": 175.5},
            {"metric": "temperature_c", "value": 35.0},
            {"metric": "occupancy_count", "value": 200},
            {"metric": "hvac_load_kw", "value": 75.0}
        ]
    }
    client.post("/api/v1/iot/telemetry", json=payload)
    
    # Fetch forecast
    res = client.get("/api/v1/energy/forecast")
    assert res.status_code == 200
    forecast_data = res.json()
    assert forecast_data["source_device_id"] == "DEV_MATCH_01"
    assert "generation_timestamp" in forecast_data
    assert forecast_data["predicted_1h_kwh"] > 0

def test_04_controlled_load_spike_triggers_anomaly_alert():
    """Verify load spike telemetry triggers an anomaly alert with correct structure."""
    payload = {
        "instance_id": "SIM_SPIKE_01",
        "device_id": "DEV_SPIKE_01",
        "building_id": "Block B Hostel",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"metric": "energy_kwh", "value": 185.0},
            {"metric": "temperature_c", "value": 36.0},
            {"metric": "occupancy_count", "value": 210},
            {"metric": "hvac_load_kw", "value": 85.0},
            {"metric": "voltage_v", "value": 230.0}
        ]
    }
    client.post("/api/v1/iot/telemetry", json=payload)
    
    # Query anomalies endpoint
    res = client.get("/api/v1/energy/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert data["active_anomalies_count"] >= 1
    
    # Verify alert details
    anom = data["anomalies"][0]
    assert anom["device_id"] == "DEV_SPIKE_01"
    assert anom["severity"] in ["HIGH", "CRITICAL"]
    assert "observed_value" in anom
    assert "expected_range" in anom
    assert "recommended_action" in anom

def test_05_normal_operation_and_recovery():
    """Verify normal operation yields normal status without active anomaly alerts."""
    payload = {
        "instance_id": "SIM_NORM_01",
        "device_id": "DEV_NORM_01",
        "building_id": "Block B Hostel",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"metric": "energy_kwh", "value": 50.0},
            {"metric": "temperature_c", "value": 26.0},
            {"metric": "occupancy_count", "value": 100},
            {"metric": "hvac_load_kw", "value": 25.0},
            {"metric": "voltage_v", "value": 230.0},
            {"metric": "water_flow_lmin", "value": 10.0}
        ]
    }
    client.post("/api/v1/iot/telemetry", json=payload)
    
    res = client.get("/api/v1/energy/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert data["active_anomalies_count"] == 0
    assert data["anomalies"][0]["severity"] == "NORMAL"

def test_06_unauthorized_revoked_simulator_rejection():
    """Verify revoked simulator instances are rejected during telemetry ingestion."""
    # Register and revoke simulator
    GLOBAL_DEVICE_REGISTRY.register_simulator("SIM_REVOKED_01", "Revoked-Sim", "IQ-DEMO")
    GLOBAL_DEVICE_REGISTRY.revoke_simulator("SIM_REVOKED_01")
    
    payload = {
        "instance_id": "SIM_REVOKED_01",
        "device_id": "DEV_REV_01",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [{"metric": "energy_kwh", "value": 120.0}]
    }
    
    res = client.post("/api/v1/iot/telemetry", json=payload)
    assert res.status_code == 400
    assert "REVOKED" in res.json()["detail"]

def test_07_intelligence_fusion_overview():
    """Verify /api/v1/intelligence/overview runs DIF analysis using live telemetry."""
    res = client.get("/api/v1/intelligence/overview")
    assert res.status_code == 200
    data = res.json()
    assert "overall_decision_score" in data or "decision_score" in data or "trace_id" in data
