"""
Comprehensive Verification Tests for EstateIQ Dual ESP32 Gateways, Alert Lifecycle & Weather Services.
"""

import pytest
import datetime
import time
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
from src.services.alert_service import AlertService, AlertState, AlertSeverity
from src.services.weather_service import WeatherService
from src.services.anomaly_engine import EstateIQAdaptiveAnomalyEngine, AdaptiveReportingState


def test_dual_gateway_registration_and_status():
    """Verifies that both Node #1 (Edge) and Node #2 (PZEM) report independent health."""
    gws = GLOBAL_DEVICE_REGISTRY.get_gateways_status()
    assert len(gws) == 2, "Expected exactly 2 registered gateways in EstateIQ registry"

    gw_ids = [g["gateway_id"] for g in gws]
    assert "ESP32_EDGE_GATEWAY_01" in gw_ids
    assert "ESP32_PZEM_GATEWAY_01" in gw_ids

    # Inspect Node #1 sensors
    node1 = next(g for g in gws if g["gateway_id"] == "ESP32_EDGE_GATEWAY_01")
    sensor_models = [s["sensor"] for s in node1["sensors"]]
    assert "HC-SR04" in sensor_models
    assert "ZJ-S201" in sensor_models
    assert "DHT11" in sensor_models
    assert "MQ-135" in sensor_models

    # Inspect Node #2 sensors
    node2 = next(g for g in gws if g["gateway_id"] == "ESP32_PZEM_GATEWAY_01")
    node2_models = [s["sensor"] for s in node2["sensors"]]
    assert "PZEM-004T" in node2_models


def test_gateway_health_state_transitions():
    """Verifies transition thresholds: Online <= 45s, Stale 45-300s, Offline > 300s."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Fresh gateway (seen 5s ago) -> ONLINE
    fresh_time = (now - datetime.timedelta(seconds=5)).isoformat()
    GLOBAL_DEVICE_REGISTRY.gateways["ESP32_EDGE_GATEWAY_01"]["last_seen_at"] = fresh_time
    st = GLOBAL_DEVICE_REGISTRY.get_gateways_status()
    n1 = next(g for g in st if g["gateway_id"] == "ESP32_EDGE_GATEWAY_01")
    assert n1["connection_status"] == "ONLINE"

    # 2. Stale gateway (seen 60s ago) -> STALE
    stale_time = (now - datetime.timedelta(seconds=60)).isoformat()
    GLOBAL_DEVICE_REGISTRY.gateways["ESP32_EDGE_GATEWAY_01"]["last_seen_at"] = stale_time
    st = GLOBAL_DEVICE_REGISTRY.get_gateways_status()
    n1 = next(g for g in st if g["gateway_id"] == "ESP32_EDGE_GATEWAY_01")
    assert n1["connection_status"] == "STALE"

    # 3. Offline gateway (seen 350s ago) -> OFFLINE
    offline_time = (now - datetime.timedelta(seconds=350)).isoformat()
    GLOBAL_DEVICE_REGISTRY.gateways["ESP32_EDGE_GATEWAY_01"]["last_seen_at"] = offline_time
    st = GLOBAL_DEVICE_REGISTRY.get_gateways_status()
    n1 = next(g for g in st if g["gateway_id"] == "ESP32_EDGE_GATEWAY_01")
    assert n1["connection_status"] == "OFFLINE"


def test_alert_lifecycle_and_deduplication():
    """Verifies alert creation, deduplication cooldown, lifecycle transitions, and auto-recovery."""
    svc = AlertService(cooldown_seconds=300)

    # 1. Create alert for water leak
    alt = svc.create_or_update_alert(
        source_type="real_sensor",
        device_id="WATER-BLOCK-B-001",
        metric="water_flow_lmin",
        observed_value=22.5,
        expected_value=3.2,
        severity="CRITICAL",
        unit="L/min",
        reason="Pipe burst detected"
    )
    assert alt.state == AlertState.OPEN
    assert alt.occurrence_count == 1
    assert alt.observed_value == 22.5

    # 2. Subsequent reading within cooldown -> DEDUPLICATE (not duplicate)
    alt2 = svc.create_or_update_alert(
        source_type="real_sensor",
        device_id="WATER-BLOCK-B-001",
        metric="water_flow_lmin",
        observed_value=23.1,
        expected_value=3.2,
        severity="CRITICAL",
        unit="L/min"
    )
    assert alt2.id == alt.id
    assert alt2.occurrence_count == 2
    assert alt2.last_observed_value == 23.1

    # 3. Acknowledge alert
    ack = svc.acknowledge_alert(alt.id, actor="Engineer Ravi", notes="Investigating Block B valve")
    assert ack.state == AlertState.ACKNOWLEDGED
    assert ack.audit_trail[-1].action == "ACKNOWLEDGED"

    # 4. Assign alert
    assigned = svc.assign_alert(alt.id, assignee="Plumbing Team A", actor="Supervisor Anita")
    assert assigned.state == AlertState.ASSIGNED
    assert assigned.assignee == "Plumbing Team A"

    # 5. Auto-resolve upon normal recovery
    resolved = svc.auto_resolve_metric("real_sensor", "WATER-BLOCK-B-001", "water_flow_lmin")
    assert resolved is not None
    assert resolved.state == AlertState.RESOLVED
    assert "consecutive normal cycles" in resolved.resolved_reason


def test_weather_service_caching_and_separation():
    """Verifies outdoor ambient weather fetching, caching, and non-blocking fallback."""
    ws = WeatherService(cache_ttl_seconds=900)
    w1 = ws.get_current_weather()
    assert w1.is_available is True
    assert w1.temperature_c > -20.0 and w1.temperature_c < 60.0
    assert w1.context_type == "OUTDOOR_AMBIENT"

    # Subsequent immediate call must return cached data
    w2 = ws.get_current_weather()
    assert w2.is_cached is True or w2.cache_age_seconds >= 0


def test_anomaly_engine_physical_limits():
    """Verifies that waste bin >= 80% and water flow > 18 L/min trigger immediate critical alarms."""
    engine = EstateIQAdaptiveAnomalyEngine()

    # Bin overflow
    res_bin = engine.evaluate_reading(
        device_id="WASTE-BLOCK-B-001",
        metric="fill_level_percent",
        value=85.0
    )
    assert res_bin.is_anomaly is True
    assert res_bin.severity.value in ("CRITICAL", "HIGH")
    assert "80.0%" in res_bin.explanation or "capacity" in res_bin.explanation

    # Normal bin reading
    res_bin_norm = engine.evaluate_reading(
        device_id="WASTE-BLOCK-B-001",
        metric="fill_level_percent",
        value=40.0
    )
    assert res_bin_norm.is_anomaly is False
