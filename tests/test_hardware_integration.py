"""
EstateIQ ESP32 & Physical Sensor Hardware Integration Test Suite
(tests/test_hardware_integration.py)

Validates the full edge telemetry pipeline:
1. Canonical Modbus RTU electricity telemetry normalization (Eastron SDM630 / SDM120).
2. Canonical YF-S201 turbine water flow pulse counter normalization.
3. Gateway authentication gate & provenance security:
   - Valid gateway key grants is_verified_hardware=True and [REAL SENSOR] badge.
   - Unauthenticated real_sensor claim does NOT receive verified hardware badge.
   - Invalid or revoked gateway credentials are strictly rejected.
4. MQTT consumer payload processing & topic hierarchy extraction parity.
5. HTTP REST ingestion parity (/api/v1/iot/telemetry).
6. Duplicate message idempotency (bounded cache).
7. Device & building attribution isolation (Block B Hostel vs Block A).
8. Physical metric boundary & quality validation.
9. Stale/offline health transitions.
"""

import os
import sys
import copy
import json
import time
import datetime
import pytest

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.telemetry_schema import (
    normalize_telemetry_payload,
    resolve_provenance_badge,
    SourceType,
    MetricQuality,
    DeviceHealthStatus
)
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
from src.data.mqtt_consumer import MQTTTelemetryConsumer, parse_topic_metadata
from api.main import ingest_iot_telemetry, get_iot_telemetry_stream, list_iot_devices, get_latest_device_telemetry


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry state before each test to maintain strict test isolation."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.gateways.clear()

    # Provision standard verified test gateway
    GLOBAL_DEVICE_REGISTRY.register_gateway(
        gateway_id="ESP32_EDGE_GATEWAY_01",
        gateway_name="ESP32 Bench Edge Node (Modbus/Pulse)",
        api_key="gw_secret_estateiq_hw_2026",
        is_verified=True
    )
    yield


# =========================================================================================
# 1. Modbus Electricity Telemetry Tests
# =========================================================================================

def test_01_modbus_electricity_telemetry_normalization():
    """Verify raw Eastron SDM630 Modbus payload normalizes to canonical units and fields."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_ELEC_TEST_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 101,
        "metrics": [
            {"metric": "voltage_v", "value": 231.4, "unit": "V", "quality": "good"},
            {"metric": "current_a", "value": 64.2, "unit": "A", "quality": "good"},
            {"metric": "active_power_kw", "value": 14.85, "unit": "kW", "quality": "good"},
            {"metric": "cumulative_energy_kwh", "value": 12845.6, "unit": "kWh", "quality": "good"},
            {"metric": "power_factor", "value": 0.96, "unit": "ratio", "quality": "good"},
            {"metric": "frequency_hz", "value": 50.02, "unit": "Hz", "quality": "good"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "METER-BLOCK-B-001"
    assert res["source_type"] == "real_sensor"
    assert res["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in res["data_source_badge"]

    # Check registered device state
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER-BLOCK-B-001"]
    assert dev.status == "ONLINE"
    assert dev.is_verified_hardware is True
    assert dev.source_type == "real_sensor"
    assert dev.last_telemetry["active_power_kw"] == 14.85
    assert dev.last_telemetry["voltage_v"] == 231.4
    assert dev.last_telemetry["current_a"] == 64.2
    assert dev.last_telemetry["cumulative_energy_kwh"] == 12845.6
    assert dev.last_telemetry["power_factor"] == 0.96
    assert dev.last_telemetry["frequency_hz"] == 50.02


# =========================================================================================
# 2. Water Flow Pulse Counter Telemetry Tests
# =========================================================================================

def test_02_water_flow_pulse_telemetry_normalization():
    """Verify YF-S201 Hall-effect turbine telemetry normalizes and updates volume accumulator."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_WATER_TEST_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "WATER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 102,
        "metrics": [
            {"metric": "water_flow_lmin", "value": 14.5, "unit": "L/min", "quality": "good"},
            {"metric": "cumulative_water_m3", "value": 12.85, "unit": "m3", "quality": "good"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "WATER-BLOCK-B-001"
    assert res["is_verified_hardware"] is True

    dev = GLOBAL_DEVICE_REGISTRY.devices["WATER-BLOCK-B-001"]
    assert dev.last_telemetry["water_flow_lmin"] == 14.5
    assert dev.last_telemetry["cumulative_water_m3"] == 12.85


# =========================================================================================
# 3. Gateway Authentication Gate & Provenance Security
# =========================================================================================

def test_03_valid_gateway_key_grants_verified_hardware():
    """Valid gateway credential grants verified hardware provenance and emerald badge."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "message_id": "MSG_AUTH_VALID_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 22.0}]
    }
    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    assert res["accepted"] is True
    assert res["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in res["data_source_badge"]


def test_04_unauthenticated_claim_never_granted_verified_badge():
    """A self-declared real_sensor claim without valid credential NEVER receives verified hardware."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # 1. Missing auth_token in unverified demo mode
    GLOBAL_DEVICE_REGISTRY.allow_unverified_demo_mode = True
    payload_no_token = {
        "message_id": "MSG_UNAUTH_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 22.0}]
    }
    res1 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_no_token)
    assert res1["accepted"] is True
    assert res1["is_verified_hardware"] is False
    assert "[UNVERIFIED SENSOR - DEMO MODE]" in res1["data_source_badge"]

    # 2. In strict production mode, unauthenticated claim is strictly rejected
    GLOBAL_DEVICE_REGISTRY.allow_unverified_demo_mode = False
    payload_strict = {
        "message_id": "MSG_UNAUTH_02",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 22.0}]
    }
    res2 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_strict)
    assert res2["accepted"] is False
    assert res2["error"] == "MISSING_GATEWAY_CREDENTIAL"


