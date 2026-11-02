"""
EstateIQ Canonical Telemetry Test Suite (tests/test_canonical_telemetry.py)

Covers:
1. Canonical schema validation and normalization
2. Real vs simulated provenance preservation across pipeline
3. HTTP and MQTT ingestion consistency
4. Duplicate message idempotency
5. Counter reset and rollback detection
6. Invalid and non-finite value rejection
7. Device health state transitions (ONLINE -> STALE -> OFFLINE)
8. Batch ingestion behavior
9. Route consolidation regression tests
"""

import os
import sys
import time
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from src.data.telemetry_schema import (
    normalize_telemetry_payload,
    TelemetryEnvelope,
    SourceType,
    MetricQuality
)
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
from src.data_quality.quality_score import DataQualityEngine

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry state before each test."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    yield

def test_01_canonical_schema_validation_and_normalization():
    """Verify legacy and alternate field names normalize to canonical metrics and units."""
    legacy_payload = {
        "device_id": "METER_TEST_NORM",
        "building_id": "Block B Hostel",
        "timestamp": datetime.datetime.now().isoformat(),
        "measurements": {
            "power_kw": 18.5,
            "cumulative_kwh": 4120.5,
            "water_flow_lpm": 22.4,
            "voltage_v": 231.0,
            "current_a": 80.2,
            "power_factor": 0.95,
            "frequency_hz": 50.0
        }
    }
    envelope, flat_map, warnings = normalize_telemetry_payload(legacy_payload, default_source=SourceType.REAL_SENSOR)
    assert envelope.device_id == "METER_TEST_NORM"
    assert envelope.source_type == SourceType.REAL_SENSOR

    names = {m.name: m for m in envelope.metrics}
    assert "active_power_kw" in names
    assert names["active_power_kw"].value == 18.5
    assert names["active_power_kw"].unit == "kW"

    assert "cumulative_energy_kwh" in names
    assert names["cumulative_energy_kwh"].value == 4120.5
    assert names["cumulative_energy_kwh"].unit == "kWh"

    assert "water_flow_lmin" in names
    assert names["water_flow_lmin"].value == 22.4
    assert names["water_flow_lmin"].unit == "L/min"

def test_02_real_vs_simulated_provenance_preservation():
    """Verify that physical device provenance requires a registered gateway credential."""
    now_iso = datetime.datetime.now().isoformat()
    # Provision a trusted physical gateway
    GLOBAL_DEVICE_REGISTRY.register_gateway("GW_PROV_01", "Physical Gateway 01", "gw_secret_token_123")

    # 1. Real sensor telemetry with valid registered gateway credential -> [REAL SENSOR]
    real_payload_auth = {
        "message_id": "MSG_REAL_AUTH_001",
        "gateway_id": "GW_PROV_01",
        "auth_token": "gw_secret_token_123",
        "device_id": "PHYS_METER_01",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [
            {"name": "active_power_kw", "value": 45.2, "unit": "kW"},
            {"name": "cumulative_energy_kwh", "value": 5200.0, "unit": "kWh"}
        ]
    }
    res_real = client.post("/api/v1/iot/telemetry", json=real_payload_auth)
    assert res_real.status_code == 200
    assert res_real.json()["source_type"] == "real_sensor"
    assert res_real.json()["data_source_badge"] == "[REAL SENSOR]"
    assert res_real.json()["is_verified_hardware"] is True

    # 2. Fabricated meter-like ID claiming real_sensor with MISSING token
    # In default demo mode: accepted as unverified demo mode
    unauth_payload = {
        "message_id": "MSG_UNAUTH_001",
        "device_id": "METER_FABRICATED_01",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"name": "active_power_kw", "value": 15.0, "unit": "kW"}]
    }
    res_unauth = client.post("/api/v1/iot/telemetry", json=unauth_payload)
    assert res_unauth.status_code == 200
    assert res_unauth.json()["data_source_badge"] == "[UNVERIFIED SENSOR - DEMO MODE]"
    assert res_unauth.json()["is_verified_hardware"] is False

    # When unverified demo mode is disabled: missing token must be REJECTED
    GLOBAL_DEVICE_REGISTRY.allow_unverified_demo_mode = False
    unauth_payload["message_id"] = "MSG_UNAUTH_002"
    res_rejected = client.post("/api/v1/iot/telemetry", json=unauth_payload)
    assert res_rejected.status_code == 400
    assert "MISSING_GATEWAY_CREDENTIAL" in res_rejected.json()["detail"]
    GLOBAL_DEVICE_REGISTRY.allow_unverified_demo_mode = True  # Restore

    # 3. Telemetry with WRONG token -> REJECTED
    wrong_payload = {
        "message_id": "MSG_WRONG_001",
        "gateway_id": "GW_PROV_01",
        "auth_token": "wrong_password_999",
        "device_id": "PHYS_METER_01",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"name": "active_power_kw", "value": 45.2, "unit": "kW"}]
    }
    res_wrong = client.post("/api/v1/iot/telemetry", json=wrong_payload)
    assert res_wrong.status_code == 400
    assert "INVALID_GATEWAY_CREDENTIAL" in res_wrong.json()["detail"]

    # 4. Telemetry with REVOKED gateway -> REJECTED
    GLOBAL_DEVICE_REGISTRY.revoke_gateway("GW_PROV_01")
    real_payload_auth["message_id"] = "MSG_REAL_REVOKED_001"
    res_revoked = client.post("/api/v1/iot/telemetry", json=real_payload_auth)
    assert res_revoked.status_code == 400
    assert "REVOKED_GATEWAY_CREDENTIAL" in res_revoked.json()["detail"]

    # 5. Simulated IoT telemetry
    sim_payload = {
        "message_id": "MSG_SIM_001",
        "device_id": "DEV_SIM_METER_01",
        "source_type": "simulated_iot",
        "event_timestamp": now_iso,
        "metrics": [{"name": "active_power_kw", "value": 25.0, "unit": "kW"}]
    }
    res_sim = client.post("/api/v1/iot/telemetry", json=sim_payload)
    assert res_sim.status_code == 200
    assert res_sim.json()["source_type"] == "simulated_iot"
    assert res_sim.json()["data_source_badge"] == "[SIMULATED IoT]"
    assert res_sim.json()["is_verified_hardware"] is False

