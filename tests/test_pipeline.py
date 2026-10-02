"""
Automated Test Suite for Sustainable Facility Intelligence Platform.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_predict_energy():
    payload = {
        "temperature": 32.0,
        "humidity": 55.0,
        "occupancy": 150,
        "hvac_load": 50.0,
        "lighting_load": 15.0,
        "equipment_load": 25.0,
        "previous_energy_kwh": 120.0,
        "hour": 14,
        "day_of_week": 2
    }
    response = client.post("/predict/energy", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "predicted_energy_kwh" in res
    assert res["predicted_energy_kwh"] > 0

def test_predict_waste():
    payload = {
        "fill_level": 82.0,
        "fill_rate": 5.0,
        "temperature": 30.0,
        "occupancy": 200,
        "day_of_week": 3,
        "hour": 16,
        "collection_time": 0
    }
    response = client.post("/predict/waste", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "overflow_probability" in res
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH"]

def test_anomaly_water():
    payload = {
        "facility_id": "FAC_COLLEGE_01",
        "building_id": "Block_B_Hostel",
        "measurements": {"flow_rate": 50.0, "occupancy": 5}
    }
    response = client.post("/anomaly/water", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["anomaly_status"] == "ANOMALY_DETECTED"
    assert "inspection" in res["explanation"]

def test_recommendations():
    payload = {
        "issue": "energy_anomaly",
        "building": "Block B Hostel",
        "actual": 120.0,
        "expected": 85.0,
        "deviation_percent": 41.1,
        "important_features": ["occupancy", "temperature"]
    }
    response = client.post("/recommendations", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "title" in res
    assert "1_what_happened" in res
    assert res["4_severity"] == "HIGH"

def test_scenario():
    payload = {
        "current_values": {"temperature": 28.0, "occupancy": 150.0, "hvac_load": 50.0},
        "modifications": {"hvac_load": 0.80}
    }
    response = client.post("/scenario", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "simulated_scenario_prediction" in res

def test_models_registry():
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json()["registered_models_count"] > 0

if __name__ == "__main__":
    print("Running automated system integration tests...")
    test_health()
    print("[PASS] GET /health PASSED")
    test_predict_energy()
    print("[PASS] POST /predict/energy PASSED")
    test_predict_waste()
    print("[PASS] POST /predict/waste PASSED")
    test_anomaly_water()
    print("[PASS] POST /anomaly/water PASSED")
    test_recommendations()
    print("[PASS] POST /recommendations PASSED")
    test_scenario()
    print("[PASS] POST /scenario PASSED")
    test_models_registry()
    print("[PASS] GET /models PASSED")
    print("==================================================")
    print("ALL API & SYSTEM INTEGRATION TESTS PASSED 100%!")
    print("==================================================")