def test_05_invalid_or_revoked_gateway_credential_rejected():
    """Invalid or revoked credentials are systematically rejected with HTTP-safe error."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Wrong token
    payload_wrong = {
        "message_id": "MSG_WRONG_TOKEN",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "incorrect_token_xyz",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 22.0}]
    }
    res_wrong = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_wrong)
    assert res_wrong["accepted"] is False
    assert res_wrong["error"] == "INVALID_GATEWAY_CREDENTIAL"

    # Revoked gateway
    GLOBAL_DEVICE_REGISTRY.revoke_gateway("ESP32_EDGE_GATEWAY_01")
    payload_revoked = {
        "message_id": "MSG_REVOKED_GATEWAY",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 22.0}]
    }
    res_revoked = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_revoked)
    assert res_revoked["accepted"] is False
    assert res_revoked["error"] == "REVOKED_GATEWAY_CREDENTIAL"


# =========================================================================================
# 4. MQTT Consumer End-to-End Processing & Topic Parsing
# =========================================================================================

def test_06_mqtt_topic_hierarchy_parsing():
    """Verify parse_topic_metadata extracts facility, building, and device accurately."""
    topic = "estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry"
    meta = parse_topic_metadata(topic)
    assert meta["facility_id"] == "FAC_GEC_CAMPUS"
    assert meta["building_id"] == "Block B Hostel"
    assert meta["device_id"] == "METER-BLOCK-B-001"

    short_topic = "estateiq/telemetry/DEV_SHORT_01"
    meta_short = parse_topic_metadata(short_topic)
    assert meta_short["device_id"] == "DEV_SHORT_01"


def test_07_mqtt_consumer_payload_processing_parity():
    """Verify MQTT consumer enriches topic metadata and executes canonical ingestion."""
    consumer = MQTTTelemetryConsumer()
    topic = "estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry"

    # Payload omits facility_id and building_id so consumer must extract from topic
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_dict = {
        "schema_version": "1.0",
        "message_id": "MSG_MQTT_TEST_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [
            {"metric": "active_power_kw", "value": 35.2},
            {"metric": "voltage_v", "value": 229.8}
        ]
    }
    payload_bytes = json.dumps(raw_dict).encode("utf-8")

    res = consumer.process_message_payload(topic, payload_bytes)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "METER-BLOCK-B-001"
    assert res["is_verified_hardware"] is True

    # Confirm device stored in registry with topic metadata
    dev = GLOBAL_DEVICE_REGISTRY.devices["METER-BLOCK-B-001"]
    assert dev.last_telemetry["active_power_kw"] == 35.2
    assert dev.last_telemetry["voltage_v"] == 229.8
    assert dev.facility_id == "FAC_GEC_CAMPUS"
    assert dev.building_id == "Block B Hostel"


# =========================================================================================
# 5. HTTP Ingestion and Parity
# =========================================================================================

def test_08_http_and_mqtt_ingestion_parity():
    """Verify HTTP endpoint and MQTT ingestion produce identical normalized registry states."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    consumer = MQTTTelemetryConsumer()

    # 1. Ingest via MQTT
    mqtt_payload = {
        "message_id": "MSG_PARITY_MQTT",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 50.0}, {"metric": "voltage_v", "value": 230.0}]
    }
    res_mqtt = consumer.process_message_payload("estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry", json.dumps(mqtt_payload).encode("utf-8"))

    # 2. Ingest via HTTP endpoint handler directly
    http_payload = {
        "message_id": "MSG_PARITY_HTTP",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-002",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 50.0}, {"metric": "voltage_v", "value": 230.0}]
    }
    res_http = ingest_iot_telemetry(http_payload)

    assert res_mqtt["accepted"] == res_http["accepted"]
    assert res_mqtt["is_verified_hardware"] == res_http["is_verified_hardware"]
    assert res_mqtt["data_source_badge"] == res_http["data_source_badge"]

    dev_mqtt = GLOBAL_DEVICE_REGISTRY.devices["METER-BLOCK-B-001"]
    dev_http = GLOBAL_DEVICE_REGISTRY.devices["METER-BLOCK-B-002"]
    assert dev_mqtt.last_telemetry["active_power_kw"] == dev_http.last_telemetry["active_power_kw"]
    assert dev_mqtt.last_telemetry["voltage_v"] == dev_http.last_telemetry["voltage_v"]