def test_03_http_and_mqtt_ingestion_parity():
    """Verify that HTTP and direct MQTT router calls invoke identical validation and storage."""
    GLOBAL_DEVICE_REGISTRY.register_gateway("GW_PARITY_01", "Parity Gateway", "key_parity_999")
    payload = {
        "message_id": "MSG_PARITY_001",
        "gateway_id": "GW_PARITY_01",
        "auth_token": "key_parity_999",
        "device_id": "PHYS_PARITY_01",
        "source_type": "real_sensor",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"name": "active_power_kw", "value": 33.5, "unit": "kW"},
            {"name": "cumulative_energy_kwh", "value": 8100.0, "unit": "kWh"}
        ]
    }
    # Direct registry ingestion (used by mqtt_consumer)
    mqtt_res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    assert mqtt_res["success"] is True
    assert mqtt_res["source_type"] == "real_sensor"
    assert mqtt_res["data_source_badge"] == "[REAL SENSOR]"
    assert mqtt_res["is_verified_hardware"] is True

    # HTTP ingestion
    payload_http = dict(payload)
    payload_http["message_id"] = "MSG_PARITY_002"
    payload_http["device_id"] = "PHYS_PARITY_02"
    http_res = client.post("/api/v1/iot/telemetry", json=payload_http)
    assert http_res.status_code == 200
    assert http_res.json()["source_type"] == "real_sensor"
    assert http_res.json()["data_source_badge"] == "[REAL SENSOR]"
    assert http_res.json()["is_verified_hardware"] is True

def test_04_idempotent_duplicate_message_handling():
    """Verify identical message_ids are acknowledged idempotently without duplication."""
    payload = {
        "message_id": "MSG_DUP_1001",
        "device_id": "METER_DUP_01",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [{"name": "active_power_kw", "value": 12.0, "unit": "kW"}]
    }
    # First submission -> ACCEPTED
    res1 = client.post("/api/v1/iot/telemetry", json=payload)
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACCEPTED"
    history_len = len(GLOBAL_DEVICE_REGISTRY.telemetry_history)
    assert history_len == 1

    # Second submission -> DUPLICATE_IGNORED (No-op acknowledgment)
    res2 = client.post("/api/v1/iot/telemetry", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "DUPLICATE_IGNORED"
    assert len(GLOBAL_DEVICE_REGISTRY.telemetry_history) == history_len

def test_05_counter_reset_and_monotonic_detection():
    """Verify cumulative counter deltas derive interval energy only on consecutive chronological readings."""
    t0 = datetime.datetime.now()
    # Reading 1: 5000 kWh -> First totalizer sample: interval energy must NOT be derived
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_CNT_01",
        "device_id": "METER_ROLLOVER_01",
        "event_timestamp": t0.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 5000.0, "unit": "kWh"}]
    })
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER_ROLLOVER_01"]
    assert "interval_energy_kwh" not in dev.last_telemetry

    # Reading 2: 5003.5 kWh (+3.5 kWh, 60s later) -> Derived interval energy == 3.5 kWh
    t1 = t0 + datetime.timedelta(seconds=60)
    res2 = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_CNT_02",
        "device_id": "METER_ROLLOVER_01",
        "event_timestamp": t1.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 5003.5, "unit": "kWh"}]
    })
    assert res2.status_code == 200
    assert dev.last_telemetry["interval_energy_kwh"] == 3.5

    # Reading 3: Non-chronological sample (t0 again) -> Interval derivation skipped
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_CNT_03",
        "device_id": "METER_ROLLOVER_01",
        "event_timestamp": t0.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 5005.0, "unit": "kWh"}]
    })
    # Interval was not updated because timestamp is not newer
    assert dev.last_telemetry["interval_energy_kwh"] == 3.5

    # Reading 4: 12.0 kWh (Rollover or meter swap)
    t2 = t1 + datetime.timedelta(seconds=60)
    res4 = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_CNT_04",
        "device_id": "METER_ROLLOVER_01",
        "event_timestamp": t2.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 12.0, "unit": "kWh"}]
    })
    assert res4.status_code == 200
    warnings = res4.json().get("warnings", [])
    assert any("rollback" in w.lower() or "reset" in w.lower() for w in warnings)
    assert dev.counter_reset_detected is True

