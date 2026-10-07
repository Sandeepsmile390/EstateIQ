"""
GenAI Assistant & Grounded Copilot Integration Tests (tests/test_genai.py).
"""

import unittest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from api.main import app

class TestGenAIEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_offline_fallback_energy_query(self):
        mock_groq = MagicMock()
        mock_completion = MagicMock()
        mock_response_json = {
            "summary": "Block B Hostel energy consumption is 145.2 kWh vs 78.0 kWh expected baseline.",
            "what_happened": "HVAC surge in Block B Hostel.",
            "why_it_happened": "Continuous HVAC load.",
            "evidence": ["Baseline deviation +86.1%"],
            "confidence_percent": 90.0,
            "business_impact": "₹53,700/year",
            "recommended_actions": ["Reset thermostat setback schedule to 24.5°C"],
            "what_if_interpretation": "",
            "assumptions": [],
            "limitations": [],
            "data_status": "SUCCESS",
            "verification_status": "PENDING",
            "provenance": "GROQ_LLM_INTERPRETATION"
        }
        mock_completion.choices[0].message.content = str(mock_response_json).replace("'", '"')
        mock_groq.chat.completions.create.return_value = mock_completion

        with patch("src.ai.ai_service.get_groq_client", return_value=mock_groq):
            payload = {"user_query": "Why is energy consumption high in Block B Hostel?"}
            res = self.client.post("/api/v1/ai/chat", json=payload)
            self.assertEqual(res.status_code, 200)
            json_res = res.json()
            self.assertIn("summary", json_res)
            self.assertIn("Block B", json_res["summary"])

    def test_offline_fallback_waste_query(self):
        mock_groq = MagicMock()
        mock_completion = MagicMock()
        mock_response_json = {
            "summary": "Bin 01 at Central Cafeteria is projected to reach >90% fill capacity within 2 hours.",
            "what_happened": "Smart waste bin overflow risk.",
            "why_it_happened": "Peak lunch occupancy fill rate.",
            "evidence": ["Bin 01 fill rate"],
            "confidence_percent": 88.0,
            "business_impact": "Sanitation dispatch required.",
            "recommended_actions": ["Dispatch collection crew to Bin 01"],
            "what_if_interpretation": "",
            "assumptions": [],
            "limitations": [],
            "data_status": "SUCCESS",
            "verification_status": "PENDING",
            "provenance": "GROQ_LLM_INTERPRETATION"
        }
        mock_completion.choices[0].message.content = str(mock_response_json).replace("'", '"')
        mock_groq.chat.completions.create.return_value = mock_completion

        with patch("src.ai.ai_service.get_groq_client", return_value=mock_groq):
            payload = {"user_query": "Which bins will overflow?"}
            res = self.client.post("/api/v1/ai/chat", json=payload)
            self.assertEqual(res.status_code, 200)
            json_res = res.json()
            self.assertIn("summary", json_res)
            self.assertIn("Bin 01", json_res["summary"])

if __name__ == "__main__":
    unittest.main()
