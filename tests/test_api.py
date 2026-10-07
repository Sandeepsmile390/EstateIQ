"""
FastAPI Endpoints & Decision Trace Integration Tests
"""

import unittest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
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
        mock_groq = MagicMock()
        mock_completion = MagicMock()
        
        def mock_chat_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            user_msg = messages[-1]["content"].lower() if messages else ""
            
            if "bins" in user_msg or "waste" in user_msg or "collection" in user_msg:
                resp_text = "Bin 01 at Central Cafeteria requires collection dispatch."
            elif "chiller" in user_msg or "vibration" in user_msg:
                resp_text = "AST_CHILLER_01 vibration risk score is elevated."
            elif "water" in user_msg or "leak" in user_msg:
                resp_text = "Hostel A water telemetry indicates low leak risk."
            else:
                resp_text = "Block B Hostel energy demand is 145.2 kWh vs baseline."
                
            mock_res_json = {
                "summary": resp_text,
                "what_happened": resp_text,
                "why_it_happened": "Grounded cause.",
                "evidence": ["Evidence point"],
                "confidence_percent": 90.0,
                "business_impact": "Impact summary",
                "recommended_actions": ["Recommended Action"],
                "what_if_interpretation": "",
                "assumptions": [],
                "limitations": [],
                "data_status": "SUCCESS",
                "verification_status": "PENDING",
                "provenance": "GROQ_LLM_INTERPRETATION"
            }
            res_obj = MagicMock()
            res_obj.choices[0].message.content = str(mock_res_json).replace("'", '"')
            return res_obj

        mock_groq.chat.completions.create.side_effect = mock_chat_create

        queries = [
            ("Why is energy high in Block B?", "Block B"),
            ("Which waste bins need collection?", "Bin 01"),
            ("What is chiller vibration status?", "AST_CHILLER_01"),
            ("What is water leak risk?", "Hostel A")
        ]
        with patch("src.ai.ai_service.get_groq_client", return_value=mock_groq):
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