def test_05b_out_of_order_preserves_baseline_and_recovers():
    """Verify out-of-order reading does not corrupt counter baseline or subsequent interval derivations."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()

    t0 = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=180)
    # 1. First valid sample at t0: 1000.0 kWh (establishes baseline, no interval)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_OOO_01",
        "device_id": "METER_OOO_01",
        "event_timestamp": t0.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 1000.0, "unit": "kWh"}]
    })
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER_OOO_01"]
    assert dev.last_counter_energy_kwh == 1000.0
    assert "interval_energy_kwh" not in dev.last_telemetry

    # 2. Second valid sample at t1 = t0 + 60s: 1004.2 kWh (delta = 4.2 kWh)
    t1 = t0 + datetime.timedelta(seconds=60)
    res2 = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_OOO_02",
        "device_id": "METER_OOO_01",
        "event_timestamp": t1.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 1004.2, "unit": "kWh"}]
    })
    assert res2.status_code == 200
    assert dev.last_counter_energy_kwh == 1004.2
    assert dev.last_telemetry["interval_energy_kwh"] == 4.2
    assert dev.counter_reset_detected is False

    # 3. Out-of-order delayed sample at t_delayed = t0 + 30s: 1002.0 kWh
    # Must NOT advance dev.last_sample_at, must NOT update last_counter_energy_kwh,
    # must NOT flag as counter reset, and must NOT produce interval delta.
    t_delayed = t0 + datetime.timedelta(seconds=30)
    res_delayed = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_OOO_03",
        "device_id": "METER_OOO_01",
        "event_timestamp": t_delayed.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 1002.0, "unit": "kWh"}]
    })
    assert res_delayed.status_code == 200
    assert any("out-of-order" in w.lower() or "non-chronological" in w.lower() for w in res_delayed.json().get("warnings", []))
    # Baseline remains 1004.2 (from t1), last_sample_at remains t1, and counter_reset_detected is False
    assert dev.last_counter_energy_kwh == 1004.2
    assert dev.last_sample_at == t1.isoformat().replace("+00:00", "Z")
    assert dev.counter_reset_detected is False

    # 4. Third valid sample at t2 = t1 + 60s: 1007.0 kWh
    # Must derive interval from valid baseline 1004.2 -> delta = 2.8 kWh (NOT from 1002.0)!
    t2 = t1 + datetime.timedelta(seconds=60)
    res4 = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_OOO_04",
        "device_id": "METER_OOO_01",
        "event_timestamp": t2.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 1007.0, "unit": "kWh"}]
    })
    assert res4.status_code == 200
    assert dev.last_telemetry["interval_energy_kwh"] == 2.8
    assert dev.last_counter_energy_kwh == 1007.0
    assert dev.last_sample_at == t2.isoformat().replace("+00:00", "Z")

def test_06_invalid_values_and_quality_rejection():
    """Verify non-finite and impossible physical values are rejected or flagged."""
    # 1. Negative active power
    payload_neg = {
        "message_id": "MSG_INV_01",
        "device_id": "METER_INV_01",
        "metrics": [{"name": "active_power_kw", "value": -50.0, "unit": "kW"}]
    }
    res_neg = client.post("/api/v1/iot/telemetry", json=payload_neg)
    assert res_neg.status_code == 400

    # 2. Out-of-bounds voltage (> 1000 V physical limit)
    payload_volt = {
        "message_id": "MSG_INV_02",
        "device_id": "METER_INV_02",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [{"name": "voltage_v", "value": 1500.0, "unit": "V"}]
    }
    res_volt = client.post("/api/v1/iot/telemetry", json=payload_volt)
    assert res_volt.status_code == 400
    assert "outside plausible physical range" in res_volt.json()["detail"]

def test_07_device_health_state_transitions():
    """Verify device health transitions from ONLINE to STALE and OFFLINE."""
    now = datetime.datetime.now()
    # 1. Fresh reading -> ONLINE
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_HLT_01",
        "device_id": "METER_HEALTH_01",
        "event_timestamp": now.isoformat(),
        "metrics": [{"name": "active_power_kw", "value": 20.0, "unit": "kW"}]
    })
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER_HEALTH_01"]
    assert dev.status == "ONLINE"

    # 2. Simulate 4 minutes elapsed -> STALE
    dev.last_sample_at = (now - datetime.timedelta(minutes=4)).isoformat()
    GLOBAL_DEVICE_REGISTRY._update_stale_statuses()
    assert dev.status == "STALE"

    # 3. Simulate 16 minutes elapsed -> OFFLINE
    dev.last_sample_at = (now - datetime.timedelta(minutes=16)).isoformat()
    GLOBAL_DEVICE_REGISTRY._update_stale_statuses()
    assert dev.status == "OFFLINE"

def test_08_batch_telemetry_ingestion():
    """Verify batch ingestion handles multiple telemetry envelopes accurately."""
    batch = [
        {
            "message_id": f"MSG_BATCH_{i}",
            "device_id": f"DEV_BATCH_{i}",
            "source_type": "real_sensor",
            "event_timestamp": datetime.datetime.now().isoformat(),
            "metrics": [{"name": "active_power_kw", "value": 10.0 + i, "unit": "kW"}]
        }
        for i in range(5)
    ]
    res = client.post("/api/v1/iot/telemetry/batch", json=batch)
    assert res.status_code == 200
    data = res.json()
    assert data["batch_size"] == 5
    assert data["accepted_count"] == 5
    assert data["rejected_count"] == 0

def test_09_duplicate_route_removal_and_endpoint_consolidation():
    """Verify consolidated endpoints operate without 404 or route collisions."""
    # Devices list
    res_devs = client.get("/api/v1/iot/devices")
    assert res_devs.status_code == 200
    assert "devices" in res_devs.json()

    # Simulator status
    res_status = client.get("/api/v1/iot-simulator/status")
    assert res_status.status_code == 200
    assert "status" in res_status.json()

    # Ingestion route
    res_ingest = client.post("/api/v1/ingestion/telemetry", json={
        "device_id": "DEV_INGEST_01",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [{"name": "active_power_kw", "value": 55.0, "unit": "kW"}]
    })
    assert res_ingest.status_code == 200
    assert res_ingest.json()["source_type"] == "real_sensor"

def test_10_absent_metrics_unit_separation_and_live_status():
    """Verify live telemetry does not confuse kW with kWh and returns None for unavailable fields."""
    from api.main import get_latest_live_telemetry

    GLOBAL_DEVICE_REGISTRY.register_gateway("GW_MET_10", "Metrology Gateway", "key_met_10")
    payload = {
        "message_id": "MSG_MET_10",
        "gateway_id": "GW_MET_10",
        "auth_token": "key_met_10",
        "device_id": "PHYS_METER_10",
        "source_type": "real_sensor",
        "event_timestamp": datetime.datetime.now().isoformat(),
        "metrics": [
            {"name": "active_power_kw", "value": 42.5, "unit": "kW"},
            {"name": "voltage_v", "value": 230.2, "unit": "V"}
        ]
    }
    res = client.post("/api/v1/iot/telemetry", json=payload)
    assert res.status_code == 200

    live = get_latest_live_telemetry()
    assert live["active_power_kw"] == 42.5
    # Strict unit separation: active power (kW) must NEVER be returned as interval energy (kWh)!
    assert live["energy_kwh"] is None
    # No fake contextual defaults in physical telemetry
    assert live["temperature"] is None
    assert live["occupancy"] is None
    assert live["hvac_load"] is None
    assert live["metric_status"]["energy_kwh"] == "UNAVAILABLE"
    assert live["metric_status"]["temperature"] == "UNAVAILABLE"
    assert live["metric_status"]["active_power_kw"] == "MEASURED"
    assert live["metric_status"]["voltage_v"] == "MEASURED"

def test_11_water_leak_sustained_flow_logic():
    """Verify water leakage detection requires sustained flow across consecutive samples for the same meter."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Step 1: Single transient spike (18.0 L/min)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_WTR_01",
        "device_id": "WATER_METER_LAB_01",
        "source_type": "real_sensor",
        "event_timestamp": (now - datetime.timedelta(seconds=120)).isoformat(),
        "metrics": [{"name": "water_flow_lmin", "value": 18.0, "unit": "L/min"}]
    })

    # Single spike must NOT trigger sustained leak alert
    res_anom1 = client.get("/api/v1/energy/anomalies")
    assert res_anom1.status_code == 200
    anoms1 = [a for a in res_anom1.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(anoms1) == 0, "Single transient spike must not trigger sustained water leak alert"

    # Step 2: Two more consecutive high flow samples (total 3 samples in sequence)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_WTR_02",
        "device_id": "WATER_METER_LAB_01",
        "source_type": "real_sensor",
        "event_timestamp": (now - datetime.timedelta(seconds=60)).isoformat(),
        "metrics": [{"name": "water_flow_lmin", "value": 19.5, "unit": "L/min"}]
    })
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_WTR_03",
        "device_id": "WATER_METER_LAB_01",
        "source_type": "real_sensor",
        "event_timestamp": now.isoformat(),
        "metrics": [{"name": "water_flow_lmin", "value": 18.2, "unit": "L/min"}]
    })

    # Sustained flow alert must now trigger
    res_anom2 = client.get("/api/v1/energy/anomalies")
    assert res_anom2.status_code == 200
    anoms2 = [a for a in res_anom2.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(anoms2) == 1
    # Because occupancy is estimated/unverified, alert must be labeled "Suspected" not "Confirmed"
    assert "Suspected" in anoms2[0]["issue"]
    assert anoms2[0]["severity"] == "HIGH"

    # Step 3: Stale samples (15 minutes old) must NOT trigger active leak alert
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    stale_ts = (now - datetime.timedelta(minutes=15)).isoformat()
    for i in range(3):
        client.post("/api/v1/iot/telemetry", json={
            "message_id": f"MSG_WTR_STALE_{i}",
            "device_id": "WATER_METER_LAB_01",
            "source_type": "real_sensor",
            "event_timestamp": stale_ts,
            "metrics": [{"name": "water_flow_lmin", "value": 20.0, "unit": "L/min"}]
        })
    res_anom_stale = client.get("/api/v1/energy/anomalies")
    anoms_stale = [a for a in res_anom_stale.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(anoms_stale) == 0, "Stale flow samples (> 10 minutes) must not trigger active water leak alert"

    # Step 4: Out-of-bounds reading (> 30.0 L/min for YF-S201 rating) triggers sensor glitch alert
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    now_step4 = datetime.datetime.now(datetime.timezone.utc)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_WTR_GLITCH_01",
        "device_id": "WATER_METER_LAB_01",
        "source_type": "real_sensor",
        "event_timestamp": now_step4.isoformat(),
        "metrics": [{"name": "water_flow_lmin", "value": 32.5, "unit": "L/min"}]
    })
    res_glitch = client.get("/api/v1/energy/anomalies")
    anoms_glitch = [a for a in res_glitch.json()["anomalies"] if a["id"] == "ALT_WATER_SENSOR_FAULT"]
    assert len(anoms_glitch) == 1
    assert "Range Error" in anoms_glitch[0]["issue"]
    assert "> 30.0 L/min" in anoms_glitch[0]["observed_value"]

