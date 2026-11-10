"""
EstateIQ Adaptive Telemetry Reporting & Advanced Anomaly Detection Test Suite
(tests/test_adaptive_reporting_and_anomaly.py)

Validates:
1. Normal operation: 15-minute cadence (900s) with continuous high-frequency sensor acquisition.
2. Anomaly detection & Immediate trigger: Out-of-bounds / statistical spike triggers immediate
   telemetry event without waiting for 15-minute timer, switching cadence to 5 minutes (300s).
3. Persistence & Noise rejection: Moderate deviations require consecutive sample persistence,
   preventing single-sample transient spikes from generating false alarms.
4. Recovery confirmation: Returns to nominal readings; enters RECOVERY_5M for 3 consecutive
   confirmation cycles (15m total observation) before reverting to NORMAL_15M.
5. Recurrence during recovery: Anomaly returning during recovery resets confirmation counter
   and immediately returns to ANOMALY_5M.
6. Offline buffering & late data isolation: Stored offline packets do not trigger false live alarms.
7. Monotonic counter reset isolation: Graceful handling of pulse counter reboot/wrap.
8. Honest MQ-135 profiling: Raw ADC handled as uncertified indicative signal; standby/warmup handled safely.
9. Time-ordered holdout replay benchmark: Evaluates EstateIQ adaptive anomaly engine against
   legacy static thresholding, demonstrating improved specificity without future lookahead.
10. REST API endpoints: GET /api/v1/iot/telemetry/adaptive-status and POST /api/v1/iot/telemetry/evaluate-benchmark.
"""

import os
import sys
import copy
import datetime
import pytest

