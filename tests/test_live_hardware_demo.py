"""
EstateIQ Live Hardware Demo & MQ-135 Environmental Node Test Suite
(tests/test_live_hardware_demo.py)

Validates:
1. Canonical MQ-135 air quality payload normalization (raw ADC, voltage, indicative ppm, warm-up state).
2. Range validation and physical boundary gating for MQ-135 metrics (rejection of out-of-bounds ADC/voltage).
3. Authenticated gateway provenance asserting [REAL SENSOR] / [LIVE HARDWARE].
4. Device freshness lifecycle transitions (CONNECTING, ONLINE, STALE, OFFLINE).
5. Live hardware buffer retention and get_device_live_status API endpoint.
6. Error handling for unknown devices (HTTP 404).
"""

import os
import sys
import copy
import time
import datetime
import pytest
from fastapi import HTTPException

# Ensure root directory on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.telemetry_schema import (
    normalize_telemetry_payload,
    resolve_provenance_badge,
    SourceType,
    MetricQuality,
    DeviceHealthStatus
)
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY, VirtualDevice
from api.main import get_device_live_status


@pytest.fixture(autouse=True)
def setup_test_registry():
    """Reset registry state before each test to guarantee isolation."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.device_telemetry_buffers.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.gateways.clear()

    # Provision standard verified ESP32 gateway
    GLOBAL_DEVICE_REGISTRY.register_gateway(
        gateway_id="ESP32_EDGE_GATEWAY_01",
        gateway_name="ESP32 Bench Edge Node (Modbus/Pulse/MQ135)",
        api_key="gw_secret_estateiq_hw_2026",
        is_verified=True
    )
    yield


# =========================================================================================
# 1. MQ-135 Environmental Telemetry Normalization
# =========================================================================================

def test_01_mq135_telemetry_normalization():
    """Verify raw MQ-135 payload normalizes to canonical metrics and verified hardware badge."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_MQ135_001",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "ENV-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 42,
        "metrics": [
            {"metric": "mq135_raw_adc", "value": 1248.0, "unit": "count", "quality": "good"},
            {"metric": "mq135_voltage_v", "value": 1.01, "unit": "V", "quality": "good"},
            {"metric": "mq135_co2_estimate_ppm", "value": 612.0, "unit": "ppm", "quality": "good"},
            {"metric": "mq135_warmup_status", "value": 1.0, "unit": "status", "quality": "good"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "ENV-BLOCK-B-001"
    assert res["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in res["data_source_badge"]

    # Verify device state in registry
    dev = GLOBAL_DEVICE_REGISTRY.devices["ENV-BLOCK-B-001"]
    assert dev.status == "ONLINE"
    assert dev.last_telemetry["mq135_raw_adc"] == 1248.0
    assert dev.last_telemetry["mq135_voltage_v"] == 1.01
    assert dev.last_telemetry["mq135_co2_estimate_ppm"] == 612.0
    assert dev.last_telemetry["mq135_warmup_status"] == 1.0


def test_02_mq135_out_of_bounds_rejection():
    """Verify impossible ADC values (>4095) or voltages (>5V) are caught and rejected."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    invalid_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_MQ135_OOB",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "ENV-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 43,
        "metrics": [
            {"metric": "mq135_raw_adc", "value": 5000.0, "unit": "count", "quality": "good"},  # Plausible max 4095
            {"metric": "mq135_voltage_v", "value": 12.0, "unit": "V", "quality": "good"}        # Plausible max 5.0V
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(invalid_payload)
    # The normalizer rejects out of range metrics
    assert res["success"] is False
    assert res["accepted"] is False
    assert "outside plausible physical range" in res["error"]


# =========================================================================================
# 2. Gateway Authentication & Provenance Integrity
# =========================================================================================

def test_03_unauthenticated_sensor_claim_denied_verified_badge():
    """Unauthenticated telemetry claiming real_sensor must NEVER receive verified badge."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    spoofed_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_SPOOF_001",
        "device_id": "ENV-BLOCK-B-001",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",  # Claiming real sensor without valid gateway
        "event_timestamp": now_iso,
        "metrics": [
            {"metric": "mq135_raw_adc", "value": 1100.0, "unit": "count"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(spoofed_payload)
    # Even if accepted in unverified demo mode, hardware badge MUST NOT be granted
    assert res["is_verified_hardware"] is False
    assert "[REAL SENSOR]" not in res["data_source_badge"]


# =========================================================================================
# 3. Dynamic Device Freshness Lifecycle
# =========================================================================================

def test_04_device_freshness_lifecycle():
    """Verify transitions: CONNECTING -> ONLINE -> STALE -> OFFLINE."""
    # Pre-register device without telemetry
    now_iso = datetime.datetime.now().isoformat()
    dev = VirtualDevice(
        device_id="ENV-BLOCK-B-001",
        device_name="Block B Environmental Node",
        instance_id="ESP32_EDGE_GATEWAY_01",
        device_type="air_quality_monitor",
        facility_id="FAC_GEC_CAMPUS",
        building_id="Block B Hostel",
        status="ONLINE",
        created_at=now_iso,
        last_sample_at=None,
        is_verified_hardware=True
    )
    GLOBAL_DEVICE_REGISTRY.devices["ENV-BLOCK-B-001"] = dev

    # 1. State before any telemetry: CONNECTING
    status_0 = GLOBAL_DEVICE_REGISTRY.get_device_freshness_status("ENV-BLOCK-B-001")
    assert status_0["status"] == "CONNECTING"

    # 2. Telemetry arrives: ONLINE (< 45 sec age)
    dev.last_sample_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status_online = GLOBAL_DEVICE_REGISTRY.get_device_freshness_status("ENV-BLOCK-B-001")
    assert status_online["status"] == "ONLINE"
    assert status_online["age_sec"] < 5.0

    # 3. Simulated age 60s: STALE (46s - 300s)
    stale_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)).isoformat()
    dev.last_sample_at = stale_iso
    status_stale = GLOBAL_DEVICE_REGISTRY.get_device_freshness_status("ENV-BLOCK-B-001")
    assert status_stale["status"] == "STALE"
    assert 55.0 <= status_stale["age_sec"] <= 65.0

    # 4. Simulated age 400s: OFFLINE (> 300s)
    offline_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=400)).isoformat()
    dev.last_sample_at = offline_iso
    status_offline = GLOBAL_DEVICE_REGISTRY.get_device_freshness_status("ENV-BLOCK-B-001")
    assert status_offline["status"] == "OFFLINE"
    assert status_offline["age_sec"] >= 390.0


# =========================================================================================
# 4. Live Device History Buffer & API Endpoint
# =========================================================================================

def test_05_device_live_endpoint_and_ring_buffer():
    """Verify get_device_live_status endpoint returns status and buffer."""
    # Ingest 3 successive samples
    base_time = datetime.datetime.now(datetime.timezone.utc)
    for i in range(3):
        pkt_time = (base_time + datetime.timedelta(seconds=i*5)).isoformat()
        payload = {
            "schema_version": "1.0",
            "message_id": f"MSG_RING_{i}",
            "gateway_id": "ESP32_EDGE_GATEWAY_01",
            "device_id": "ENV-BLOCK-B-001",
            "auth_token": "gw_secret_estateiq_hw_2026",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel",
            "source_type": "real_sensor",
            "event_timestamp": pkt_time,
            "metrics": [
                {"metric": "mq135_raw_adc", "value": 1200.0 + (i * 50), "unit": "count"},
                {"metric": "mq135_voltage_v", "value": 0.98 + (i * 0.04), "unit": "V"}
            ]
        }
        res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
        assert res["success"] is True

    # Call endpoint function directly
    data = get_device_live_status("ENV-BLOCK-B-001")

    assert data["device_id"] == "ENV-BLOCK-B-001"
    assert data["status"] == "ONLINE"
    assert data["is_verified_hardware"] is True
    assert len(data["recent_samples"]) == 3
    # Check chronological order of recent_samples
    assert data["recent_samples"][-1]["metrics"]["mq135_raw_adc"] == 1300.0


def test_06_live_endpoint_404_for_unknown_device():
    """Verify get_device_live_status raises 404 for nonexistent device."""
    with pytest.raises(HTTPException) as excinfo:
        get_device_live_status("NONEXISTENT_DEVICE_999")
    assert excinfo.value.status_code == 404


def test_07_ajsr04m_ultrasonic_tank_telemetry_normalization():
    """Verify AJ-SR04M ultrasonic distance and tank level normalize with [REAL SENSOR] badge."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_AJSR04M_001",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "WATER-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 88,
        "metrics": [
            {"metric": "tank_distance_cm", "value": 34.2, "unit": "cm", "quality": "good"},
            {"metric": "tank_level_pct", "value": 82.9, "unit": "%", "quality": "good"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "WATER-BLOCK-B-001"
    assert res["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in res["data_source_badge"]

    # Verify device status and telemetry
    dev = GLOBAL_DEVICE_REGISTRY.devices["WATER-BLOCK-B-001"]
    assert dev.status == "ONLINE"
    assert dev.last_telemetry["tank_distance_cm"] == 34.2
    assert dev.last_telemetry["tank_level_pct"] == 82.9


def test_08_hcsr04_waste_bin_telemetry_normalization():
    """Verify HC-SR04 ultrasonic waste bin telemetry normalizes with [REAL SENSOR] badge and updates repo."""
    from src.data.repository import DataRepository
    repo = DataRepository()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_payload = {
        "schema_version": "1.0",
        "message_id": "MSG_ESP32_HCSR04_WASTE_001",
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "device_id": "WASTE-BLOCK-B-001",
        "auth_token": "gw_secret_estateiq_hw_2026",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor",
        "event_timestamp": now_iso,
        "sent_timestamp": now_iso,
        "sequence_number": 105,
        "bin_distance_cm": 22.4,
        "fill_level_percent": 75.8,
        "metrics": [
            {"metric": "bin_distance_cm", "value": 22.4, "unit": "cm", "quality": "good"},
            {"metric": "fill_level_percent", "value": 75.8, "unit": "%", "quality": "good"}
        ]
    }

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert res["success"] is True
    assert res["accepted"] is True
    assert res["device_id"] == "WASTE-BLOCK-B-001"
    assert res["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in res["data_source_badge"]

    # Verify device status and telemetry in registry
    dev = GLOBAL_DEVICE_REGISTRY.devices["WASTE-BLOCK-B-001"]
    assert dev.status == "ONLINE"
    assert dev.last_telemetry["bin_distance_cm"] == 22.4
    assert dev.last_telemetry["fill_level_percent"] == 75.8

    # Verify repo.get_latest_waste() returns real-time sensor reading
    waste_summary = repo.get_latest_waste()
    assert waste_summary["fill_level_pct"] == 75.8
    assert waste_summary["bin_distance_cm"] == 22.4
    assert waste_summary["is_verified_hardware"] is True
    assert "[REAL SENSOR]" in waste_summary["provenance_badge"]