def test_12_malformed_and_missing_timestamps_quarantined():
    """Verify malformed and missing timestamps are quarantined and cannot advance baselines or live state."""
    from api.main import get_latest_live_telemetry
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()

    # 1. Establish valid initial baseline at t0
    t0 = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=20)
    res_init = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_INIT_01",
        "device_id": "METER_TS_QUAR_01",
        "source_type": "real_sensor",
        "event_timestamp": t0.isoformat(),
        "metrics": [
            {"name": "cumulative_energy_kwh", "value": 1000.0, "unit": "kWh"},
            {"name": "cumulative_water_m3", "value": 50.0, "unit": "m3"}
        ]
    })
    assert res_init.status_code == 200
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER_TS_QUAR_01"]
    assert dev.last_counter_energy_kwh == 1000.0
    assert dev.last_counter_water_m3 == 50.0
    assert dev.last_sample_at == t0.isoformat().replace("+00:00", "Z")
    assert "interval_energy_kwh" not in dev.last_telemetry

    # 2. Ingest payload with malformed timestamp string
    res_malformed = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_MALFORMED_01",
        "device_id": "METER_TS_QUAR_01",
        "source_type": "real_sensor",
        "event_timestamp": "invalid-garbage-date-2026-99-99",
        "metrics": [
            {"name": "cumulative_energy_kwh", "value": 1050.0, "unit": "kWh"},
            {"name": "cumulative_water_m3", "value": 65.0, "unit": "m3"},
            {"name": "water_flow_lmin", "value": 25.0, "unit": "L/min"}
        ]
    })
    # HTTP ingestion must reject with 400
    assert res_malformed.status_code == 400
    assert "MALFORMED_EVENT_TIMESTAMP" in res_malformed.json()["detail"]

    # Verify quarantined sample in registry telemetry_history
    assert len(GLOBAL_DEVICE_REGISTRY.telemetry_history) == 2
    quar_rec = GLOBAL_DEVICE_REGISTRY.telemetry_history[0]
    assert quar_rec["quarantined"] is True
    assert quar_rec["is_valid_sample"] is False
    assert "MALFORMED_EVENT_TIMESTAMP" in quar_rec["timestamp_error"]

    # Critical: counter baselines must NOT have moved, and last_sample_at must NOT change!
    assert dev.last_counter_energy_kwh == 1000.0
    assert dev.last_counter_water_m3 == 50.0
    assert dev.last_sample_at == t0.isoformat().replace("+00:00", "Z")
    assert "interval_energy_kwh" not in dev.last_telemetry
    assert "interval_water_m3" not in dev.last_telemetry

    # 3. Quarantined sample must NOT become latest live telemetry
    live = get_latest_live_telemetry()
    assert live["cumulative_energy_kwh"] == 1000.0
    assert live["cumulative_water_m3"] == 50.0
    assert live["water_flow_lmin"] is None or live["water_flow_lmin"] != 25.0

    # 4. Quarantined sample must NOT trigger resource anomalies
    res_anom = client.get("/api/v1/energy/anomalies")
    assert res_anom.status_code == 200
    leak_anoms = [a for a in res_anom.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(leak_anoms) == 0

    # 5. Missing timestamp on real sensor payload must also be quarantined
    res_missing = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_MISSING_TS_01",
        "device_id": "METER_TS_QUAR_01",
        "source_type": "real_sensor",
        "event_timestamp": None,
        "metrics": [{"name": "cumulative_energy_kwh", "value": 1100.0, "unit": "kWh"}]
    })
    assert res_missing.status_code == 400
    assert "MISSING_EVENT_TIMESTAMP" in res_missing.json()["detail"]
    assert dev.last_counter_energy_kwh == 1000.0
    assert dev.last_sample_at == t0.isoformat().replace("+00:00", "Z")