# Ensure root directory on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.telemetry_schema import (
    normalize_telemetry_payload,
    SourceType,
    MetricQuality,
    DeviceHealthStatus,
    TelemetryEnvelope
)
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY, VirtualDevice
from src.services.anomaly_engine import (
    EstateIQAdaptiveAnomalyEngine,
    AdaptiveReportingState,
    GLOBAL_ADAPTIVE_ANOMALY_ENGINE
)
from api.main import get_adaptive_telemetry_status, evaluate_anomaly_benchmark


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Reset registry and anomaly engine before each test for complete test isolation."""
    GLOBAL_DEVICE_REGISTRY.telemetry_history.clear()
    GLOBAL_DEVICE_REGISTRY.device_telemetry_buffers.clear()
    GLOBAL_DEVICE_REGISTRY.seen_message_ids.clear()
    GLOBAL_DEVICE_REGISTRY.devices.clear()
    GLOBAL_DEVICE_REGISTRY.gateways.clear()

    # Provision standard verified ESP32 gateway
    GLOBAL_DEVICE_REGISTRY.register_gateway(
        gateway_id="ESP32_EDGE_GATEWAY_01",
        gateway_name="ESP32 Bench Edge Node (Modbus/Pulse/MQ135/Sonar)",
        api_key="gw_secret_estateiq_hw_2026",
        is_verified=True
    )

    # Reset adaptive anomaly engine
    GLOBAL_ADAPTIVE_ANOMALY_ENGINE.reset()


def make_telemetry_payload(device_id, metric_name, metric_value, seq=1, reporting_state="NORMAL_15M",
                           reporting_interval_sec=900, is_anomaly=False, is_verified_hardware=True,
                           buffered_offline=False, timestamp=None, **extra_metrics):
    """Helper to construct canonical telemetry payload matching ESP32 firmware output."""
    if timestamp is None:
        # Strictly monotonically increasing timestamp based on sequence number
        base = datetime.datetime.now(datetime.timezone.utc)
        timestamp = (base + datetime.timedelta(seconds=seq)).isoformat()

    metrics = {metric_name: metric_value}
    metrics.update(extra_metrics)

    metrics_list = [{"metric": k, "value": v} for k, v in metrics.items()]
    return {
        "device_id": device_id,
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "real_sensor" if is_verified_hardware else "simulated_iot",
        "is_verified_hardware": is_verified_hardware,
        "gateway_id": "ESP32_EDGE_GATEWAY_01",
        "api_key": "gw_secret_estateiq_hw_2026",
        "message_id": f"MSG_{device_id}_{seq:04d}",
        "sequence_number": seq,
        "sent_timestamp": timestamp,
        "event_timestamp": timestamp,
        "buffered_offline": buffered_offline,
        "reporting_state": reporting_state,
        "reporting_interval_sec": reporting_interval_sec,
        "next_report_expected_sec": reporting_interval_sec,
        "is_anomaly": is_anomaly,
        "metrics": metrics_list
    }


def test_normal_operation_15m_cadence():
    """Test 1: Normal operation maintains 15-minute reporting cadence (900s) and NORMAL_15M state."""
    payload = make_telemetry_payload(
        device_id="METER-BLOCK-B-001",
        metric_name="active_power_kw",
        metric_value=1.85,
        voltage_v=230.5,
        current_a=8.02,
        power_factor=0.98,
        reporting_state="NORMAL_15M",
        reporting_interval_sec=900,
        seq=1
    )

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload)
    assert res["success"] is True
    assert res["reporting_state"] == "NORMAL_15M"
    assert res["reporting_interval_sec"] == 900
    assert res["is_anomaly"] is False

    # Check device registry state
    dev = GLOBAL_DEVICE_REGISTRY.get_device("METER-BLOCK-B-001")
    assert dev is not None
    assert dev.reporting_state == "NORMAL_15M"
    assert dev.reporting_interval_sec == 900
    assert dev.active_anomaly is None


def test_immediate_anomaly_trigger_and_switch_to_5m():
    """Test 2: Extreme power spike triggers immediate anomaly event and switches cadence to 5 minutes (300s)."""
    # 1. Normal baseline reading first
    p1 = make_telemetry_payload("METER-BLOCK-B-001", "active_power_kw", 1.8, seq=1)
    GLOBAL_DEVICE_REGISTRY.ingest_telemetry(p1)

    # 2. Over-capacity anomaly reading (e.g. 4.8 kW on single-phase meter exceeding 3.5 kW threshold)
    p2 = make_telemetry_payload(
        device_id="METER-BLOCK-B-001",
        metric_name="active_power_kw",
        metric_value=4.85,
        seq=2,
        reporting_state="ANOMALY_5M",
        reporting_interval_sec=300,
        is_anomaly=True,
        voltage_v=232.0
    )

    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(p2)
    assert res["success"] is True
    assert res["reporting_state"] == "ANOMALY_5M"
    assert res["reporting_interval_sec"] == 300
    assert res["is_anomaly"] is True

    # Validate active anomaly record in device registry
    dev = GLOBAL_DEVICE_REGISTRY.get_device("METER-BLOCK-B-001")
    assert dev.reporting_state == "ANOMALY_5M"
    assert dev.reporting_interval_sec == 300
    assert dev.active_anomaly is not None
    assert dev.active_anomaly["metric"] == "active_power_kw"
    assert dev.active_anomaly["observed_value"] == 4.85


def test_edge_and_backend_anomaly_origin_tagging():
    """Test 3: Validates clear differentiation between [EDGE DETECTED] and [BACKEND DETECTED] origins."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Case A: Edge detected flag present in firmware envelope
    res_edge = engine.evaluate_reading(
        device_id="WATER-BLOCK-B-001",
        metric="tank_distance_cm",
        value=15.0,  # Below 25cm safety clearance
        is_edge_flagged=True,
        edge_details="Sonar near-field breach (< 25 cm)"
    )
    assert res_edge.is_anomaly is True
    assert res_edge.origin == "EDGE_DETECTED"
    assert "EDGE DETECTED" in res_edge.reason or "near-field" in res_edge.reason

    # Case B: Edge did not flag, but Backend detected statistical violation
    res_backend = engine.evaluate_reading(
        device_id="WATER-BLOCK-B-001",
        metric="water_flow_lmin",
        value=35.0,  # Far above 18 L/min limit
        is_edge_flagged=False
    )
    assert res_backend.is_anomaly is True
    assert res_backend.origin == "BACKEND_DETECTED"


def test_persistence_rejects_single_sample_glitch():
    """Test 4: Noise rejection - moderate statistical deviation requires persistence, rejecting single-sample glitch."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Establish baseline with 10 normal samples (2.0 kW)
    for i in range(10):
        engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)

    # Single moderate spike (2.7 kW - above normal baseline 2.0 kW, ~2.8 MAD, but below instant trip 3.5 kW)
    r1 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.7)
    # 1st sample: pending persistence, NOT yet marked as active anomaly
    assert r1.is_anomaly is False
    assert r1.reporting_state == AdaptiveReportingState.NORMAL_15M

    # Returns to normal on next sample -> transient noise absorbed without alarm
    r2 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)
    assert r2.is_anomaly is False
    assert r2.reporting_state == AdaptiveReportingState.NORMAL_15M


def test_sustained_deviation_triggers_after_persistence():
    """Test 5: Sustained moderate deviation triggers anomaly after persistence count is met."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Baseline
    for _ in range(10):
        engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)

    # Sample 1 of moderate elevation
    r1 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.7)
    assert r1.is_anomaly is False

    # Sample 2 of moderate elevation (meets persistence >= 2)
    r2 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.7)
    assert r2.is_anomaly is True
    assert r2.reporting_state == AdaptiveReportingState.ANOMALY_5M
    assert r2.reporting_interval_sec == 300


