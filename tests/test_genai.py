"""
GenAI Assistant & Offline Fallback Tests
"""

import unittest
from pathlib import Path
import sys
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from api.main import app

class TestGenAIEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_offline_fallback_energy_query(self):
        payload = {"user_query": "Why is energy consumption high in Block B Hostel?"}
        res = self.client.post("/api/v1/ai/chat", json=payload)
        
        self.assertEqual(res.status_code, 200)
        json_res = res.json()
        self.assertIn("mode", json_res)
        self.assertIn("response", json_res)
        self.assertIn("Block B", json_res["response"])

    def test_offline_fallback_waste_query(self):
        payload = {"user_query": "Which bins will overflow?"}
        res = self.client.post("/api/v1/ai/chat", json=payload)
        
        self.assertEqual(res.status_code, 200)
        json_res = res.json()
        self.assertIn("response", json_res)
        self.assertIn("Bin 01", json_res["response"])

if __name__ == "__main__":
    unittest.main()
