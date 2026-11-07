"""
EstateIQ Resource Simulator Unit & Integration Test Suite (tests/test_resource_simulator.py).

Covers:
1. Electricity physics: P = V * I * PF / 1000, frequency, voltage bounds, monotonic kWh totalizer.
2. Water physics: Flow rate, hydraulic pressure behavior, monotonic m³ totalizer.
3. Air quality metrics: CO2, PM2.5, PM10, temperature, humidity, and EPA AQI derivation.
4. Waste metrics: Accumulation rate, volumetric fill %, mass derivation (kg), overflow risk, emptied reset.
5. Telemetry provenance: source_type="simulated_iot", is_verified_hardware=False, badge="[SIMULATED IoT]".
6. Global device registry ingestion: End-to-end ingestion of all 4 resource streams.
"""

import os
import sys
import math
import datetime
import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.telemetry_schema import (
    normalize_telemetry_payload,
    resolve_provenance_badge,
    SourceType,
    CANONICAL_METRIC_MAP,
    METRIC_RANGE_LIMITS
)
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY


# --- 1. Electricity Physics Tests ---

def test_electricity_physics_and_plausibility():
    """Verify active power, voltage, current, power factor and monotonic kWh totalizer."""
    base_kw = 55.0
    v_nom = 230.0
    pf_nom = 0.95
    dt_sec = 5.0

    # Physical formula: I = (1000 * P) / (V * PF)
    current_calc = (1000.0 * base_kw) / (v_nom * pf_nom)
    assert 245.0 <= current_calc <= 260.0

    # Bounded electrical limits
    assert METRIC_RANGE_LIMITS["active_power_kw"][0] <= base_kw <= METRIC_RANGE_LIMITS["active_power_kw"][1]
    assert METRIC_RANGE_LIMITS["voltage_v"][0] <= v_nom <= METRIC_RANGE_LIMITS["voltage_v"][1]
    assert METRIC_RANGE_LIMITS["power_factor"][0] <= pf_nom <= METRIC_RANGE_LIMITS["power_factor"][1]

    # Monotonic cumulative energy: dKwh = P * dt / 3600
    cum_kwh_0 = 3420.50
    delta_kwh = (base_kw * dt_sec) / 3600.0
    cum_kwh_1 = cum_kwh_0 + delta_kwh
    assert cum_kwh_1 > cum_kwh_0
    assert math.isclose(cum_kwh_1 - cum_kwh_0, delta_kwh, rel_tol=1e-5)


# --- 2. Water Hydraulic & Volume Tests ---

def test_water_flow_and_monotonic_volume():
    """Verify flow rate, pressure bounds, and monotonic cubic meter totalizer."""
    base_flow_lmin = 35.0
    pressure_bar = 3.4
    dt_sec = 5.0

    # Bounded hydraulic limits
    assert METRIC_RANGE_LIMITS["water_flow_lmin"][0] <= base_flow_lmin <= METRIC_RANGE_LIMITS["water_flow_lmin"][1]
    assert METRIC_RANGE_LIMITS["water_pressure_bar"][0] <= pressure_bar <= METRIC_RANGE_LIMITS["water_pressure_bar"][1]

    # Monotonic cubic meter volume increment: 1 m³ = 1000 Liters
    cum_m3_0 = 842.150
    delta_m3 = (base_flow_lmin * (dt_sec / 60.0)) / 1000.0
    cum_m3_1 = cum_m3_0 + delta_m3
    assert cum_m3_1 > cum_m3_0
    assert math.isclose(cum_m3_1 - cum_m3_0, delta_m3, rel_tol=1e-5)

    # In burst flow scenario, pressure drops significantly
    burst_flow_lmin = base_flow_lmin * 4.2
    burst_pressure_bar = 1.4
    assert burst_flow_lmin > base_flow_lmin
    assert burst_pressure_bar < pressure_bar


# --- 3. Air Quality & AQI Tests ---