def test_recovery_state_requires_3_consecutive_cycles():
    """Test 6: Recovery confirmation requires 3 consecutive normal cycles before returning to NORMAL_15M."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Baseline
    for _ in range(5):
        engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)

    # Trigger anomaly with safety boundary breach
    r_anom = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=4.5)
    assert r_anom.is_anomaly is True
    assert r_anom.reporting_state == AdaptiveReportingState.ANOMALY_5M

    # Cycle 1: Values return to normal -> Enters RECOVERY_5M (cycle 1 of 3)
    c1 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)
    assert c1.is_anomaly is False
    assert c1.reporting_state == AdaptiveReportingState.RECOVERY_5M
    assert c1.reporting_interval_sec == 300  # Remains 5-min cadence during recovery!
    assert c1.recovery_cycles_confirmed == 1

    # Cycle 2: Values remain normal -> Remains in RECOVERY_5M (cycle 2 of 3)
    c2 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)
    assert c2.is_anomaly is False
    assert c2.reporting_state == AdaptiveReportingState.RECOVERY_5M
    assert c2.reporting_interval_sec == 300
    assert c2.recovery_cycles_confirmed == 2

    # Cycle 3: Values remain normal -> Clears recovery and reverts to NORMAL_15M!
    c3 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)
    assert c3.is_anomaly is False
    assert c3.reporting_state == AdaptiveReportingState.NORMAL_15M
    assert c3.reporting_interval_sec == 900


def test_anomaly_recurrence_during_recovery_reverts_to_anomaly_5m():
    """Test 7: If anomaly returns during RECOVERY_5M, state immediately reverts to ANOMALY_5M."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Trigger anomaly
    engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=4.5)

    # 1 normal cycle (enters recovery)
    c1 = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=2.0)
    assert c1.reporting_state == AdaptiveReportingState.RECOVERY_5M
    assert c1.recovery_cycles_confirmed == 1

    # Spike returns!
    c_spike = engine.evaluate_reading(device_id="METER-BLOCK-B-001", metric="active_power_kw", value=4.8)
    assert c_spike.is_anomaly is True
    assert c_spike.reporting_state == AdaptiveReportingState.ANOMALY_5M
    assert c_spike.reporting_interval_sec == 300
    assert c_spike.recovery_cycles_confirmed == 0


def test_late_buffered_packet_does_not_trigger_false_live_alarm():
    """Test 8: Buffered packets from an offline queue do not disrupt the live cadence state."""
    # First ingest a live normal packet
    live_p = make_telemetry_payload("METER-BLOCK-B-001", "active_power_kw", 2.0, seq=10)
    GLOBAL_DEVICE_REGISTRY.ingest_telemetry(live_p)

    # Ingest a delayed buffered packet from 2 hours ago that happened to have high load
    past_ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).isoformat()
    buff_p = make_telemetry_payload(
        "METER-BLOCK-B-001", "active_power_kw", 4.5, seq=2,
        buffered_offline=True, timestamp=past_ts
    )
    res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(buff_p)
    assert res["success"] is True

    # Device live state must NOT be forced into active live anomaly by late historical packet
    dev = GLOBAL_DEVICE_REGISTRY.get_device("METER-BLOCK-B-001")
    assert dev.reporting_state == "NORMAL_15M"


