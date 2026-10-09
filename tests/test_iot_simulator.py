import pytest
from fastapi.testclient import TestClient
from api.main import app
from src.services.iot_simulator import IoTSimulatorEngine, get_iot_simulator

client = TestClient(app)

def test_iot_simulator_engine_lifecycle():
    engine = IoTSimulatorEngine()
    
    # Test initial status
    status = engine.get_status()
    assert status["data_source_mode"] == "simulated_iot"
    assert "SIMULATED IoT — NOT PHYSICAL SENSOR DATA" in status["data_source_badge"]
    assert status["status"] in ["PAUSED", "STOPPED"]
    
    # Test start & speed
    res_start = engine.start_simulation()
    assert res_start["status"] == "RUNNING"
    
    res_speed = engine.set_speed(5)
    assert res_speed["speed"] == 5
    
    # Test step simulation
    initial_sample_count = engine.samples_generated
    res_step = engine.step_simulation()
    assert engine.samples_generated == initial_sample_count + 1
    assert len(engine.get_stream()) > 0
    
    # Test pause & stop
    res_pause = engine.pause_simulation()
    assert res_pause["status"] == "PAUSED"
    
    res_stop = engine.stop_simulation()
    assert res_stop["status"] == "STOPPED"

def test_iot_simulator_scenario_presets():
    engine = IoTSimulatorEngine()
    
    # Apply HVAC peak surge scenario
    res_hvac = engine.apply_scenario_preset("HVAC_PEAK_SURGE")
    assert res_hvac["active_scenario"] == "HVAC_PEAK_SURGE"
    assert engine.sensors.active_power_kw == 245.0
    assert engine.sensors.hvac_load_kw == 95.0
    
    # Apply Water Pipe Leak scenario
    res_leak = engine.apply_scenario_preset("WATER_PIPE_LEAK")
    assert res_leak["active_scenario"] == "WATER_PIPE_LEAK"
    assert engine.sensors.water_flow_lmin == 185.0
    
    # Reset controls
    res_reset = engine.reset_controls()
    assert engine.sensors.active_power_kw == 145.2

def test_iot_simulator_sensor_overrides_validation():
    engine = IoTSimulatorEngine()
    
    # Valid override
    res = engine.update_sensors({"active_power_kw": 200.0, "temperature_c": 35.0})
    assert res["sensors"]["active_power_kw"] == 200.0
    assert res["sensors"]["temperature_c"] == 35.0
    
    # Out of range override should be clamped
    res_clamp = engine.update_sensors({"active_power_kw": 9999.0, "temperature_c": -100.0})
    assert res_clamp["sensors"]["active_power_kw"] == 500.0
    assert res_clamp["sensors"]["temperature_c"] == 10.0

def test_api_iot_simulator_endpoints():
    # Test status endpoint
    response = client.get("/api/v1/iot-simulator/status")
    assert response.status_code == 200
    data = response.json()
    assert data["data_source_mode"] == "simulated_iot"
    
    # Test control endpoint (Start)
    response = client.post("/api/v1/iot-simulator/control", json={"action": "start", "speed": 2})
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"
    
    # Test scenario endpoint
    response = client.post("/api/v1/iot-simulator/scenario", json={"scenario_key": "BIN_OVERFLOW_HAZARD"})
    assert response.status_code == 200
    assert response.json()["active_scenario"] == "BIN_OVERFLOW_HAZARD"
    
    # Test sensor update endpoint
    response = client.post("/api/v1/iot-simulator/sensors", json={"water_flow_lmin": 120.0})
    assert response.status_code == 200
    assert response.json()["sensors"]["water_flow_lmin"] == 120.0
    
    # Test stream endpoint
    response = client.get("/api/v1/iot-simulator/stream?limit=10")
    assert response.status_code == 200
    stream_data = response.json()
    assert stream_data["data_source_mode"] == "simulated_iot"
    assert "stream" in stream_data
    
    # Test DIF engine evaluation endpoint
    response = client.post("/api/v1/iot-simulator/evaluate")
    assert response.status_code == 200
    eval_data = response.json()
    assert eval_data["status"] == "SUCCESS"
    assert eval_data["data_source_mode"] == "simulated_iot"
    assert "dif_analysis" in eval_data
    assert "anomaly_score" in eval_data["dif_analysis"]
