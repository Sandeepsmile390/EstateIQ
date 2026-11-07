"""
EstateIQ Standalone Resource Simulator Test Suite (resource-simulator-app/tests/test_standalone.py).
Tests standalone physics engine, monotonic totalizers, telemetry envelope builder, and REST endpoints.
"""

import sys
import os
import math
from pathlib import Path
import pytest

# Ensure resource-simulator-app directory is on sys.path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

os.environ["TESTING"] = "1"

from server import (
    SIMULATOR,
    health,
    get_status,
    start_simulation,
    pause_simulation,
    step_simulation,
    stop_simulation,
    reset_simulation,
    set_scenario,
    set_baseline,
    set_interval,
    get_stream,
    ScenarioRequest,
    BaselineConfigRequest,
    IntervalConfigRequest
)
from engine.models import ElectricityState, WaterState, AirQualityState, WasteState
from engine.physics import (
    update_electricity_physics,
    update_water_physics,
    update_air_quality_physics,
    update_waste_physics,
    calculate_epa_aqi
)
from engine.client import build_telemetry_packets


# --- 1. Physics Engine Tests ---

def test_standalone_electricity_physics():
    state = ElectricityState()
    initial_kwh = state.cumulative_energy_kwh

    update_electricity_physics(state, dt_sec=5.0)

    # Plausible Ohm's relationship: I = 1000 * P / (V * PF)
    expected_current = (1000.0 * state.active_power_kw) / (state.voltage_v * state.power_factor)
    assert math.isclose(state.current_a, expected_current, rel_tol=0.05)

    # Monotonic increment
    assert state.cumulative_energy_kwh > initial_kwh
    assert 180.0 <= state.voltage_v <= 280.0
    assert 0.50 <= state.power_factor <= 1.0
    assert 48.0 <= state.frequency_hz <= 52.0


def test_standalone_water_physics():
    state = WaterState()
    initial_m3 = state.cumulative_water_m3

    update_water_physics(state, dt_sec=5.0)
    assert state.cumulative_water_m3 > initial_m3
    assert 0.0 <= state.flow_rate_lmin <= 600.0
    assert 0.2 <= state.water_pressure_bar <= 8.0

    # Burst flow test: pressure drops
    state.scenario = "BURST_FLOW"
    update_water_physics(state, dt_sec=5.0)
    assert state.flow_rate_lmin > 100.0
    assert state.water_pressure_bar <= 2.2


def test_standalone_air_quality_physics():
    state = AirQualityState()
    update_air_quality_physics(state, dt_sec=5.0)

    assert 350.0 <= state.co2_ppm <= 5000.0
    assert 0.0 <= state.pm25 <= 500.0
    assert 0.0 <= state.air_quality_aqi <= 500.0

    # High occupancy increase test
    state.baseline_occupancy = 300
    state.scenario = "POOR_VENTILATION"
    update_air_quality_physics(state, dt_sec=5.0)
    assert state.co2_ppm > 1500.0

    # EPA AQI Breakpoints check
    aqi_good, cat_good = calculate_epa_aqi(10.0)
    assert aqi_good <= 50 and cat_good == "Good"
    aqi_unh, cat_unh = calculate_epa_aqi(90.0)
    assert aqi_unh > 150 and cat_unh == "Unhealthy"


def test_standalone_waste_physics():
    state = WasteState()
    initial_fill = state.fill_level_percent

    update_waste_physics(state, dt_sec=5.0)
    assert state.fill_level_percent >= initial_fill
    assert 0.0 <= state.fill_level_percent <= 100.0
    assert state.estimated_waste_kg > 0.0

    # Emptied reset test
    state.scenario = "RESET_EMPTIED"
    update_waste_physics(state, dt_sec=5.0)
    assert state.fill_level_percent <= 8.0
    assert state.estimated_waste_kg < 15.0


# --- 2. Telemetry Packet Construction Tests ---

def test_standalone_telemetry_packet_provenance():
    elec = ElectricityState()
    water = WaterState()
    air = AirQualityState()
    waste = WasteState()

    packets = build_telemetry_packets(elec, water, air, waste)
    assert len(packets) == 4

    for pkt in packets:
        assert pkt["source_type"] == "simulated_iot"
        assert pkt["is_verified_hardware"] is False
        assert pkt["data_source_badge"] == "[SIMULATED IoT]"
        assert pkt["facility_id"] == "FAC_GEC_CAMPUS"
        assert pkt["building_id"] == "Block B Hostel"
        assert "measurements" in pkt
        assert len(pkt["measurements"]) > 0


# --- 3. Standalone Server API Endpoint Tests (Direct Route Testing) ---

def test_standalone_api_endpoints():
    # Disable network auto_ingest during test execution
    SIMULATOR.config.auto_ingest = False

    # 1. Health endpoint
    h = health()
    assert h["status"] == "ok"
    assert h["port"] == 8503

    # 2. Status endpoint
    s = get_status()
    assert s["provenance_badge"] == "[SIMULATED DATA]"
    assert s["is_verified_hardware"] is False
    assert "electricity" in s
    assert "water" in s
    assert "air" in s
    assert "waste" in s

    # 3. Step endpoint
    prior_samples = s["samples_generated"]
    step_res = step_simulation()
    assert step_res["success"] is True
    assert step_res["samples_generated"] == prior_samples + 1

    # 4. Scenario switching
    scen_res = set_scenario(ScenarioRequest(utility="water", scenario="BURST_FLOW"))
    assert scen_res["success"] is True
    assert SIMULATOR.water.scenario == "BURST_FLOW"

    # 5. Baseline configuration
    conf_res = set_baseline(BaselineConfigRequest(utility="electricity", value=80.0))
    assert conf_res["success"] is True
    assert SIMULATOR.electricity.baseline_kw == 80.0

    # 6. Interval configuration
    int_res = set_interval(IntervalConfigRequest(interval_sec=2.0))
    assert int_res["success"] is True
    assert SIMULATOR.config.sample_interval_sec == 2.0

    # 7. History stream endpoint
    stream_res = get_stream()
    assert "history" in stream_res
    assert len(stream_res["history"]["electricity"]["power"]) > 0

    # 8. Reset endpoint
    reset_res = reset_simulation()
    assert reset_res["success"] is True
    assert SIMULATOR.electricity.baseline_kw == 55.0