def test_13_late_duplicate_and_future_timestamps_live_state():
    """Verify delayed, duplicate, and future timestamps preserve live state and device status."""
    from api.main import get_latest_live_telemetry
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()

    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Future timestamp beyond 300s permitted clock drift
    t_future = now + datetime.timedelta(minutes=10)
    res_future = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_FUT_01",
        "device_id": "METER_SKEW_01",
        "source_type": "real_sensor",
        "event_timestamp": t_future.isoformat(),
        "metrics": [{"name": "cumulative_energy_kwh", "value": 500.0, "unit": "kWh"}]
    })
    assert res_future.status_code == 400
    assert "FUTURE_EVENT_TIMESTAMP" in res_future.json()["detail"]

    # 2. Establish baseline at t0 = now - 60s (freshness age = 60s -> STALE)
    t0 = now - datetime.timedelta(seconds=60)
    res_t0 = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_CHRONO_01",
        "device_id": "METER_SKEW_01",
        "source_type": "real_sensor",
        "event_timestamp": t0.isoformat(),
        "metrics": [
            {"name": "active_power_kw", "value": 25.0, "unit": "kW"},
            {"name": "cumulative_energy_kwh", "value": 2000.0, "unit": "kWh"}
        ]
    })
    assert res_t0.status_code == 200
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER_SKEW_01"]
    assert dev.status == "STALE"
    assert dev.last_counter_energy_kwh == 2000.0
    assert dev.last_sample_at == t0.isoformat().replace("+00:00", "Z")

    # Verify live telemetry reflects t0
    live_t0 = get_latest_live_telemetry()
    assert live_t0["cumulative_energy_kwh"] == 2000.0
    assert live_t0["active_power_kw"] == 25.0
    assert live_t0["device_status"] == "STALE"

    # 3. Ingest late/out-of-order sample at t_late = now - 120s (older than t0)
    t_late = now - datetime.timedelta(seconds=120)
    res_late = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_LATE_01",
        "device_id": "METER_SKEW_01",
        "source_type": "real_sensor",
        "event_timestamp": t_late.isoformat(),
        "metrics": [
            {"name": "active_power_kw", "value": 99.0, "unit": "kW"},
            {"name": "cumulative_energy_kwh", "value": 1990.0, "unit": "kWh"}
        ]
    })
    # Late sample is accepted for audit
    assert res_late.status_code == 200
    assert res_late.json()["is_late_sample"] is True
    assert res_late.json()["status"] == "ACCEPTED_LATE_SAMPLE_AUDIT_ONLY"

    # Critical assertions:
    # A. dev.last_sample_at remains t0
    assert dev.last_sample_at == t0.isoformat().replace("+00:00", "Z")
    # B. baseline counter remains 2000.0 (NOT regressed to 1990.0)
    assert dev.last_counter_energy_kwh == 2000.0
    # C. dev.status must NOT be restored to ONLINE! It remains STALE
    assert dev.status == "STALE"
    # D. dev.last_telemetry must NOT be overwritten with late sample metrics (active_power_kw remains 25.0, not 99.0)
    assert dev.last_telemetry["active_power_kw"] == 25.0
    # E. get_latest_live_telemetry must NOT return the late sample
    live_after_late = get_latest_live_telemetry()
    assert live_after_late["active_power_kw"] == 25.0
    assert live_after_late["cumulative_energy_kwh"] == 2000.0
    assert live_after_late["device_status"] == "STALE"

    # 4. Duplicate timestamp: exact same event_timestamp as t0
    res_dup_ts = client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_DUP_TS_01",
        "device_id": "METER_SKEW_01",
        "source_type": "real_sensor",
        "event_timestamp": t0.isoformat(),
        "metrics": [
            {"name": "active_power_kw", "value": 30.0, "unit": "kW"},
            {"name": "cumulative_energy_kwh", "value": 2005.0, "unit": "kWh"}
        ]
    })
    assert res_dup_ts.status_code == 200
    assert res_dup_ts.json()["is_late_sample"] is True
    assert dev.last_counter_energy_kwh == 2000.0
    assert "interval_energy_kwh" not in dev.last_telemetry

    # 5. Stale (> 45s) and Offline (> 300s) states
    t_offline = now - datetime.timedelta(seconds=350)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": "MSG_OFFLINE_01",
        "device_id": "METER_OFFLINE_01",
        "source_type": "real_sensor",
        "event_timestamp": t_offline.isoformat(),
        "metrics": [{"name": "active_power_kw", "value": 10.0, "unit": "kW"}]
    })
    dev_offline = GLOBAL_DEVICE_REGISTRY.devices["METER_OFFLINE_01"]
    assert dev_offline.status == "OFFLINE"