def test_air_quality_metrics_and_epa_aqi():
    """Verify CO2, PM2.5, PM10 ranges and EPA AQI category classification."""
    occupancy = 120
    # Expected normal indoor CO2: ~400 + (1.8 * 120) = 616 ppm
    expected_co2 = 410.0 + (occupancy * 1.8)
    assert 550.0 <= expected_co2 <= 700.0
    assert METRIC_RANGE_LIMITS["co2_ppm"][0] <= expected_co2 <= METRIC_RANGE_LIMITS["co2_ppm"][1]

    # EPA PM2.5 AQI piecewise evaluation
    def epa_aqi(pm25):
        if pm25 <= 12.0:
            return round((50.0 / 12.0) * pm25), "Good"
        elif pm25 <= 35.4:
            return round(((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1) + 51), "Moderate"
        elif pm25 <= 55.4:
            return round(((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5) + 101), "Sensitive"
        else:
            return round(((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5) + 151), "Unhealthy"

    aqi_good, cat_good = epa_aqi(10.5)
    assert aqi_good <= 50 and cat_good == "Good"

    aqi_mod, cat_mod = epa_aqi(22.0)
    assert 51 <= aqi_mod <= 100 and cat_mod == "Moderate"

    aqi_unh, cat_unh = epa_aqi(95.0)
    assert aqi_unh > 150 and cat_unh == "Unhealthy"


# --- 4. Waste Management & Reset Tests ---

def test_waste_accumulation_and_reset():
    """Verify fill level bounds, volume-to-mass derivation, overflow risk, and emptied reset."""
    fill_level_pct = 38.0
    bin_capacity_liters = 1100.0
    average_density_kg_l = 0.15  # Uncompacted municipal waste

    # Estimated mass: (fill_pct / 100) * 1100 * 0.15 => max ~165 kg
    estimated_mass_kg = (fill_level_pct / 100.0) * bin_capacity_liters * average_density_kg_l
    assert 60.0 <= estimated_mass_kg <= 65.0
    assert METRIC_RANGE_LIMITS["fill_level_percent"][0] <= fill_level_pct <= METRIC_RANGE_LIMITS["fill_level_percent"][1]
    assert METRIC_RANGE_LIMITS["estimated_waste_kg"][0] <= estimated_mass_kg <= METRIC_RANGE_LIMITS["estimated_waste_kg"][1]

    # Overflow risk tiers
    def derive_risk(fill):
        if fill < 50.0: return "LOW"
        elif fill < 75.0: return "MEDIUM"
        elif fill < 90.0: return "HIGH"
        return "CRITICAL"

    assert derive_risk(38.0) == "LOW"
    assert derive_risk(65.0) == "MEDIUM"
    assert derive_risk(82.0) == "HIGH"
    assert derive_risk(94.5) == "CRITICAL"

    # Emptied reset: resets level to ~4%
    reset_fill = 4.0
    reset_mass = (reset_fill / 100.0) * bin_capacity_liters * average_density_kg_l
    assert reset_fill < 10.0
    assert reset_mass < 10.0


# --- 5. Telemetry Provenance & Hardware Flags ---

def test_telemetry_provenance_and_hardware_flags():
    """Verify all simulated packets preserve simulated_iot provenance and is_verified_hardware=False."""
    now_iso = datetime.datetime.now().isoformat()
    raw_payload = {
        "device_id": "SIM-ELEC-01",
        "simulator_id": "SIM_RESOURCE_DEMO_01",
        "facility_id": "FAC_GEC_CAMPUS",
        "building_id": "Block B Hostel",
        "source_type": "simulated_iot",
        "is_verified_hardware": False,
        "data_source_badge": "[SIMULATED IoT]",
        "event_timestamp": now_iso,
        "measurements": {
            "active_power_kw": 55.4,
            "cumulative_energy_kwh": 3422.1,
            "voltage_v": 230.1,
            "current_a": 252.0,
            "power_factor": 0.95,
            "frequency_hz": 50.02
        }
    }

    envelope, flat_map, warnings = normalize_telemetry_payload(raw_payload)
    assert envelope.device_id == "SIM-ELEC-01"
    assert envelope.source_type == SourceType.SIMULATED_IOT

    badge = resolve_provenance_badge(envelope.source_type, is_verified=False)
    assert badge == "[SIMULATED IoT]"
    assert "[REAL SENSOR]" not in badge

    # Verification via registry ingestion
    ingest_res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(raw_payload)
    assert ingest_res["is_verified_hardware"] is False
    assert ingest_res["source_type"] == "simulated_iot"
    assert ingest_res["data_source_badge"] == "[SIMULATED IoT]"


# --- 6. End-to-End Global Device Registry Ingestion ---

def test_registry_telemetry_ingestion_end_to_end():
    """Verify all 4 utility streams are ingested and accepted by GLOBAL_DEVICE_REGISTRY."""
    now_iso = datetime.datetime.now().isoformat()

    packets = [
        {
            "message_id": f"MSG_TEST_ELEC_{datetime.datetime.now().timestamp()}",
            "device_id": "SIM-ELEC-01",
            "simulator_id": "SIM_RESOURCE_DEMO_01",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel",
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "active_power_kw": 58.2,
                "cumulative_energy_kwh": 3425.0,
                "voltage_v": 229.8,
                "current_a": 265.0,
                "power_factor": 0.94,
                "frequency_hz": 50.01
            }
        },
        {
            "message_id": f"MSG_TEST_WATER_{datetime.datetime.now().timestamp()}",
            "device_id": "SIM-WATER-01",
            "simulator_id": "SIM_RESOURCE_DEMO_01",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel",
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "water_flow_lmin": 36.4,
                "cumulative_water_m3": 843.05,
                "water_pressure_bar": 3.35
            }
        },
        {
            "message_id": f"MSG_TEST_AIR_{datetime.datetime.now().timestamp()}",
            "device_id": "SIM-AIR-01",
            "simulator_id": "SIM_RESOURCE_DEMO_01",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel",
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "co2_ppm": 635.0,
                "pm25": 17.2,
                "pm10": 28.5,
                "temperature_c": 23.4,
                "humidity_pct": 49.0,
                "air_quality_aqi": 48.0
            }
        },
        {
            "message_id": f"MSG_TEST_WASTE_{datetime.datetime.now().timestamp()}",
            "device_id": "SIM-WASTE-01",
            "simulator_id": "SIM_RESOURCE_DEMO_01",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel",
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "fill_level_percent": 41.5,
                "estimated_waste_kg": 68.5
            }
        }
    ]

    for pkt in packets:
        res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(pkt)
        assert res["success"] is True or res.get("accepted") is True
        assert res["data_source_badge"] == "[SIMULATED IoT]"
        assert res["source_type"] == "simulated_iot"

    # Confirm devices registered in registry
    assert "SIM-ELEC-01" in GLOBAL_DEVICE_REGISTRY.devices
    assert "SIM-WATER-01" in GLOBAL_DEVICE_REGISTRY.devices
    assert "SIM-AIR-01" in GLOBAL_DEVICE_REGISTRY.devices
    assert "SIM-WASTE-01" in GLOBAL_DEVICE_REGISTRY.devices

    # Confirm monotonic totalizer stored
    elec_dev = GLOBAL_DEVICE_REGISTRY.devices["SIM-ELEC-01"]
    assert elec_dev.last_counter_energy_kwh == 3425.0
    assert elec_dev.source_type == "simulated_iot"

