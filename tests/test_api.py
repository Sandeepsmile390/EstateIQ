"""
FastAPI Endpoints Tests
"""

import unittest
from pathlib import Path
import sys
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from api.main import app

class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "HEALTHY")

    def test_predict_energy_endpoint(self):
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
        res = self.client.post("/predict/energy", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("predicted_energy_kwh", res.json())

    def test_predict_waste_endpoint(self):
        payload = {
            "fill_level": 82.0,
            "fill_rate": 5.0,
            "temperature": 30.0,
            "occupancy": 200,
            "day_of_week": 3,
            "hour": 16,
            "collection_time": 0
        }
        res = self.client.post("/predict/waste", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("overflow_probability", res.json())

    def test_water_anomaly_endpoint(self):
        payload = {
            "facility_id": "FAC_COLLEGE_01",
            "building_id": "Block_B_Hostel",
            "measurements": {"flow_rate": 50.0, "occupancy": 5}
        }
        res = self.client.post("/anomaly/water", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["anomaly_status"], "ANOMALY_DETECTED")

    def test_models_registry_endpoint(self):
        res = self.client.get("/models")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.json()["registered_models_count"], 0)

if __name__ == "__main__":
    unittest.main()
