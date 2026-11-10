"""Focused regressions for telemetry normalization, provenance, and live aggregation."""

import datetime
import os
import sys

import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.telemetry_schema import normalize_telemetry_payload
from src.registry.device_registry import DeviceRegistryEngine, GLOBAL_DEVICE_REGISTRY
from api.main import get_latest_live_telemetry, _sustained_power_samples
from src.intelligence.model_consensus import ModelConsensusEngine
from src.intelligence.confidence import ConfidenceEngine


def _payload(metrics, **overrides):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "device_id": "HW_TEST_METER",
        "facility_id": "FAC_TEST",
        "building_id": "Block A",
        "source_type": "real_sensor",
        "event_timestamp": now,
        "sent_timestamp": now,
        "message_id": f"MSG_{datetime.datetime.now().timestamp()}",
        "metrics": metrics,
    }
    payload.update(overrides)
    return payload


def test_unknown_metrics_are_warned_and_not_passed_through():
    envelope, normalized, warnings = normalize_telemetry_payload(
        _payload([
            {"metric": "voltage_v", "value": 230.2, "unit": "V"},
            {"metric": "vendor_private_metric", "value": 123, "unit": "unit"},
        ])
    )
    assert normalized["voltage_v"] == 230.2
    assert "vendor_private_metric" not in normalized
    assert any("unknown metric" in warning.lower() for warning in warnings)


def test_invalid_metric_does_not_drop_other_valid_metrics():
    _, normalized, warnings = normalize_telemetry_payload(
        _payload([
            {"metric": "voltage_v", "value": 231.0, "unit": "V"},
            {"metric": "current_a", "value": "NaN", "unit": "A"},
            {"metric": "water_flow_lmin", "value": None, "unit": "L/min"},
        ])
    )
    assert normalized == {"voltage_v": 231.0}
    assert len(warnings) >= 2


def test_pzem_units_convert_before_canonical_range_check():
    _, normalized, warnings = normalize_telemetry_payload(
        _payload([
            {"metric": "pzem_power_w", "value": 1250, "unit": "W"},
            {"metric": "pzem_energy_wh", "value": 2450, "unit": "Wh"},
        ])
    )
    assert normalized["active_power_kw"] == 1.25
    assert normalized["cumulative_energy_kwh"] == 2.45
    assert len([w for w in warnings if "Converted" in w]) == 2


def test_wrong_units_are_not_silently_accepted():
    with pytest.raises(ValueError, match="no recognized, valid numeric metrics"):
        normalize_telemetry_payload(
            _payload([{"metric": "voltage_v", "value": 230, "unit": "A"}])
        )


def test_unprovisioned_gateway_token_never_verifies_hardware_in_demo_mode():
    registry = DeviceRegistryEngine()
    registry.gateways.clear()
    registry.allow_unverified_demo_mode = True
    result = registry.ingest_telemetry(_payload(
        [{"metric": "voltage_v", "value": 230, "unit": "V"}],
        gateway_id="GW_NOT_PROVISIONED",
        auth_token="arbitrary-client-token",
    ))
    assert result["accepted"] is True
    assert result["is_verified_hardware"] is False
    assert result["data_source_badge"] == "[UNVERIFIED SENSOR - DEMO MODE]"


def test_latest_live_overview_never_mixes_buildings_or_provenance():
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    now = datetime.datetime.now(datetime.timezone.utc)
    GLOBAL_DEVICE_REGISTRY.telemetry_history.extend([
        {
            "device_id": "HW_POWER_A", "facility_id": "FAC_TEST", "building_id": "Block A",
            "source_type": "real_sensor", "is_verified_hardware": True,
            "event_timestamp": now.isoformat(), "metrics": {"active_power_kw": 0.12, "voltage_v": 230},
            "is_valid_sample": True, "quarantined": False, "is_late_sample": False,
        },
        {
            "device_id": "HW_OCC_A", "facility_id": "FAC_TEST", "building_id": "Block A",
            "source_type": "real_sensor", "is_verified_hardware": True,
            "event_timestamp": (now - datetime.timedelta(seconds=2)).isoformat(), "metrics": {"occupancy_count": 8},
            "is_valid_sample": True, "quarantined": False, "is_late_sample": False,
        },
        {
            "device_id": "SIM_OCC_B", "facility_id": "FAC_TEST", "building_id": "Block B",
            "source_type": "simulated_iot", "is_verified_hardware": False,
            "event_timestamp": (now - datetime.timedelta(seconds=1)).isoformat(), "metrics": {"occupancy_count": 2, "air_quality_aqi": 900},
            "is_valid_sample": True, "quarantined": False, "is_late_sample": False,
        },
    ])
    live = get_latest_live_telemetry()
    assert live["building_id"] == "Block A"
    assert live["source_type"] == "real_sensor"
    assert live["data_source_badge"] == "[REAL SENSOR]"
    assert live["active_power_kw"] == 0.12
    assert live["occupancy"] == 8
    assert live["air_aqi"] is None


def test_resource_simulator_payload_uses_backend_canonical_contract():
    _, normalized, warnings = normalize_telemetry_payload({
        "message_id": "SIM_INTEGRATION_TEST_001",
        "simulator_id": "SIM_RESOURCE_DEMO_01",
        "device_id": "SIM-ELEC-01",
        "facility_id": "FAC_TEST",
        "building_id": "Block A",
        "source_type": "simulated_iot",
        "event_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "measurements": {
            "active_power_kw": 0.18,
            "cumulative_energy_kwh": 4.2,
            "voltage_v": 230.0,
            "water_flow_lmin": 2.5,
            "cumulative_water_m3": 0.04,
            "co2_ppm": 620.0,
            "pm25": 12.0,
            "fill_level_percent": 44.0,
            "estimated_waste_kg": 3.0,
        },
    })
    assert normalized["active_power_kw"] == 0.18
    assert normalized["water_flow_lmin"] == 2.5
    assert normalized["co2_ppm"] == 620.0
    assert normalized["fill_level_percent"] == 44.0
    assert not warnings


def test_after_hours_rule_requires_three_recent_contiguous_samples():
    now = pd.Timestamp.now(tz="UTC")
    records = [
        {"event_timestamp": (now - pd.Timedelta(minutes=offset)).isoformat(),
         "metrics": {"active_power_kw": 0.06}}
        for offset in (0, 15, 30)
    ]
    assert len(_sustained_power_samples(records, 0.05, now)) == 3
    records[1]["metrics"]["active_power_kw"] = 0.03
    assert _sustained_power_samples(records, 0.05, now) == []
    records[1]["metrics"]["active_power_kw"] = 0.06
    records[2]["event_timestamp"] = (now - pd.Timedelta(minutes=50)).isoformat()
    assert _sustained_power_samples(records, 0.05, now) == []


def test_consensus_and_confidence_do_not_invent_missing_model_evidence():
    consensus = ModelConsensusEngine().evaluate_consensus()
    assert consensus["consensus_status"] == "INSUFFICIENT_EVIDENCE"
    assert consensus["model_consensus_score"] is None
    confidence = ConfidenceEngine().calculate_decision_confidence()
    assert confidence["overall_confidence_pct"] == 0.0
    assert confidence["is_sufficient_for_action"] is False