def test_monotonic_counter_reset_isolation():
    """Test 9: Monotonic pulse counter resetting due to ESP32 reboot is isolated without false anomaly."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # 1. Device was at 15000 pulses / 33.3 m3
    res_normal = engine.evaluate_reading(
        device_id="WATER-BLOCK-B-001",
        metric="cumulative_water_m3",
        value=33.3
    )
    assert res_normal.is_anomaly is False

    # 2. ESP32 reboot occurred -> counter resets to 0.05 m3
    # The anomaly engine data quality check recognizes monotonic counter resets
    res_reset = engine.evaluate_reading(
        device_id="WATER-BLOCK-B-001",
        metric="cumulative_water_m3",
        value=0.05
    )
    # Must NOT report as catastrophic pipe burst
    assert res_reset.is_anomaly is False


def test_mq135_raw_adc_standby_isolation():
    """Test 10: MQ-135 raw ADC at 0 during sensor warm-up is treated as STANDBY, not toxic air anomaly."""
    engine = EstateIQAdaptiveAnomalyEngine()

    res = engine.evaluate_reading(
        device_id="ENV-BLOCK-B-001",
        metric="mq135_raw_adc",
        value=0.0
    )
    assert res.is_anomaly is False
    assert res.reporting_state == AdaptiveReportingState.NORMAL_15M


def test_time_ordered_holdout_replay_benchmark():
    """Test 11: Sequential holdout replay benchmark confirms adaptive engine superior specificity over static thresholds."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Synthesize realistic benchmark sequence:
    # 25 normal baseline points, 2 transient noise glitches, 3 genuine prolonged anomalies, 5 recovery points
    scenario = []
    base_time = datetime.datetime(2026, 11, 8, 8, 0, 0, tzinfo=datetime.timezone.utc)

    # 1. Baseline normal (2.0 kW)
    for i in range(25):
        scenario.append({
            "timestamp": (base_time + datetime.timedelta(minutes=15 * i)).isoformat(),
            "value": 2.0 + (i % 3) * 0.1,
            "ground_truth_anomaly": False
        })

    # 2. Transient noise glitches (single-sample spikes to 3.3 kW)
    scenario.append({
        "timestamp": (base_time + datetime.timedelta(minutes=15 * 25)).isoformat(),
        "value": 3.3,  # Noise spike
        "ground_truth_anomaly": False
    })
    scenario.append({
        "timestamp": (base_time + datetime.timedelta(minutes=15 * 26)).isoformat(),
        "value": 2.1,  # Promptly back to normal
        "ground_truth_anomaly": False
    })

    # 3. Sustained genuine overload anomaly (3 samples at 4.2 kW)
    for j in range(3):
        scenario.append({
            "timestamp": (base_time + datetime.timedelta(minutes=15 * (27 + j))).isoformat(),
            "value": 4.2,
            "ground_truth_anomaly": True
        })

    # 4. Recovery
    for k in range(5):
        scenario.append({
            "timestamp": (base_time + datetime.timedelta(minutes=15 * (30 + k))).isoformat(),
            "value": 2.0,
            "ground_truth_anomaly": False
        })

    report = engine.evaluate_historical_holdout(
        device_id="METER-BENCH-TEST",
        metric="active_power_kw",
        scenario_data=scenario,
        static_threshold=3.0  # Naive threshold triggers on every single transient noise spike
    )

    assert "adaptive_engine" in report
    assert "static_threshold" in report

    adaptive = report["adaptive_engine"]
    static = report["static_threshold"]

    # Adaptive engine rejects the transient noise spike, achieving fewer or zero false positives
    assert adaptive["false_positives"] < static["false_positives"]
    assert adaptive["specificity_pct"] >= static["specificity_pct"]
    assert report["performance_verdict"] == "ADAPTIVE_SUPERIOR_SPECIFICITY"


def test_adaptive_status_endpoint_direct():
    """Test 12: get_adaptive_telemetry_status returns campus cadence, countdowns, and active devices."""
    # Seed a device
    p = make_telemetry_payload("METER-BLOCK-B-001", "active_power_kw", 2.1)
    GLOBAL_DEVICE_REGISTRY.ingest_telemetry(p)

    data = get_adaptive_telemetry_status()

    assert "campus_reporting_state" in data
    assert "campus_reporting_interval_sec" in data
    assert "campus_next_report_expected_sec" in data
    assert "active_devices_count" in data
    assert "active_anomalies" in data
    assert data["campus_reporting_state"] in ["NORMAL_15M", "ANOMALY_5M", "RECOVERY_5M"]


def test_evaluate_benchmark_endpoint_direct():
    """Test 13: evaluate_anomaly_benchmark runs sequential holdout evaluation endpoint."""
    report = evaluate_anomaly_benchmark()
    assert report["status"] == "COMPLETED"
    assert "comparison" in report
    assert report["comparison"]["adaptive_engine"]["true_positives"] >= 1