def test_14_cross_building_and_unverified_occupancy_leak_alert_isolation():
    """Verify that water leak alerts require verified, fresh same-building occupancy to be confirmed.

    Tests:
    1. Cross-building occupancy: Water meter in Block A + Verified low occupancy in Block B -> Alert is Suspected, assigned to Block A, explains occupancy context is unavailable.
    2. Stale occupancy: Water meter in Block A + Stale occupancy in Block A (>600s) -> Alert is Suspected.
    3. Unverified occupancy: Water meter in Block A + Simulated/unverified occupancy in Block A -> Alert is Suspected.
    4. Verified same-building case: Water meter in Block A + Fresh, verified occupancy in Block A (<15) -> Alert is Confirmed Off-Hours Water Leak (CRITICAL).
    """
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.gateways.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()

    # Provision trusted gateway
    GLOBAL_DEVICE_REGISTRY.register_gateway("GW_PROV_BLDG", "Gateway Bldg", "gw_key_bldg_auth")

    # Helper to send sustained water leak samples (3 consecutive chronological samples at 18.0+ L/min)
    def _send_water_leak_samples(building_id="Block A Science", is_auth=True, auth_token="gw_key_bldg_auth", step="step"):
        t_now = datetime.datetime.now(datetime.timezone.utc)
        for i in range(3):
            # Chronological samples within 15 seconds of now (fresh, online)
            t_sample = t_now - datetime.timedelta(seconds=(10 - i * 3))
            payload = {
                "message_id": f"MSG_WTR_{step}_{building_id.replace(' ', '_')}_{i}_{uuid.uuid4().hex[:8]}",
                "gateway_id": "GW_PROV_BLDG" if is_auth else None,
                "auth_token": auth_token if is_auth else None,
                "device_id": f"WATER_METER_{building_id.replace(' ', '_')}",
                "facility_id": "FAC_GEC_CAMPUS",
                "building_id": building_id,
                "source_type": "real_sensor" if is_auth else "simulated_iot",
                "event_timestamp": t_sample.isoformat(),
                "metrics": [{"name": "water_flow_lmin", "value": 18.0 + i, "unit": "L/min"}]
            }
            res = client.post("/api/v1/iot/telemetry", json=payload)
            assert res.status_code == 200

    # 1. MISMATCHING BUILDING ID (Cross-building occupancy)
    # Block A has sustained water leak. Block B has verified low occupancy (count = 5).
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()

    t_now1 = datetime.datetime.now(datetime.timezone.utc)
    # Ingest verified occupancy in Block B Hostel
    client.post("/api/v1/iot/telemetry", json={
        "message_id": f"MSG_OCC_BLOCK_B_{uuid.uuid4().hex[:8]}",
        "gateway_id": "GW_PROV_BLDG",
        "auth_token": "gw_key_bldg_auth",
        "device_id": "OCC_SENSOR_BLOCK_B",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": (t_now1 - datetime.timedelta(seconds=5)).isoformat(),
        "metrics": [{"name": "occupancy_count", "value": 5, "unit": "count"}]
    })

    # Ingest sustained water leak in Block A Science
    _send_water_leak_samples(building_id="Block A Science", is_auth=True, step="cross")

    res_cross = client.get("/api/v1/energy/anomalies")
    assert res_cross.status_code == 200
    leaks_cross = [a for a in res_cross.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(leaks_cross) == 1
    anom_cross = leaks_cross[0]
    # Alert must be assigned to Block A Science, NOT Block B
    assert anom_cross["building"] == "Block A Science"
    # Alert must NOT be Confirmed; it must be labeled Suspected
    assert "Suspected" in anom_cross["issue"]
    assert anom_cross["severity"] == "HIGH"
    # Explanation must state occupancy context is unavailable or unverified
    assert "Occupancy context is unavailable or unverified" in anom_cross["explanation"]
    assert "cross-building occupancy" in anom_cross["explanation"]

    # 2. STALE OCCUPANCY
    # Both in Block A Science, but occupancy was reported 15 minutes ago (> 600s)
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()

    t_now2 = datetime.datetime.now(datetime.timezone.utc)
    t_stale = t_now2 - datetime.timedelta(minutes=15)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": f"MSG_OCC_STALE_{uuid.uuid4().hex[:8]}",
        "gateway_id": "GW_PROV_BLDG",
        "auth_token": "gw_key_bldg_auth",
        "device_id": "OCC_SENSOR_BLOCK_A",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block A Science",
        "source_type": "real_sensor",
        "event_timestamp": t_stale.isoformat(),
        "metrics": [{"name": "occupancy_count", "value": 5, "unit": "count"}]
    })

    _send_water_leak_samples(building_id="Block A Science", is_auth=True, step="stale")

    res_stale = client.get("/api/v1/energy/anomalies")
    leaks_stale = [a for a in res_stale.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(leaks_stale) == 1
    anom_stale = leaks_stale[0]
    assert "Suspected" in anom_stale["issue"]
    assert anom_stale["severity"] == "HIGH"
    assert "Occupancy context is unavailable or unverified" in anom_stale["explanation"]
    assert "stale" in anom_stale["explanation"]

    # 3. UNVERIFIED / SIMULATED OCCUPANCY
    # Both in Block A Science and fresh, but occupancy source is simulated_iot (unverified)
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()

    t_now3 = datetime.datetime.now(datetime.timezone.utc)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": f"MSG_OCC_SIM_{uuid.uuid4().hex[:8]}",
        "device_id": "OCC_SENSOR_BLOCK_A",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block A Science",
        "source_type": "simulated_iot",
        "event_timestamp": (t_now3 - datetime.timedelta(seconds=5)).isoformat(),
        "metrics": [{"name": "occupancy_count", "value": 5, "unit": "count"}]
    })

    _send_water_leak_samples(building_id="Block A Science", is_auth=True, step="unver")

    res_unver = client.get("/api/v1/energy/anomalies")
    leaks_unver = [a for a in res_unver.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(leaks_unver) == 1
    anom_unver = leaks_unver[0]
    assert "Suspected" in anom_unver["issue"]
    assert anom_unver["severity"] == "HIGH"
    assert "Occupancy context is unavailable or unverified" in anom_unver["explanation"]
    assert "unverified" in anom_unver["explanation"] or "simulated" in anom_unver["explanation"]

    # 4. VERIFIED SAME-BUILDING CASE
    # Both in Block A Science, both verified hardware, both fresh (< 600s), occupancy < 15
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()

    t_now4 = datetime.datetime.now(datetime.timezone.utc)
    client.post("/api/v1/iot/telemetry", json={
        "message_id": f"MSG_OCC_VERIFIED_A_{uuid.uuid4().hex[:8]}",
        "gateway_id": "GW_PROV_BLDG",
        "auth_token": "gw_key_bldg_auth",
        "device_id": "OCC_SENSOR_BLOCK_A",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block A Science",
        "source_type": "real_sensor",
        "event_timestamp": (t_now4 - datetime.timedelta(seconds=5)).isoformat(),
        "metrics": [{"name": "occupancy_count", "value": 5, "unit": "count"}]
    })

    _send_water_leak_samples(building_id="Block A Science", is_auth=True, step="conf")

    res_conf = client.get("/api/v1/energy/anomalies")
    leaks_conf = [a for a in res_conf.json()["anomalies"] if a["id"] == "ALT_WATER_LEAK"]
    assert len(leaks_conf) == 1
    anom_conf = leaks_conf[0]
    assert anom_conf["building"] == "Block A Science"
    assert anom_conf["issue"] == "Confirmed Off-Hours Water Leak"
    assert anom_conf["severity"] == "CRITICAL"
    assert "Verified same-building occupancy is 5" in anom_conf["explanation"]