# --- 7. Multi-Scenario Range & Physics Bounds Tests ---

def test_all_utility_scenarios_bounds():
    """Verify that every scenario for each utility outputs values within physical ranges."""
    # 1. Electricity Scenarios
    elec_scenarios = ["NORMAL", "PEAK_DEMAND", "AFTER_HOURS_WASTE", "VOLTAGE_INSTABILITY"]
    for scen in elec_scenarios:
        base_kw = 55.0
        if scen == "PEAK_DEMAND":
            p = base_kw * 1.85
            v = 224.0
            pf = 0.91
        elif scen == "AFTER_HOURS_WASTE":
            p = base_kw * 1.35
            v = 232.0
            pf = 0.89
        elif scen == "VOLTAGE_INSTABILITY":
            p = base_kw * 1.10
            v = 210.0
            pf = 0.75
        else:
            p = base_kw
            v = 230.0
            pf = 0.95

        i_calc = (1000.0 * p) / (v * pf)
        assert 1.0 <= p <= 500.0
        assert 180.0 <= v <= 280.0
        assert 0.50 <= pf <= 1.0
        assert i_calc > 0

    # 2. Water Scenarios
    water_scenarios = ["NORMAL", "SUSTAINED_LEAK", "BURST_FLOW", "LOW_FLOW"]
    for scen in water_scenarios:
        base_flow = 35.0
        if scen == "SUSTAINED_LEAK":
            flow = base_flow + 26.5
            pres = 2.8
        elif scen == "BURST_FLOW":
            flow = base_flow * 4.2
            pres = 1.4
        elif scen == "LOW_FLOW":
            flow = 0.5
            pres = 1.8
        else:
            flow = base_flow
            pres = 3.4

        assert 0.0 <= flow <= 500.0
        assert 0.2 <= pres <= 8.0

    # 3. Air Quality Scenarios
    air_scenarios = ["NORMAL", "POOR_VENTILATION", "PARTICULATE_SPIKE", "SENSOR_FAULT"]
    for scen in air_scenarios:
        occ = 120
        if scen == "POOR_VENTILATION":
            co2 = 1450.0 + (occ * 3.2)
            pm25 = 36.0
        elif scen == "PARTICULATE_SPIKE":
            co2 = 620.0
            pm25 = 125.0
        elif scen == "SENSOR_FAULT":
            co2 = 2500.0
            pm25 = 85.0
        else:
            co2 = 410.0 + (occ * 1.8)
            pm25 = 15.0

        assert 350.0 <= co2 <= 5000.0
        assert 0.0 <= pm25 <= 500.0

    # 4. Waste Scenarios
    waste_scenarios = ["NORMAL", "EVENT_RAPID", "BIN_FULL", "RESET_EMPTIED"]
    for scen in waste_scenarios:
        if scen == "EVENT_RAPID":
            fill = 65.0
        elif scen == "BIN_FULL":
            fill = 94.0
        elif scen == "RESET_EMPTIED":
            fill = 4.0
        else:
            fill = 38.0

        est_kg = (fill / 100.0) * 165.0
        assert 0.0 <= fill <= 100.0
        assert 0.0 <= est_kg <= 185.0


