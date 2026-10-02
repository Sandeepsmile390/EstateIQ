"""
FastAPI Endpoints & Decision Trace Integration Tests
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

    def test_decision_trace_endpoint(self):
        res = self.client.get("/api/v1/decisions/ALT_01")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("step_1_observed", data)
        self.assertIn("step_5_anomaly", data)
        self.assertIn("step_6_shap", data)
        self.assertIn("step_10_whatif_impact", data)

    def test_data_quality_endpoint(self):
        res = self.client.get("/api/v1/data-quality")
        self.assertEqual(res.status_code, 200)
        self.assertIn("overall_quality_score", res.json())

    def test_sustainability_score_endpoint(self):
        res = self.client.get("/api/v1/sustainability")
        self.assertEqual(res.status_code, 200)
        self.assertIn("sustainability_score", res.json())

    def test_ai_chat_query_matching(self):
        queries = [
            ("Why is energy high in Block B?", "Block B"),
            ("Which waste bins need collection?", "Bin 01"),
            ("What is chiller vibration status?", "AST_CHILLER_01"),
            ("What is water leak risk?", "Hostel A")
        ]
        for q, expected in queries:
            res = self.client.post("/api/v1/ai/chat", json={"user_query": q})
            self.assertEqual(res.status_code, 200)
            self.assertIn(expected, res.json()["response"])

    def test_models_registry_endpoint(self):
        res = self.client.get("/models")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.json()["registered_models_count"], 0)

if __name__ == "__main__":
    unittest.main()