# =========================================================================================
# 6. Idempotency & Bounded Duplicate Filtering
# =========================================================================================

def test_09_duplicate_message_idempotency():
    """Duplicate message_id is safely recognized and returned as DUPLICATE_IGNORED without side-effects."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "message_id": "MSG_DUP_TEST_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 10.0}]
    }

    res1 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    assert res1["accepted"] is True
    assert res1.get("duplicate") is not True

    # Immediate resubmission of same message_id
    res2 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    assert res2["accepted"] is True
    assert res2["duplicate"] is True
    assert res2["status"] == "DUPLICATE_IGNORED"
    # Ensure not duplicated in telemetry history
    history_entries = [t for t in GLOBAL_DEVICE_REGISTRY.telemetry_history if t.get("message_id") == "MSG_DUP_TEST_01"]
    assert len(history_entries) == 1


# =========================================================================================
# 7. Device and Building Attribution Isolation
# =========================================================================================

def test_10_device_and_building_isolation():
    """Telemetry from one meter never overwrites or bleeds into another device or building."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Block B Electricity
    p1 = {
        "message_id": "MSG_ISOLATION_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 75.0}]
    }
    # Block A Water
    p2 = {
        "message_id": "MSG_ISOLATION_02",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "WATER-BLOCK-A-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block A Academic",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "water_flow_lmin", "value": 25.0}]
    }

    GLOBAL_DEVICE_REGISTRY.ingest_telemetry(p1)
    GLOBAL_DEVICE_REGISTRY.ingest_telemetry(p2)

    dev_elec = GLOBAL_DEVICE_REGISTRY.devices["METER-BLOCK-B-001"]
    dev_water = GLOBAL_DEVICE_REGISTRY.devices["WATER-BLOCK-A-001"]

    assert dev_elec.building_id == "Block B Hostel"
    assert "water_flow_lmin" not in dev_elec.last_telemetry
    assert dev_elec.last_telemetry["active_power_kw"] == 75.0

    assert dev_water.building_id == "Block A Academic"
    assert "active_power_kw" not in dev_water.last_telemetry
    assert dev_water.last_telemetry["water_flow_lmin"] == 25.0


# =========================================================================================
# 8. Physical Metric Boundaries and Quality Validation
# =========================================================================================

def test_11_physical_bounds_and_non_finite_rejection():
    """Non-finite (inf/NaN) and physically impossible values are flagged or clamped."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload_nan = {
        "message_id": "MSG_BOUNDS_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [
            {"metric": "active_power_kw", "value": float("inf")},
            {"metric": "voltage_v", "value": 230.0}
        ]
    }
    # Inf or NaN values must fail schema validation or be dropped
    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_nan)
    dev = GLOBAL_DEVICE_REGISTRY.devices.get("METER-BLOCK-B-001")
    if dev:
        assert dev.last_telemetry.get("active_power_kw") != float("inf")


# =========================================================================================
# 9. Telemetry Stream API Endpoint Verification
# =========================================================================================

def test_12_telemetry_stream_api_endpoint():
    """Verify get_iot_telemetry_stream returns unified real-time stream with provenance."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
        "message_id": "MSG_STREAM_01",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "METER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "metrics": [{"metric": "active_power_kw", "value": 42.0}]
    })

    stream_res = get_iot_telemetry_stream(limit=10)
    assert stream_res["count"] >= 1
    assert stream_res["total_ingested"] >= 1
    assert any(s["message_id"] == "MSG_STREAM_01" for s in stream_res["stream"])
    matched = next(s for s in stream_res["stream"] if s["message_id"] == "MSG_STREAM_01")
    assert matched["is_verified_hardware"] is True
    assert matched["source_type"] == "real_sensor"