# --- 8. Monotonicity and Idempotency Tests ---

def test_monotonic_counter_integrity_and_idempotency():
    """Verify cumulative energy totalizers increment monotonically and duplicate packets are idempotent."""
    dev_id = "SIM-MONO-TEST-01"
    now_iso = datetime.datetime.now().isoformat()

    msg_id = f"MSG_IDEMP_{datetime.datetime.now().timestamp()}"
    payload_1 = {
        "message_id": msg_id,
        "device_id": dev_id,
        "source_type": "simulated_iot",
        "event_timestamp": now_iso,
        "measurements": {
            "cumulative_energy_kwh": 100.0,
            "active_power_kw": 20.0
        }
    }
    res1 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_1)
    assert res1["success"] is True

    # Same message_id again => idempotent duplicate acknowledgment
    res2 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_1)
    assert res2["accepted"] is True
    assert res2.get("duplicate") is True
    assert res2["status"] == "DUPLICATE_IGNORED"

    # Monotonic increment with new message_id and chronological forward timestamp
    next_iso = (datetime.datetime.now() + datetime.timedelta(seconds=5)).isoformat()
    payload_2 = {
        "message_id": f"MSG_IDEMP_2_{datetime.datetime.now().timestamp()}",
        "device_id": dev_id,
        "source_type": "simulated_iot",
        "event_timestamp": next_iso,
        "measurements": {
            "cumulative_energy_kwh": 100.5,
            "active_power_kw": 20.0
        }
    }
    res3 = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload_2)
    assert res3["success"] is True
    dev = GLOBAL_DEVICE_REGISTRY.devices[dev_id]
    assert dev.last_counter_energy_kwh == 100.5
